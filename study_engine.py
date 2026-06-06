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


def time_blocks(minutes: int) -> list[tuple[str, int]]:
    minutes = max(15, int(minutes or 15))
    if minutes <= 45:
        return [("Reset and choose", 5), ("Core recall", minutes - 15), ("Quick test", 7), ("Final sheet", 3)]
    if minutes <= 120:
        return [("Reset and rank", 8), ("Core pass", 35), ("Drill pass", 35), ("Patch weak spots", minutes - 90), ("Final sheet", 12)]
    if minutes <= 360:
        return [("Reset and rank", 10), ("Core pass", 70), ("Practice loop", 90), ("Break", 15), ("Weak-topic patch", 90), ("Final sheet", 25)]
    return [("Today plan", 45), ("Core pass", 120), ("Practice loop", 120), ("Break", 30), ("Second pass", 120), ("Final sheet", 45)]


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


@lru_cache(maxsize=1)
def _generator():
    from transformers import pipeline

    kwargs = {
        "task": "text-generation",
        "model": DEFAULT_MODEL_ID,
        "trust_remote_code": True,
    }

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
    cleaned = re.sub(r"<think>.*?</think>", " ", text or "", flags=re.I | re.S)
    if re.search(r"<think\b", cleaned, flags=re.I):
        return ""
    cleaned = re.sub(r"</think>", " ", cleaned, flags=re.I)
    return compact(cleaned)


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


def accelerator_available() -> bool:
    accelerator = os.getenv("ACCELERATOR", "none").strip().lower()
    return accelerator not in {"", "none", "cpu-basic", "cpu-upgrade"}


def should_preload_transformer_model() -> bool:
    configured = os.getenv("PRELOAD_TRANSFORMER_MODEL")
    if configured is not None:
        return bool_env("PRELOAD_TRANSFORMER_MODEL")
    return bool(os.getenv("SPACE_ID")) and accelerator_available()


def maybe_preload_transformer_model() -> None:
    global TRANSFORMER_PRELOAD_NOTE
    if not USE_LOCAL_MODEL or USE_LLAMA_CPP or not should_preload_transformer_model():
        return

    try:
        _generator()
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


def model_rescue(data: StudyInput, topics: list[str]) -> tuple[str | None, str]:
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

    try:
        result = _generator()(
            chat_messages(data, topics),
            max_new_tokens=int_env("MODEL_MAX_NEW_TOKENS", 520),
            do_sample=False,
            return_full_text=False,
        )
    except Exception as exc:
        details = str(exc)
        if TRANSFORMER_PRELOAD_NOTE:
            details = f"{details} | {TRANSFORMER_PRELOAD_NOTE}"
        return None, f"Using fallback study engine because {DEFAULT_MODEL_ID} was unavailable: {details}"

    generated = generated_text_from_pipeline_result(result)
    if not generated:
        return None, f"{DEFAULT_MODEL_ID} returned an empty plan; fallback used."
    return generated, f"Generated with {DEFAULT_MODEL_ID} on {TRANSFORMER_DEVICE_NOTE}."


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
    if any(word in lowered for word in ["numerical", "problem", "sum", "math"]):
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


def build_rescue_plan(
    student_name: str,
    subject: str,
    time_left_minutes: int,
    exam_format: str,
    panic_note: str,
    known_material: str,
    confidence: int,
) -> StudyPlan:
    data = StudyInput(
        student_name=student_name,
        subject=subject,
        time_left_minutes=int(time_left_minutes or 60),
        exam_format=exam_format,
        panic_note=panic_note,
        known_material=known_material,
        confidence=int(confidence or 1),
    )
    topics = extract_study_topics(known_material, panic_note)
    panic = detect_panic(panic_note)
    weaknesses = detect_weaknesses(panic_note)
    pattern = panic_pattern(data, weaknesses, panic)
    focus, tactic = FORMAT_WEIGHTS.get(exam_format, FORMAT_WEIGHTS["Mixed"])
    blocks = time_blocks(data.time_left_minutes)
    generated, note = model_rescue(data, topics)

    if generated:
        rescue_body = generated
    else:
        name = compact(student_name) or "You"
        topic_text = ", ".join(topics[:4]) if topics else "the highest-probability topics from your class notes"
        weak_text = ", ".join(weaknesses) if weaknesses else "the exact place you lose marks"
        rescue_body = (
            f"{name}, stop trying to study everything. Your job is to protect marks from {topic_text}.\n\n"
            f"1. Spend the first block making a tiny hit list of what can actually appear.\n"
            f"2. Attack {weak_text} with {focus} practice because this is a {exam_format.lower()} exam.\n"
            f"3. Turn every wrong answer into one line on a final sheet.\n"
            f"4. In the last block, read only that sheet and stop adding new topics."
        )

    rescue_plan_markdown = "### Rescue plan\n\n" + rescue_body
    drill_markdown = "### Drill deck\n\n" + "\n".join(f"- {drill}" for drill in fallback_drills(subject, topics, exam_format))
    triage_lines = [
        f"- Panic pattern: {pattern}",
        f"- Format focus: {focus} - {tactic}",
        f"- Confidence: {data.confidence}/5",
        f"- Panic signals: {', '.join(panic) if panic else 'none detected'}",
        f"- Weaknesses to attack: {', '.join(weaknesses) if weaknesses else 'none named; start from recent mistakes'}",
        f"- Topics extracted: {', '.join(topics) if topics else 'none; start with your class headings'}",
        f"- Proof target: {proof_checklist(data.exam_format, topics)}",
    ]
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
