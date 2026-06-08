from __future__ import annotations

import os
import json
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from html import escape
from dataclasses import dataclass
from functools import lru_cache


DEFAULT_MODEL_ID = os.getenv("MODEL_ID", "openbmb/MiniCPM4.1-8B")
TRANSFORMER_DEVICE_NOTE = "CPU"
TRANSFORMER_PRELOAD_NOTE = ""
NEMOTRON_FALLBACK_MODEL_ID = os.getenv("NEMOTRON_FALLBACK_MODEL_ID", "nvidia/Nemotron-Mini-4B-Instruct").strip()
USE_NEMOTRON_FALLBACK = os.getenv("USE_NEMOTRON_FALLBACK", "0").strip() in {"1", "true", "True", "yes", "YES"}
USE_LLAMA_CPP = os.getenv("USE_LLAMA_CPP", "0").strip() in {"1", "true", "True"}
LLAMA_CPP_BACKEND = os.getenv("LLAMA_CPP_BACKEND", "auto").strip().lower()
LLAMA_CPP_CLI = os.getenv("LLAMA_CPP_CLI", "llama-cli").strip() or "llama-cli"
LLAMA_CPP_MODEL_PATH = os.getenv("LLAMA_CPP_MODEL_PATH", "").strip()
LLAMA_CPP_REPO_ID = os.getenv("LLAMA_CPP_REPO_ID", "openbmb/MiniCPM4.1-8B-GGUF")
LLAMA_CPP_FILENAME = os.getenv("LLAMA_CPP_FILENAME", "MiniCPM4.1-8B-Q4_K_M.gguf")
LLAMA_CPP_HF_SELECTOR = os.getenv("LLAMA_CPP_HF_SELECTOR", "Q4_K_M").strip() or LLAMA_CPP_FILENAME
USE_COHERE_REVIEW = os.getenv("USE_COHERE_REVIEW", "0").strip() in {"1", "true", "True"}
COHERE_MODEL = os.getenv("COHERE_MODEL", "command-a-plus-05-2026")
COHERE_API_URL = "https://api.cohere.com/v2/chat"

# Known parameter budgets for the small models this app is built to run. All are within
# the hackathon's <=32B ceiling; the <=4B entries are the Tiny Titan-eligible demo paths
# selectable via MODEL_ID (e.g. MODEL_ID=openbmb/MiniCPM4-0.5B).
MODEL_PARAM_BUDGETS = {
    "openbmb/MiniCPM4.1-8B": "8B",
    "openbmb/MiniCPM4-0.5B": "0.5B",
    "openbmb/MiniCPM4-0.5B-QAT-Int4-GGUF": "0.5B",
    "openbmb/MiniCPM5-1B": "1B",
    "openbmb/MiniCPM-1B-sft-bf16": "1B",
    "nvidia/Nemotron-Mini-4B-Instruct": "4B",
}


def model_size_label(model_id: str) -> str:
    """Return a human-readable parameter count for a known model id, else empty string."""
    return MODEL_PARAM_BUDGETS.get((model_id or "").strip(), "")


def resolve_local_model_mode() -> tuple[bool, str]:
    configured = os.getenv("USE_LOCAL_MODEL")
    if configured is not None:
        enabled = configured.strip() not in {"0", "false", "False"}
        if enabled:
            return True, ""
        return False, "Small-model generation disabled with USE_LOCAL_MODEL=0; fallback study plan used."

    accelerator = os.getenv("ACCELERATOR", "none").strip().lower()
    is_hf_space = bool(os.getenv("SPACE_ID"))
    cpu_only_space = is_hf_space and accelerator in {"", "none"}
    if cpu_only_space and not USE_LLAMA_CPP:
        return (
            False,
            "HF Space CPU-only runtime detected; fallback study plan used. "
            "Set USE_LOCAL_MODEL=1 only after upgrading hardware or configuring a small GGUF route.",
        )

    return True, ""


USE_LOCAL_MODEL, LOCAL_MODEL_DISABLED_NOTE = resolve_local_model_mode()

PANIC_TERMS = {
    "panic",
    "panicking",
    "scared",
    "afraid",
    "stressed",
    "nothing",
    "fail",
    "blank",
    "crying",
    "overwhelmed",
}

NON_TOPIC_TERMS = PANIC_TERMS | {
    "test",
    "exam",
    "tomorrow",
    "morning",
    "tonight",
    "today",
    "formula",
    "formulas",
    "numerical",
    "numericals",
}

FORMAT_WEIGHTS = {
    "Multiple choice": ("recognition", "Use fast recall loops and mistake traps."),
    "Short answer": ("precision", "Practice compact definitions and worked steps."),
    "Long answer": ("structure", "Build reusable outlines before memorizing detail."),
    "Mixed": ("triage", "Split time between recall, worked examples, and outline drills."),
}


@dataclass(frozen=True)
class StudyInput:
    student_name: str
    subject: str
    time_left_minutes: int
    exam_format: str
    panic_note: str
    known_material: str
    confidence: int


@dataclass(frozen=True)
class StudyPlan:
    rescue_plan_markdown: str
    drill_markdown: str
    triage_markdown: str
    final_sheet_html: str
    demo_receipt_markdown: str
    field_note_markdown: str
    model_note: str


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def extract_topics(text: str, limit: int = 6) -> list[str]:
    raw_parts = re.split(r"[,;\n]|\band\b|\bplus\b", text, flags=re.I)
    topics = []
    for part in raw_parts:
        topic = compact(re.sub(r"^(i know|i need|need to study|study|revise)\s+", "", part, flags=re.I))
        if len(topic) >= 3 and topic.lower() not in {"nothing", "not sure", "everything"}:
            topics.append(topic[:80])

    deduped = []
    seen = set()
    for topic in topics:
        key = topic.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(topic)
    return deduped[:limit]


def extract_study_topics(known_material: str, panic_note: str, limit: int = 6) -> list[str]:
    primary = extract_topics(known_material, limit=limit)
    if primary:
        return primary

    candidates = extract_topics(panic_note, limit=limit * 2)
    filtered = []
    for topic in candidates:
        words = re.findall(r"[a-zA-Z]+", topic.lower())
        if words and sum(word in NON_TOPIC_TERMS for word in words) / len(words) < 0.45:
            filtered.append(topic)
    return filtered[:limit]


def detect_panic(note: str) -> list[str]:
    lowered = note.lower()
    return sorted(term for term in PANIC_TERMS if term in lowered)


def _apportion_minutes(total: int, weights: list[float]) -> list[int]:
    """Split ``total`` minutes across ``weights`` as positive integers that sum to exactly ``total``.

    Uses the largest-remainder (Hamilton) method so rounding never loses or invents
    minutes, then lends one minute to any zero slice (borrowing from the largest slice)
    so every study block stays visible and positive.
    """
    weight_sum = sum(weights) or 1.0
    raw = [total * weight / weight_sum for weight in weights]
    floors = [int(value) for value in raw]
    remainder = total - sum(floors)
    order = sorted(range(len(raw)), key=lambda i: raw[i] - floors[i], reverse=True)
    for offset in range(max(remainder, 0)):
        floors[order[offset % len(order)]] += 1

    # Guarantee no zero-length block while preserving the exact total.
    for index, value in enumerate(floors):
        if value <= 0:
            donor = max(range(len(floors)), key=lambda i: floors[i])
            if floors[donor] > 1:
                floors[donor] -= 1
                floors[index] += 1
    return floors


def time_blocks(minutes: int) -> list[tuple[str, int]]:
    """Return a triage plan whose blocks always sum to the available minutes.

    Blocks are apportioned by weight for the chosen time tier, so 60 minutes yields a
    60-minute plan and 360 minutes yields a 360-minute plan (the old fixed-size tiers
    silently overshot or wasted time outside a couple of values).
    """
    total = max(15, int(minutes or 15))
    if total <= 45:
        labels = ["Reset and choose", "Core recall", "Quick test", "Final sheet"]
        weights = [0.12, 0.62, 0.18, 0.08]
    elif total <= 120:
        labels = ["Reset and rank", "Core pass", "Drill pass", "Patch weak spots", "Final sheet"]
        weights = [0.09, 0.34, 0.30, 0.16, 0.11]
    elif total <= 360:
        labels = ["Reset and rank", "Core pass", "Practice loop", "Break", "Weak-topic patch", "Final sheet"]
        weights = [0.05, 0.26, 0.30, 0.07, 0.22, 0.10]
    else:
        labels = ["Today plan", "Core pass", "Practice loop", "Break", "Second pass", "Final sheet"]
        weights = [0.08, 0.24, 0.26, 0.06, 0.24, 0.12]
    allocation = _apportion_minutes(total, weights)
    return [(label, block_minutes) for label, block_minutes in zip(labels, allocation)]


def coach_state(blocks: list[tuple[str, int]], elapsed_seconds: float) -> dict:
    """Given a triage schedule and elapsed seconds, return the live-coach state.

    Pure and deterministic so it can be unit-tested without the UI. Returns the current
    block, seconds remaining in it, the next block, and progress, or done=True at the end.
    """
    positive = [(label, mins) for label, mins in blocks if mins > 0]
    total_min = sum(mins for _, mins in positive)
    if total_min <= 0:
        return {"done": True, "current": None, "remaining_s": 0, "next": None,
                "index": 0, "count": 0, "total_s": 0, "elapsed_s": int(elapsed_seconds)}
    elapsed_min = max(0.0, elapsed_seconds) / 60.0
    acc = 0
    for i, (label, mins) in enumerate(positive):
        if elapsed_min < acc + mins:
            remaining_s = int(round((acc + mins - elapsed_min) * 60))
            nxt = positive[i + 1][0] if i + 1 < len(positive) else None
            return {"done": False, "current": label, "remaining_s": remaining_s, "next": nxt,
                    "index": i, "count": len(positive), "total_s": total_min * 60,
                    "elapsed_s": int(elapsed_seconds)}
        acc += mins
    return {"done": True, "current": None, "remaining_s": 0, "next": None,
            "index": len(positive), "count": len(positive), "total_s": total_min * 60,
            "elapsed_s": int(elapsed_seconds)}


def build_prompt(data: StudyInput, topics: list[str]) -> str:
    focus, tactic = FORMAT_WEIGHTS.get(data.exam_format, FORMAT_WEIGHTS["Mixed"])
    return f"""Student: {compact(data.student_name) or "student"}
Subject: {compact(data.subject)}
Time left: {data.time_left_minutes} minutes
Exam format: {data.exam_format}
Format focus: {focus}
Format tactic: {tactic}
Student panic note: {compact(data.panic_note)}
What they know: {compact(data.known_material)}
Extracted topics: {", ".join(topics) if topics else "none"}
Confidence out of 5: {data.confidence}

Return exactly this structure:
5 practice questions:
- ...

4-step survival plan:
1. ...

Write like a calm older student helping under time pressure: direct, human, and a little reassuring without being cheesy.
Use only the provided topics and note when class notes should verify facts. Do not invent syllabus coverage, marks, dates, or outcomes.
Keep formatting clean with short bullets and numbered steps. Do not include analysis, hidden reasoning, chain-of-thought, or <think> tags.
"""


SYSTEM_PROMPT = """You are helping one stressed student recover before an exam.
Do not pretend to know the exact syllabus. Do not guarantee marks.
Use the student's own topics and create practical drills.
Sound human, steady, and specific. Avoid generic productivity advice.
Do not reveal hidden reasoning. Do not write <think> tags. Return only the useful final answer."""


def chat_messages(data: StudyInput, topics: list[str]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(data, topics)},
    ]


def render_generation_payload(generator, data: StudyInput, topics: list[str]):
    """Build the text-generation payload, disabling MiniCPM 'thinking' when possible.

    MiniCPM4.1 is a hybrid reasoning model: left in thinking mode it can spend the whole
    token budget inside a ``<think>`` block, which ``strip_hidden_reasoning`` then discards,
    forcing a silent fallback. We pre-render the chat prompt with ``enable_thinking=False``
    when the tokenizer supports it, and fall back to passing raw messages (the original
    behaviour) on any incompatibility so a working runtime is never broken.
    """
    messages = chat_messages(data, topics)
    tokenizer = getattr(generator, "tokenizer", None)
    if tokenizer is not None and hasattr(tokenizer, "apply_chat_template"):
        for extra in ({"enable_thinking": False}, {}):
            try:
                return tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                    **extra,
                )
            except TypeError:
                continue
            except Exception:
                break
    return messages


@lru_cache(maxsize=1)
def _llama_cpp_model():
    from llama_cpp import Llama

    common_kwargs = {
        "n_ctx": int(os.getenv("LLAMA_CPP_N_CTX", "2048")),
        "n_threads": int(os.getenv("LLAMA_CPP_THREADS", "4")),
        "n_gpu_layers": int(os.getenv("LLAMA_CPP_N_GPU_LAYERS", "0")),
        "verbose": False,
    }
    if not LLAMA_CPP_MODEL_PATH and hasattr(Llama, "from_pretrained"):
        return Llama.from_pretrained(
            repo_id=LLAMA_CPP_REPO_ID,
            filename=LLAMA_CPP_FILENAME,
            **common_kwargs,
        )

    return Llama(
        model_path=LLAMA_CPP_MODEL_PATH,
        **common_kwargs,
    )


@lru_cache(maxsize=2)
def _generator(model_id: str = DEFAULT_MODEL_ID):
    from transformers import AutoTokenizer, pipeline

    kwargs = {
        "task": "text-generation",
        "model": model_id,
        "trust_remote_code": True,
    }
    if model_id == "nvidia/Nemotron-Mini-4B-Instruct":
        kwargs["tokenizer"] = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)

    global TRANSFORMER_DEVICE_NOTE
    try:
        import torch
    except Exception:
        kwargs["device"] = -1
        TRANSFORMER_DEVICE_NOTE = "CPU"
    else:
        if torch.cuda.is_available():
            kwargs["device_map"] = "auto"
            kwargs["torch_dtype"] = torch.bfloat16
            TRANSFORMER_DEVICE_NOTE = "CUDA/ZeroGPU"
        else:
            kwargs["device"] = -1
            TRANSFORMER_DEVICE_NOTE = "CPU"

    return pipeline(**kwargs)


def generated_text_from_pipeline_result(result) -> str:
    if not result:
        return ""
    first = result[0]
    generated = first.get("generated_text", "") if isinstance(first, dict) else first
    if isinstance(generated, list) and generated:
        last = generated[-1]
        if isinstance(last, dict):
            return strip_hidden_reasoning(last.get("content", ""))
    return strip_hidden_reasoning(str(generated))


def generated_text_from_llama_cpp_result(result) -> str:
    if not result:
        return ""
    choices = result.get("choices", [])
    if not choices:
        return ""
    first = choices[0]
    message = first.get("message", {})
    if isinstance(message, dict) and message.get("content"):
        return strip_hidden_reasoning(message.get("content", ""))
    return strip_hidden_reasoning(first.get("text", ""))


def strip_hidden_reasoning(text: str) -> str:
    cleaned = (text or "").replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", " ")
    cleaned = re.sub(r"<think>.*?</think>", " ", cleaned, flags=re.I | re.S)
    if re.search(r"<think\b", cleaned, flags=re.I):
        return ""
    cleaned = re.sub(r"</think>", " ", cleaned, flags=re.I)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines())
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def bool_env(name: str, default: bool = False) -> bool:
    configured = os.getenv(name)
    if configured is None:
        return default
    return configured.strip() in {"1", "true", "True", "yes", "YES"}


def nemotron_fallback_enabled() -> bool:
    return USE_NEMOTRON_FALLBACK and bool(NEMOTRON_FALLBACK_MODEL_ID)


def accelerator_available() -> bool:
    accelerator = os.getenv("ACCELERATOR", "none").strip().lower()
    return accelerator not in {"", "none", "cpu-basic", "cpu-upgrade"}


def is_zero_gpu() -> bool:
    if os.getenv("SPACES_ZERO_GPU"):
        return True
    return os.getenv("ACCELERATOR", "").strip().lower() in {"zero-gpu", "zerogpu", "zero-a10g"}


def should_preload_transformer_model() -> bool:
    # On ZeroGPU the GPU is attached only inside @spaces.GPU calls, so an import-time
    # preload runs with no GPU: it wastes cold-start time and can cache a CPU-bound
    # pipeline. The model loads correctly on the first GPU call instead, so skip it here.
    if is_zero_gpu():
        return False
    configured = os.getenv("PRELOAD_TRANSFORMER_MODEL")
    if configured is not None:
        return bool_env("PRELOAD_TRANSFORMER_MODEL")
    return bool(os.getenv("SPACE_ID")) and accelerator_available()


def maybe_preload_transformer_model() -> None:
    global TRANSFORMER_PRELOAD_NOTE
    if not USE_LOCAL_MODEL or USE_LLAMA_CPP or not should_preload_transformer_model():
        return

    try:
        _generator(DEFAULT_MODEL_ID)
    except Exception as exc:
        TRANSFORMER_PRELOAD_NOTE = f"Transformer preload skipped after error: {exc}"
    else:
        TRANSFORMER_PRELOAD_NOTE = f"Transformer model preloaded on {TRANSFORMER_DEVICE_NOTE}."


maybe_preload_transformer_model()


def llama_cli_available() -> bool:
    return bool(shutil.which(LLAMA_CPP_CLI) or os.path.exists(LLAMA_CPP_CLI))


def llama_cli_source() -> str:
    if LLAMA_CPP_MODEL_PATH:
        return LLAMA_CPP_MODEL_PATH
    return f"{LLAMA_CPP_REPO_ID}:{LLAMA_CPP_HF_SELECTOR}"


def llama_cli_command(prompt: str, max_tokens: int = 260) -> list[str]:
    command = [LLAMA_CPP_CLI]
    if LLAMA_CPP_MODEL_PATH:
        command.extend(["-m", LLAMA_CPP_MODEL_PATH])
    else:
        command.extend(["-hf", llama_cli_source()])

    command.extend(
        [
            "-p",
            prompt,
            "-n",
            str(max_tokens),
            "--temp",
            "0",
            "--single-turn",
            "--simple-io",
            "--no-display-prompt",
            "--log-disable",
        ]
    )

    if os.getenv("LLAMA_CPP_N_CTX", "").strip():
        command.extend(["-c", os.getenv("LLAMA_CPP_N_CTX", "").strip()])
    if os.getenv("LLAMA_CPP_THREADS", "").strip():
        command.extend(["-t", os.getenv("LLAMA_CPP_THREADS", "").strip()])
    if os.getenv("LLAMA_CPP_N_GPU_LAYERS", "").strip():
        command.extend(["-ngl", os.getenv("LLAMA_CPP_N_GPU_LAYERS", "").strip()])
    return command


def generated_text_from_llama_cli_output(output: str, prompt: str = "") -> str:
    text = (output or "").strip()
    if prompt and prompt in text:
        text = text.split(prompt, 1)[1].strip()
    text = re.sub(r"\[\s*Prompt:.*?\]\s*", " ", text, flags=re.S)
    text = text.replace("Exiting...", " ")
    text = re.sub(r"^(>\s*)+", "", text).strip()
    return strip_hidden_reasoning(text)


def llama_cli_rescue(data: StudyInput, topics: list[str]) -> tuple[str | None, str]:
    if not llama_cli_available():
        return None, f"llama-cli runtime not found at `{LLAMA_CPP_CLI}`."

    prompt = build_prompt(data, topics)
    command = llama_cli_command(prompt, max_tokens=int_env("LLAMA_CPP_MAX_TOKENS", 260))
    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=int_env("LLAMA_CPP_TIMEOUT", 120),
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"llama-cli runtime failed: {exc}"

    if result.returncode != 0:
        detail = compact(result.stderr or result.stdout)
        return None, f"llama-cli exited with code {result.returncode}: {detail[:220]}"

    generated = generated_text_from_llama_cli_output(result.stdout, prompt)
    if not generated:
        return None, "llama-cli returned an empty plan."
    return generated, f"Generated locally with llama.cpp CLI model {llama_cli_source()}."


def cohere_review_text_from_response(body: dict) -> str:
    content = body.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return ""

    parts = []
    for item in content:
        if isinstance(item, dict) and item.get("type", "text") == "text":
            text = compact(item.get("text", ""))
            if text:
                parts.append(text)
    return compact(" ".join(parts))


def cohere_quality_review(rescue_plan_markdown: str, drill_markdown: str, triage_markdown: str) -> str | None:
    if not USE_COHERE_REVIEW:
        return None

    api_key = os.getenv("COHERE_API_KEY", "").strip()
    if not api_key:
        return "Cohere quality review requested but COHERE_API_KEY is not set; skipped."

    prompt = f"""Review this exam rescue packet for specificity, calm tone, and actionability.
Return one short line that starts with "Cohere quality check:".

{rescue_plan_markdown}

{drill_markdown}

{triage_markdown}
"""
    payload = {
        "model": COHERE_MODEL,
        "messages": [
            {"role": "system", "content": "You are a strict one-line quality reviewer for student study plans."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 80,
        "temperature": 0.2,
        "safety_mode": "CONTEXTUAL",
    }
    request = urllib.request.Request(
        COHERE_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Client-Name": "exam-panic-rescue",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = compact(exc.read().decode("utf-8"))
        except Exception:
            detail = compact(str(exc))
        return f"Cohere quality review unavailable: HTTP {exc.code} {detail[:160]}"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return f"Cohere quality review unavailable: {exc}"

    review = cohere_review_text_from_response(body)
    return review or "Cohere quality review returned no text."


def transformer_rescue(model_id: str, data: StudyInput, topics: list[str]) -> tuple[str | None, str]:
    try:
        generator = _generator(model_id)
        result = generator(
            render_generation_payload(generator, data, topics),
            max_new_tokens=int_env("MODEL_MAX_NEW_TOKENS", 520),
            do_sample=False,
            return_full_text=False,
        )
    except Exception as exc:
        details = str(exc)
        if model_id == DEFAULT_MODEL_ID and TRANSFORMER_PRELOAD_NOTE:
            details = f"{details} | {TRANSFORMER_PRELOAD_NOTE}"
        return None, f"{model_id} unavailable: {details}"

    generated = generated_text_from_pipeline_result(result)
    if not generated:
        return None, f"{model_id} returned an empty plan."
    size = model_size_label(model_id)
    label = f"{model_id} ({size})" if size else model_id
    return generated, f"Generated with {label} on {TRANSFORMER_DEVICE_NOTE}."


def model_rescue(data: StudyInput, topics: list[str], model_id: str | None = None) -> tuple[str | None, str]:
    if not USE_LOCAL_MODEL:
        return None, LOCAL_MODEL_DISABLED_NOTE

    if USE_LLAMA_CPP:
        backend = LLAMA_CPP_BACKEND if LLAMA_CPP_BACKEND in {"auto", "cli", "python"} else "auto"
        notes = []

        if backend in {"auto", "cli"}:
            generated, cli_note = llama_cli_rescue(data, topics)
            if generated:
                return generated, cli_note
            notes.append(cli_note)
            if backend == "cli":
                return None, f"Using fallback study engine because llama.cpp CLI was unavailable: {cli_note}"

        if backend in {"auto", "python"}:
            try:
                llama = _llama_cpp_model()
                if hasattr(llama, "create_chat_completion"):
                    result = llama.create_chat_completion(
                        messages=chat_messages(data, topics),
                        max_tokens=260,
                        temperature=0.0,
                    )
                else:
                    result = llama(
                        build_prompt(data, topics),
                        max_tokens=260,
                        temperature=0.0,
                        stop=["\n\nStudent:", "\nSubject:"],
                    )
            except Exception as exc:
                notes.append(f"llama-cpp-python unavailable: {exc}")
                return None, "Using fallback study engine because llama.cpp was unavailable: " + " | ".join(notes)
            generated = generated_text_from_llama_cpp_result(result)
            if not generated:
                return None, "llama.cpp returned an empty plan; fallback used."
            source = LLAMA_CPP_MODEL_PATH or f"{LLAMA_CPP_REPO_ID}:{LLAMA_CPP_FILENAME}"
            return generated, f"Generated locally with llama-cpp-python model {source}."

    primary = (model_id or "").strip() or DEFAULT_MODEL_ID
    generated, note = transformer_rescue(primary, data, topics)
    if not generated:
        if nemotron_fallback_enabled() and primary != NEMOTRON_FALLBACK_MODEL_ID:
            fallback_generated, fallback_note = transformer_rescue(NEMOTRON_FALLBACK_MODEL_ID, data, topics)
            if fallback_generated:
                return fallback_generated, fallback_note.replace(" on ", " fallback on ", 1)
            return None, f"Using fallback study engine because primary and Nemotron fallback models were unavailable: {note} | {fallback_note}"
        return None, f"Using fallback study engine because {note}; fallback used."
    return generated, note


VISION_MODEL_ID = os.getenv("VISION_MODEL_ID", "openbmb/MiniCPM-V-4_5")
VISION_QUESTION = (
    "This is a photo of a student's syllabus, timetable, textbook page, or notes. "
    "List ONLY the exam topics or chapter headings you can see, as a short comma-separated "
    "list. No introduction and no explanation - just the comma-separated topics."
)


def extract_topics_from_image(image_path: str) -> tuple[str, str]:
    """Read a photo of a syllabus/notes with MiniCPM-V and return (topics_text, status_note).

    The vision model is loaded fresh and freed after each call so it never co-resides with the
    text model in memory (both are ~8B and would not fit together). Any failure returns an empty
    string plus a friendly note, so the caller keeps working and the student can just type topics.
    """
    if not image_path:
        return "", "No image provided - upload a photo or type your topics."
    try:
        import torch
        from PIL import Image
        from transformers import AutoModel, AutoTokenizer
    except Exception as exc:  # pragma: no cover - depends on runtime deps
        return "", f"Vision support is unavailable here ({exc}). Type your topics instead."

    model = None
    try:
        image = Image.open(image_path).convert("RGB")
        model = AutoModel.from_pretrained(
            VISION_MODEL_ID,
            trust_remote_code=True,
            attn_implementation="sdpa",
            torch_dtype=torch.bfloat16,
        ).eval()
        if torch.cuda.is_available():
            model = model.cuda()
        tokenizer = AutoTokenizer.from_pretrained(VISION_MODEL_ID, trust_remote_code=True)
        answer = model.chat(msgs=[{"role": "user", "content": [image, VISION_QUESTION]}], tokenizer=tokenizer)
        topics = clip_text(compact(answer), 600)
        if not topics:
            return "", "Could not find topics in that photo. Try a clearer image or type them."
        return topics, f"Topics read from your photo with {VISION_MODEL_ID}. Check them before you rely on them."
    except Exception as exc:
        return "", f"Could not read the photo ({type(exc).__name__}). Type your topics instead."
    finally:
        try:
            import gc

            import torch
            if model is not None:
                del model
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass


def fallback_drills(subject: str, topics: list[str], exam_format: str) -> list[str]:
    topic_list = topics or [compact(subject) or "the most likely exam topic"]
    drills = []
    for topic in topic_list[:4]:
        if exam_format == "Long answer":
            drills.append(f"Write a 5-line outline for: {topic}. Include definition, example, and one common mistake.")
        elif exam_format == "Multiple choice":
            drills.append(f"Create 3 traps for {topic}: one true statement, one almost-true statement, and one false statement.")
        elif exam_format == "Short answer":
            drills.append(f"Explain {topic} in 3 sentences, then reduce it to 1 sentence from memory.")
        else:
            drills.append(f"Recall {topic} without notes for 2 minutes, then check your notes and repair the gap.")
    drills.append("Make a final one-page sheet from only the mistakes you made in the drills.")
    return drills[:5]


def detect_weaknesses(panic_note: str) -> list[str]:
    lowered = panic_note.lower()
    weaknesses = []
    if any(word in lowered for word in ["blank", "forget", "forgot"]):
        weaknesses.append("memory blank-out")
    if any(word in lowered for word in ["numerical", "problem", "math"]) or re.search(r"\bsums?\b", lowered):
        weaknesses.append("worked problems")
    if any(word in lowered for word in ["formula", "formulas", "equation"]):
        weaknesses.append("formula recall under pressure")
    if any(word in lowered for word in ["long answer", "essay", "explain"]):
        weaknesses.append("structured answers")
    if any(word in lowered for word in ["mcq", "multiple choice", "options"]):
        weaknesses.append("option traps")
    return weaknesses[:4]


def panic_pattern(data: StudyInput, weaknesses: list[str], panic: list[str]) -> str:
    if data.time_left_minutes <= 60:
        return "emergency recall loop"
    if data.confidence <= 2 and "memory blank-out" in weaknesses:
        return "blank-out spiral"
    if "worked problems" in weaknesses or "formula recall under pressure" in weaknesses:
        return "formula-to-step gap"
    if "structured answers" in weaknesses:
        return "outline-first problem"
    if "option traps" in weaknesses:
        return "trap-rush problem"
    if panic:
        return "confidence collapse"
    return "ordinary triage"


def proof_checklist(exam_format: str, topics: list[str]) -> str:
    lead_topic = topics[0] if topics else "the first high-probability topic"
    if exam_format == "Multiple choice":
        return f"Reject two traps for {lead_topic} before choosing an option."
    if exam_format == "Long answer":
        return f"Write one outline for {lead_topic} before adding memorized facts."
    if exam_format == "Short answer":
        return f"Explain {lead_topic} in one sentence without notes, then repair the missing word."
    return f"Answer one drill on {lead_topic} without notes, then repair one mistake."


def build_final_sheet_html(data: StudyInput, topics: list[str], weaknesses: list[str], blocks: list[tuple[str, int]]) -> str:
    topic_items = topics[:5] or [compact(data.subject) or "highest-probability class headings"]
    weakness_items = weaknesses or ["recent mistakes", "blank spots", "rushed definitions"]
    final_minutes = next((minutes for label, minutes in reversed(blocks) if "Final" in label), 10)
    escaped_topics = "\n".join(f"<li>{escape(topic)}</li>" for topic in topic_items)
    escaped_weaknesses = "\n".join(f"<li>{escape(weakness)}</li>" for weakness in weakness_items)
    first_action = f"First 2 minutes: write everything you remember about {topic_items[0]}, then circle one leak."
    do_not = "Do not reread everything. Protect marks from the listed topics and stop adding new material in the final block."
    if data.time_left_minutes <= 60:
        do_not = "Do not open a new chapter now. Recall, test, patch, and walk in."
    elif data.exam_format == "Multiple choice":
        do_not = "Do not pick an option until you can reject two traps."
    elif data.exam_format == "Long answer":
        do_not = "Do not memorize paragraphs first. Build the outline, then attach facts."
    stop_line = (
        "If you freeze: write the topic, one formula/definition, one worked step, then move."
        if data.exam_format != "Long answer"
        else "If you freeze: write a 5-line outline first, then fill facts from memory."
    )
    proof = proof_checklist(data.exam_format, topic_items)

    return f"""
<section class="final-sheet">
  <div class="sheet-kicker">Last page before the exam</div>
  <h2>Final Sheet for {escape(compact(data.student_name) or "You")}</h2>
  <div class="sheet-grid">
    <div>
      <h3>Protect these marks</h3>
      <ul>{escaped_topics}</ul>
    </div>
    <div>
      <h3>Patch these leaks</h3>
      <ul>{escaped_weaknesses}</ul>
    </div>
  </div>
  <p class="sheet-action">{escape(first_action)}</p>
  <p class="sheet-rule">{escape(stop_line)}</p>
  <p class="sheet-proof"><strong>Proof before stopping:</strong> {escape(proof)}</p>
  <p class="sheet-warning"><strong>Do not do:</strong> {escape(do_not)}</p>
  <p class="sheet-footer">Final pass: {final_minutes} minutes. No new topics in the last block.</p>
</section>
"""


def build_field_note_markdown(data: StudyInput, pattern: str, topics: list[str]) -> str:
    topic = topics[0] if topics else compact(data.subject) or "the first topic"
    return (
        "### Field note prompt\n\n"
        "Use this after the study block if a real student tries the rescue packet:\n\n"
        f"- Before: I felt stuck because of **{pattern}**.\n"
        f"- Action: I spent the first two minutes on **{topic}** and followed the proof target.\n"
        "- Result: My confidence changed from ___/5 to ___/5.\n"
        "- Keep/change: The most useful part was ___; the confusing part was ___.\n\n"
        "Copyable field note:\n\n"
        "```text\n"
        f"Student: {compact(data.student_name) or 'student'}\n"
        f"Subject: {compact(data.subject) or 'exam'}\n"
        f"Panic pattern: {pattern}\n"
        f"First action topic: {topic}\n"
        "Confidence before/after: ___/5 -> ___/5\n"
        "Most useful part: ___\n"
        "Confusing part: ___\n"
        "Would use again? yes / no / maybe\n"
        "```"
    )


def build_demo_receipt_markdown(data: StudyInput, pattern: str, topics: list[str], weaknesses: list[str]) -> str:
    topic = topics[0] if topics else compact(data.subject) or "the first high-probability topic"
    weakness = weaknesses[0] if weaknesses else "the first visible leak"
    proof = proof_checklist(data.exam_format, topics)
    return (
        "### Study receipt\n\n"
        f"- Before: {compact(data.student_name) or 'student'} starts at **{data.confidence}/5** confidence with **{pattern}**.\n"
        f"- First move: attack **{topic}** instead of rereading everything.\n"
        f"- Leak to patch: **{weakness}**.\n"
        f"- Proof of work: **{proof}**\n"
        "- Practical fit: one student, one exam window, one useful artifact, no required cloud key."
    )


MAX_INPUT_CHARS = 2000


def clip_text(text: str, limit: int = MAX_INPUT_CHARS) -> str:
    """Trim oversized pasted input so prompts and model context stay bounded."""
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip()


_DRILL_QUESTION_HEADER = re.compile(r"(?im)^[^\n]*practice\s+questions?[^\n]*$")
_DRILL_PLAN_HEADER = re.compile(r"(?im)^[^\n]*survival\s+plan[^\n]*$")


def _clean_bullet(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[-*•]\s+", "", line)
    line = re.sub(r"^\d+[.)]\s+", "", line)
    return line.strip()


def split_model_plan_and_drills(generated: str) -> tuple[str, list[str]]:
    """Separate the model's survival-plan prose from its practice questions.

    Returns ``(plan_text, drill_questions)``. When the expected headers are missing we
    return the whole text as the plan and no drills, so the deterministic drill templates
    stay in charge rather than guessing from unstructured output.
    """
    text = (generated or "").strip()
    if not text:
        return "", []

    question_header = _DRILL_QUESTION_HEADER.search(text)
    plan_header = _DRILL_PLAN_HEADER.search(text)

    drills: list[str] = []
    if question_header:
        q_start = question_header.end()
        q_end = plan_header.start() if (plan_header and plan_header.start() > q_start) else len(text)
        for raw_line in text[q_start:q_end].splitlines():
            item = _clean_bullet(raw_line)
            if len(item) >= 6 and not _DRILL_PLAN_HEADER.match(item):
                drills.append(item)

    if plan_header:
        plan_text = text[plan_header.start():].strip()
    elif question_header:
        plan_text = text[:question_header.start()].strip() or text
    else:
        plan_text = text

    return plan_text, drills[:5]


def packet_to_markdown(rescue: str, drill: str, triage: str, final_sheet_html: str, receipt: str) -> str:
    """Assemble the generated packet into a clean, printable Markdown document."""
    fs_text = re.sub(r"<[^>]+>", "\n", final_sheet_html or "")
    fs_text = "\n".join(line.strip() for line in fs_text.splitlines() if line.strip())
    sections = [
        "# Exam Panic Rescue - your study packet",
        "",
        (rescue or "").strip(),
        "",
        (drill or "").strip(),
        "",
        (triage or "").strip(),
        "",
        "### Final sheet",
        fs_text,
        "",
        (receipt or "").strip(),
        "",
        "_Generated by Exam Panic Rescue. Always verify facts against your own class notes._",
    ]
    return "\n".join(sections).strip() + "\n"


def build_rescue_plan(
    student_name: str,
    subject: str,
    time_left_minutes: int,
    exam_format: str,
    panic_note: str,
    known_material: str,
    confidence: int,
    force_fallback: bool = False,
    model_id: str | None = None,
) -> StudyPlan:
    data = StudyInput(
        student_name=clip_text(student_name, 120),
        subject=clip_text(subject, 300),
        time_left_minutes=int(time_left_minutes or 60),
        exam_format=exam_format,
        panic_note=clip_text(panic_note),
        known_material=clip_text(known_material),
        confidence=int(confidence or 1),
    )
    topics = extract_study_topics(data.known_material, data.panic_note)
    panic = detect_panic(data.panic_note)
    weaknesses = detect_weaknesses(data.panic_note)
    pattern = panic_pattern(data, weaknesses, panic)
    focus, tactic = FORMAT_WEIGHTS.get(exam_format, FORMAT_WEIGHTS["Mixed"])
    blocks = time_blocks(data.time_left_minutes)
    if force_fallback:
        generated, note = None, "Deterministic fallback used for reliability (model path skipped)."
    else:
        try:
            generated, note = model_rescue(data, topics, model_id=model_id)
        except Exception as exc:  # a model-path error must never crash the whole packet
            generated, note = None, (
                f"Using fallback study engine after a model-path error "
                f"({type(exc).__name__}: {str(exc)[:160]}); fallback used."
            )

    try:
        model_plan_text, model_drills = split_model_plan_and_drills(generated) if generated else ("", [])
    except Exception:
        model_plan_text, model_drills = (generated or ""), []

    if model_plan_text:
        rescue_body = model_plan_text
    else:
        name = compact(data.student_name) or "You"
        topic_text = ", ".join(topics[:4]) if topics else "the highest-probability topics from your class notes"
        weak_text = ", ".join(weaknesses) if weaknesses else "the exact place you lose marks"
        rescue_body = (
            f"{name}, stop trying to study everything. Your job is to protect marks from {topic_text}.\n\n"
            f"1. Spend the first block making a tiny hit list of what can actually appear.\n"
            f"2. Attack {weak_text} with {focus} practice because this is a {exam_format.lower()} exam.\n"
            f"3. Turn every wrong answer into one line on a final sheet.\n"
            f"4. In the last block, read only that sheet and stop adding new topics."
        )

    if len(model_drills) >= 3:
        drills = list(model_drills[:5])
        for template_drill in fallback_drills(subject, topics, exam_format):
            if len(drills) >= 5:
                break
            drills.append(template_drill)
        drill_source = "model-written drills"
    else:
        drills = fallback_drills(subject, topics, exam_format)
        drill_source = "built-in template drills"

    note = f"{note} Drill source: {drill_source}."

    rescue_plan_markdown = "### Rescue plan\n\n" + rescue_body
    drill_markdown = "### Drill deck\n\n" + "\n".join(f"- {drill}" for drill in drills)
    triage_lines = [
        f"- Panic pattern: {pattern}",
        f"- Format focus: {focus} - {tactic}",
        f"- Confidence: {data.confidence}/5",
        f"- Panic signals: {', '.join(panic) if panic else 'none detected'}",
        f"- Weaknesses to attack: {', '.join(weaknesses) if weaknesses else 'none named; start from recent mistakes'}",
        f"- Topics extracted: {', '.join(topics) if topics else 'none; start with your class headings'}",
        f"- Proof target: {proof_checklist(data.exam_format, topics)}",
    ]
    skip = topics[3:6] if len(topics) > 3 else []
    if skip:
        triage_lines.append(
            f"- If time runs out, drop these first: {', '.join(skip)} "
            "(you listed them later; keep them only if you know they are high-value)."
        )
    triage_lines.extend(f"- {label}: {minutes} min" for label, minutes in blocks if minutes > 0)
    triage_lines.append("- Boundary: verify facts with your class notes; this app plans the rescue, it does not replace the syllabus.")
    triage_markdown = "### Triage clock\n\n" + "\n".join(triage_lines)
    final_sheet_html = build_final_sheet_html(data, topics, weaknesses, blocks)
    demo_receipt_markdown = build_demo_receipt_markdown(data, pattern, topics, weaknesses)
    field_note_markdown = build_field_note_markdown(data, pattern, topics)
    cohere_review = cohere_quality_review(rescue_plan_markdown, drill_markdown, triage_markdown)
    if cohere_review:
        note = f"{note}\n\n{cohere_review}"

    return StudyPlan(
        rescue_plan_markdown,
        drill_markdown,
        triage_markdown,
        final_sheet_html,
        demo_receipt_markdown,
        field_note_markdown,
        note,
    )


DEMO_CASES = [
    {
        "name": "biology panic",
        "student_name": "Mira",
        "subject": "Biology: cell division",
        "time_left_minutes": 45,
        "exam_format": "Short answer",
        "panic_note": "I am scared and keep forgetting definitions.",
        "known_material": "mitosis, meiosis, chromosomes, cytokinesis, cell cycle checkpoints",
        "confidence": 1,
        "must_include": ["mitosis", "definitions"],
    },
    {
        "name": "physics numericals",
        "student_name": "Aarav",
        "subject": "Physics: work, energy, and power",
        "time_left_minutes": 120,
        "exam_format": "Mixed",
        "panic_note": "I go blank in numericals and forget which formula to use.",
        "known_material": "work-energy theorem, kinetic energy, potential energy, conservation of energy",
        "confidence": 2,
        "must_include": ["work-energy theorem", "worked problems"],
    },
    {
        "name": "history long answers",
        "student_name": "Zoya",
        "subject": "History: nationalism in India",
        "time_left_minutes": 1440,
        "exam_format": "Long answer",
        "panic_note": "I know the chapters but my long answers become messy.",
        "known_material": "non-cooperation movement, civil disobedience, salt march, Simon Commission",
        "confidence": 3,
        "must_include": ["non-cooperation movement", "structured answers"],
    },
    {
        "name": "math traps",
        "student_name": "Kabir",
        "subject": "Math: quadratic equations",
        "time_left_minutes": 360,
        "exam_format": "Multiple choice",
        "panic_note": "MCQ options trick me and I rush the formula.",
        "known_material": "factorization, quadratic formula, discriminant, completing the square",
        "confidence": 2,
        "must_include": ["quadratic formula", "option traps"],
    },
]


EXAMPLE_INPUT = {
    "student_name": "Aarav",
    "subject": "Class 11 Physics: work, energy, and power",
    "time_left_minutes": 120,
    "exam_format": "Mixed",
    "panic_note": "I am panicking. I know formulas but go blank in numericals. The test is tomorrow morning.",
    "known_material": "Work-energy theorem, kinetic energy, potential energy, power, conservation of energy",
    "confidence": 2,
}
