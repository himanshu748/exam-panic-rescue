from __future__ import annotations

import os
import json
import re
import shutil
import subprocess
import threading
import urllib.error
import urllib.request
from html import escape
from dataclasses import dataclass
from functools import lru_cache


DEFAULT_MODEL_ID = os.getenv("MODEL_ID", "openbmb/MiniCPM-V-4.6")
TRANSFORMER_DEVICE_NOTE = "CPU"
TRANSFORMER_PRELOAD_NOTE = ""
NEMOTRON_FALLBACK_MODEL_ID = os.getenv("NEMOTRON_FALLBACK_MODEL_ID", "nvidia/Nemotron-Mini-4B-Instruct").strip()
USE_NEMOTRON_FALLBACK = os.getenv("USE_NEMOTRON_FALLBACK", "0").strip() in {"1", "true", "True", "yes", "YES"}
USE_LLAMA_CPP = os.getenv("USE_LLAMA_CPP", "0").strip() in {"1", "true", "True"}
LLAMA_CPP_BACKEND = os.getenv("LLAMA_CPP_BACKEND", "auto").strip().lower()
LLAMA_CPP_CLI = os.getenv("LLAMA_CPP_CLI", "llama-cli").strip() or "llama-cli"
LLAMA_CPP_MODEL_PATH = os.getenv("LLAMA_CPP_MODEL_PATH", "").strip()
LLAMA_CPP_REPO_ID = os.getenv("LLAMA_CPP_REPO_ID", "openbmb/MiniCPM4-0.5B-QAT-Int4-GGUF")
LLAMA_CPP_FILENAME = os.getenv("LLAMA_CPP_FILENAME", "MiniCPM4-0.5B-QAT-Int4_gptq_aware_q4_0.gguf")
LLAMA_CPP_HF_SELECTOR = os.getenv("LLAMA_CPP_HF_SELECTOR", "Q4_0").strip() or LLAMA_CPP_FILENAME
USE_COHERE_REVIEW = os.getenv("USE_COHERE_REVIEW", "0").strip() in {"1", "true", "True"}
COHERE_MODEL = os.getenv("COHERE_MODEL", "command-a-plus-05-2026")
COHERE_API_URL = "https://api.cohere.com/v2/chat"

# Known parameter budgets for the small models this app runs, all within the hackathon's
# <=32B ceiling. MiniCPM-V 4.6 is the primary engine (text + vision); Nemotron-Mini-4B is the
# selectable alternate and, at 4B, is the Tiny Titan-eligible (<=4B) path. MiniCPM-V-4_5 stays
# listed so an explicit MODEL_ID=openbmb/MiniCPM-V-4_5 override still reports its true size.
MODEL_PARAM_BUDGETS = {
    "openbmb/MiniCPM-V-4.6": "1.3B",
    "openbmb/MiniCPM-V-4_5": "8B",
    "nvidia/Nemotron-Mini-4B-Instruct": "4B",
    "openbmb/MiniCPM4-0.5B-QAT-Int4-GGUF": "0.5B",
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
        labels = ["Reset: pick first target", "Core pass", "Drill pass", "Patch weak spots", "Final sheet"]
        weights = [0.09, 0.34, 0.30, 0.16, 0.11]
    elif total <= 360:
        labels = ["Reset: pick first target", "Core pass", "Practice loop", "Break", "Patch weak spots", "Final sheet"]
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

    Some MiniCPM chat models can spend the whole
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


_LOADED_TEXT_MODEL_ID = None


def _generator(model_id: str = DEFAULT_MODEL_ID):
    """Return a cached text-generation pipeline, keeping only ONE text model resident.

    ZeroGPU gives us 24 GB. The text models here are up to ~8B (~16 GB in bf16), and the
    vision/voice models already load-and-free themselves each call, so to guarantee we never
    exceed 24 GB we keep a single text model at a time: when the requested model changes, free
    the previous one (clear the cache and empty the CUDA allocator) before building the new one.
    """
    global _LOADED_TEXT_MODEL_ID
    requested = (model_id or "").strip() or DEFAULT_MODEL_ID
    # The resident MiniCPM-V must never co-reside with a text pipeline model (~24 GB ceiling).
    free_resident_vlm()
    if _LOADED_TEXT_MODEL_ID is not None and _LOADED_TEXT_MODEL_ID != requested:
        _build_text_generator.cache_clear()
        try:
            import gc

            import torch
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
    generator = _build_text_generator(requested)
    _LOADED_TEXT_MODEL_ID = requested
    return generator


@lru_cache(maxsize=1)
def _build_text_generator(model_id: str = DEFAULT_MODEL_ID):
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


_PREFETCHED_WEIGHTS: set[str] = set()


def ensure_weights(model_id: str) -> str:
    """Download a model's weights to the local cache on CPU, before any GPU call.

    On ZeroGPU the GPU is only held inside ``@spaces.GPU`` functions and is bound by a
    strict duration budget. A first-use cold download of a multi-GB model *inside* that
    budget can exceed it and get aborted, which forces the deterministic fallback even
    though the model is perfectly capable of running. Prefetching the snapshot here -
    in the main process, with no GPU held and no time budget - means the GPU call only
    pays the fast load-from-cache + generate cost and comfortably fits the window.

    Best-effort and idempotent: a failed prefetch never raises (the model path will
    still attempt its own download), and each repo is only fetched once per process.
    """
    mid = (model_id or "").strip()
    if not mid or mid in _PREFETCHED_WEIGHTS:
        return ""
    # Only prefetch on real model + accelerator environments; skip CPU-only dev and CI
    # so importing or unit-testing the engine never triggers multi-GB downloads.
    if not USE_LOCAL_MODEL or not (is_zero_gpu() or accelerator_available()):
        return ""
    try:
        from huggingface_hub import snapshot_download

        snapshot_download(repo_id=mid)
        _PREFETCHED_WEIGHTS.add(mid)
        return f"prefetched weights for {mid}"
    except Exception as exc:  # network/permission/etc. - non-fatal, GPU path will retry
        return f"weight prefetch skipped for {mid} ({type(exc).__name__})"


# ---------------------------------------------------------------------------
# Resident MiniCPM-V cache.
#
# The original design loaded the VLM fresh and freed it on EVERY call, which kept
# the 24 GB ZeroGPU budget safe but made each warm call pay a ~10-15 s reload. The
# documented ZeroGPU pattern is the opposite: load once in the main process (with
# .cuda(); the `spaces` runtime virtualizes it) and reuse it inside @spaces.GPU
# calls. We do that here for the default MiniCPM-V model only, with one hard rule:
# the resident model is EVICTED before the alternate Nemotron pipeline loads,
# preserving the one-big-model-at-a-time guarantee.
#
# Kill-switch: set the Space variable VLM_RESIDENT=0 to restore the old
# load-fresh-per-call behavior instantly, with no redeploy.
# ---------------------------------------------------------------------------

_VLM_RESIDENT: dict[str, tuple] = {}
_VLM_LOCK = threading.Lock()


def vlm_resident_enabled() -> bool:
    """True when the default MiniCPM-V model should stay resident between calls.

    Only on real accelerator environments (ZeroGPU or a GPU Space) with the local
    model path enabled; local dev and CI never load anything. VLM_RESIDENT=0 turns
    it off without a code change.
    """
    if not bool_env("VLM_RESIDENT", True):
        return False
    return USE_LOCAL_MODEL and (is_zero_gpu() or accelerator_available())


def load_resident_vlm(model_id: str = DEFAULT_MODEL_ID) -> str:
    """Load a MiniCPM-V model once and keep it resident. Never raises.

    Safe to call from a startup thread (warms the model before the first student
    clicks) or lazily from the generation path. Returns a short status string.
    """
    mid = (model_id or "").strip() or DEFAULT_MODEL_ID
    if not vlm_resident_enabled() or not is_minicpm_v(mid):
        return ""
    with _VLM_LOCK:
        if mid in _VLM_RESIDENT:
            return f"{mid} already resident"
        try:
            global TRANSFORMER_DEVICE_NOTE
            import torch

            ensure_weights(mid)
            # helper is a processor (MiniCPM-V 4.6) or a tokenizer (4.5); _run_vlm dispatches.
            model, helper = _load_vlm_fresh(mid)
            if torch.cuda.is_available():
                model = model.cuda()
                TRANSFORMER_DEVICE_NOTE = "CUDA/ZeroGPU"
            _VLM_RESIDENT[mid] = (model, helper)
            return f"resident VLM ready: {mid}"
        except Exception as exc:  # never block the request path on a warmup failure
            return f"resident VLM load failed for {mid} ({type(exc).__name__}); per-call loading stays in effect"


def resident_vlm(model_id: str):
    """Return the resident (model, tokenizer) pair for model_id, or None."""
    if not vlm_resident_enabled():
        return None
    with _VLM_LOCK:
        return _VLM_RESIDENT.get((model_id or "").strip())


def free_resident_vlm() -> None:
    """Evict any resident VLM before a different big model loads (VRAM safety)."""
    with _VLM_LOCK:
        if not _VLM_RESIDENT:
            return
        _VLM_RESIDENT.clear()
    try:
        import gc

        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def classify_gpu_failure(exc: Exception | None) -> str:
    """Map a GPU-path failure to one honest, actionable sentence for the runtime note.

    Used when generation falls back to the deterministic packet, so the student
    learns WHY the model did not run and what actually fixes it. Returns "" when
    there is nothing useful to say.
    """
    msg = (str(exc) if exc else "").strip()
    lowered = msg.lower()
    if not lowered:
        return ""
    if "quota" in lowered or "exceeded" in lowered:
        return (
            "Why the fallback: free ZeroGPU minutes ran out for this visitor. Sign in to "
            "Hugging Face for a larger free quota, wait a few minutes, or switch the model "
            "picker to the 0.5B llama.cpp option (runs on CPU)."
        )
    if "abort" in lowered or "timeout" in lowered or "duration" in lowered:
        return (
            "Why the fallback: the GPU window timed out — usually a one-time cold model "
            "download. Try again now; the next run is much faster."
        )
    if "gpu" in lowered or "cuda" in lowered or "device" in lowered:
        return "Why the fallback: no GPU was available just now (ZeroGPU busy). Try again shortly."
    return f"Why the fallback: {msg[:140]}"


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
    if "minicpm-v" in DEFAULT_MODEL_ID.lower():
        # The default is a vision-language model with its own multimodal path, not the text pipeline.
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


def is_minicpm_v(model_id: str) -> bool:
    """True for any MiniCPM-V vision-language model (generates via a multimodal call, not a text pipeline)."""
    return "minicpm-v" in (model_id or "").lower()


def is_minicpm_v_native(model_id: str) -> bool:
    """True for MiniCPM-V models that use the native transformers API instead of .chat().

    MiniCPM-V 4.6 (and newer) is integrated into transformers (>=5.7) as an
    ``AutoModelForImageTextToText`` + ``AutoProcessor`` model: generation goes through
    ``processor.apply_chat_template(...)`` + ``model.generate(...)``, not the legacy
    ``trust_remote_code`` ``model.chat(msgs=, tokenizer=)`` API that MiniCPM-V-4.5 used.
    We keep BOTH paths so an explicit ``MODEL_ID=openbmb/MiniCPM-V-4_5`` still works.
    """
    lowered = (model_id or "").lower()
    if "minicpm-v" not in lowered:
        return False
    return any(tag in lowered for tag in ("4.6", "4_6", "4-6"))


def _load_pil(image_path: str | None):
    """Best-effort load an RGB PIL image; returns None on any failure (image just omitted)."""
    if not image_path:
        return None
    try:
        from PIL import Image

        return Image.open(image_path).convert("RGB")
    except Exception:
        return None


def _build_vlm_messages(prompt_text: str, image_path: str | None, native: bool) -> list[dict]:
    """Build a one-user-turn message list in the right shape for the chosen MiniCPM-V API.

    Native 4.6 wants typed content parts ({"type": "image"/"text", ...}); the legacy 4.5
    .chat() wants a flat [PIL_image, prompt_text] content list. Either way the image is
    optional, so a text-only rescue plan and a photo-grounded one share one builder.
    """
    image = _load_pil(image_path)
    if native:
        content: list = []
        if image is not None:
            content.append({"type": "image", "image": image})
        content.append({"type": "text", "text": prompt_text})
        return [{"role": "user", "content": content}]
    content = []
    if image is not None:
        content.append(image)
    content.append(prompt_text)
    return [{"role": "user", "content": content}]


def _vlm_chat(model, tokenizer, msgs: list[dict], max_new_tokens: int) -> str:
    """Call a MiniCPM-V .chat() with graceful kwargs fallbacks across model revisions (4.5 path)."""
    out = ""
    for extra in ({"max_new_tokens": max_new_tokens, "sampling": False},
                  {"max_new_tokens": max_new_tokens},
                  {}):
        try:
            out = model.chat(msgs=msgs, tokenizer=tokenizer, **extra)
            break
        except TypeError:
            continue
    return out if isinstance(out, str) else str(out)


def _vlm_generate_native(model, processor, messages: list[dict], max_new_tokens: int,
                         downsample_mode: str = "16x") -> str:
    """Generate with a native MiniCPM-V 4.6 model via apply_chat_template + generate.

    Mirrors the official MiniCPM-V-4.6 transformers recipe (greedy decoding, thinking left
    off by the chat template's default). The image-only kwargs (downsample_mode/max_slice_nums)
    are passed defensively so a text-only call never breaks on an older processor signature.
    """
    import torch

    try:
        inputs = processor.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors="pt",
            downsample_mode=downsample_mode, max_slice_nums=36,
        )
    except TypeError:
        inputs = processor.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors="pt",
        )
    inputs = inputs.to(model.device)

    gen_kwargs = {"max_new_tokens": max_new_tokens, "do_sample": False}
    generated_ids = None
    for extra in ({"downsample_mode": downsample_mode}, {}):
        try:
            with torch.no_grad():
                generated_ids = model.generate(**inputs, **gen_kwargs, **extra)
            break
        except (TypeError, ValueError):
            continue
    if generated_ids is None:
        with torch.no_grad():
            generated_ids = model.generate(**inputs, **gen_kwargs)

    input_ids = inputs["input_ids"]
    trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(input_ids, generated_ids)]
    decoded = processor.batch_decode(
        trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    return decoded[0] if decoded else ""


def _load_vlm_fresh(model_id: str):
    """Load a MiniCPM-V (model, helper) pair on CPU. helper is a processor (4.6) or tokenizer (4.5)."""
    import torch

    if is_minicpm_v_native(model_id):
        from transformers import AutoModelForImageTextToText, AutoProcessor

        model = AutoModelForImageTextToText.from_pretrained(
            model_id, torch_dtype=torch.bfloat16, attn_implementation="sdpa"
        ).eval()
        processor = AutoProcessor.from_pretrained(model_id)
        return model, processor

    from transformers import AutoModel, AutoTokenizer

    model = AutoModel.from_pretrained(
        model_id, trust_remote_code=True, attn_implementation="sdpa", torch_dtype=torch.bfloat16
    ).eval()
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    return model, tokenizer


def _run_vlm(model, helper, messages: list[dict], max_new_tokens: int, model_id: str) -> str:
    """Dispatch a multimodal generation to the right MiniCPM-V API for ``model_id``."""
    if is_minicpm_v_native(model_id):
        return _vlm_generate_native(model, helper, messages, max_new_tokens)
    return _vlm_chat(model, helper, messages, max_new_tokens)


def minicpm_v_complete(prompt_text: str, model_id: str, image_path: str | None = None,
                       max_new_tokens: int = 520) -> str:
    """Generate text with a MiniCPM-V vision-language model via its multimodal API.

    This lets MiniCPM-V 4.6 be the primary engine: it writes the rescue plan/drills from the text
    prompt, and - when a syllabus photo is supplied - reads the image directly in the same
    multimodal call. MiniCPM-V 4.6 runs through the native ``apply_chat_template`` + ``generate``
    path; an explicit ``MODEL_ID=openbmb/MiniCPM-V-4_5`` still uses the legacy ``.chat()`` path.
    Uses the resident model when available (fast path: no reload); otherwise loads fresh and frees
    afterwards to stay within the 24 GB ZeroGPU budget.
    """
    global TRANSFORMER_DEVICE_NOTE
    import torch

    messages = _build_vlm_messages(prompt_text, image_path, is_minicpm_v_native(model_id))

    # Fast path: reuse the resident model (loaded at boot or on a previous call).
    if vlm_resident_enabled():
        if resident_vlm(model_id) is None:
            load_resident_vlm(model_id)
        pair = resident_vlm(model_id)
        if pair is not None:
            model, helper = pair
            if torch.cuda.is_available():
                try:  # ensure the weights are actually on the GPU inside this window
                    if next(model.parameters()).device.type != "cuda":
                        model = model.cuda()
                except Exception:
                    pass
                TRANSFORMER_DEVICE_NOTE = "CUDA/ZeroGPU"
            else:
                TRANSFORMER_DEVICE_NOTE = "CPU"
            return strip_hidden_reasoning(_run_vlm(model, helper, messages, max_new_tokens, model_id))

    model = None
    try:
        model, helper = _load_vlm_fresh(model_id)
        if torch.cuda.is_available():
            model = model.cuda()
            TRANSFORMER_DEVICE_NOTE = "CUDA/ZeroGPU"
        else:
            TRANSFORMER_DEVICE_NOTE = "CPU"
        out = _run_vlm(model, helper, messages, max_new_tokens, model_id)
        return strip_hidden_reasoning(out)
    finally:
        try:
            import gc
            if model is not None:
                del model
            gc.collect()
            import torch as _torch
            if _torch.cuda.is_available():
                _torch.cuda.empty_cache()
        except Exception:
            pass


def transformer_rescue(model_id: str, data: StudyInput, topics: list[str],
                       image_path: str | None = None) -> tuple[str | None, str]:
    # MiniCPM-V is a vision-language model: generate via its .chat() (text, plus the photo if given).
    if is_minicpm_v(model_id):
        try:
            prompt = SYSTEM_PROMPT + "\n\n" + build_prompt(data, topics)
            if image_path:
                prompt = (
                    "A photo of the student's own syllabus or notes is attached. "
                    "Read it and use it together with the details below.\n\n" + prompt
                )
            generated = minicpm_v_complete(
                prompt, model_id, image_path=image_path,
                max_new_tokens=int_env("MODEL_MAX_NEW_TOKENS", 520),
            )
        except Exception as exc:
            return None, f"{model_id} unavailable: {str(exc)[:160]}"
        generated = strip_hidden_reasoning(generated or "")
        if not generated:
            return None, f"{model_id} returned an empty plan."
        size = model_size_label(model_id)
        label = f"{model_id} ({size})" if size else model_id
        source = " (read your photo)" if image_path else ""
        return generated, f"Generated with {label} on {TRANSFORMER_DEVICE_NOTE}{source}."

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


def is_llama_cpp_choice(model_id: str) -> bool:
    """True for the selectable llama.cpp engine (a GGUF model id), which runs on CPU."""
    return "gguf" in (model_id or "").lower()


def llama_cpp_python_rescue(data: StudyInput, topics: list[str]) -> tuple[str | None, str]:
    """Run the rescue generation through the llama.cpp runtime (llama-cpp-python, CPU).

    This is the selectable Llama Champion path: a small GGUF model genuinely runs through
    llama.cpp on the Space. The runtime note names llama-cpp-python so the engine is unambiguous.
    """
    try:
        llama = _llama_cpp_model()
    except Exception as exc:
        return None, f"llama.cpp (llama-cpp-python) unavailable: {str(exc)[:160]}"
    generated = ""
    try:
        result = llama.create_chat_completion(
            messages=chat_messages(data, topics), max_tokens=360, temperature=0.0
        )
        generated = generated_text_from_llama_cpp_result(result)
    except Exception:
        generated = ""
    if not generated:
        try:
            result = llama(
                build_prompt(data, topics), max_tokens=360, temperature=0.0,
                stop=["\n\nStudent:", "\nSubject:"],
            )
            generated = generated_text_from_llama_cpp_result(result)
        except Exception as exc:
            return None, f"llama.cpp generation failed: {str(exc)[:160]}"
    if not generated:
        return None, "llama.cpp returned an empty plan."
    source = LLAMA_CPP_MODEL_PATH or f"{LLAMA_CPP_REPO_ID}:{LLAMA_CPP_FILENAME}"
    size = model_size_label(LLAMA_CPP_REPO_ID)
    label = f"{source} ({size})" if size else source
    return generated, f"Generated locally with llama-cpp-python (llama.cpp runtime), model {label}."


def model_rescue(data: StudyInput, topics: list[str], model_id: str | None = None,
                 image_path: str | None = None) -> tuple[str | None, str]:
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
    if is_llama_cpp_choice(primary):
        generated, note = llama_cpp_python_rescue(data, topics)
        if generated:
            return generated, note
        return None, f"Using fallback study engine because {note}; fallback used."
    generated, note = transformer_rescue(primary, data, topics, image_path=image_path)
    if not generated:
        if nemotron_fallback_enabled() and primary != NEMOTRON_FALLBACK_MODEL_ID:
            fallback_generated, fallback_note = transformer_rescue(NEMOTRON_FALLBACK_MODEL_ID, data, topics)
            if fallback_generated:
                return fallback_generated, fallback_note.replace(" on ", " fallback on ", 1)
            return None, f"Using fallback study engine because primary and Nemotron fallback models were unavailable: {note} | {fallback_note}"
        return None, f"Using fallback study engine because {note}; fallback used."
    return generated, note


def _generic_complete(messages: list[dict], model_id: str, max_new_tokens: int = 480) -> str:
    """Run a one-off chat completion (thinking off). Routes MiniCPM-V via its .chat() API."""
    if is_minicpm_v(model_id):
        prompt = "\n\n".join(m.get("content", "") for m in messages if m.get("content"))
        return minicpm_v_complete(prompt, model_id, image_path=None, max_new_tokens=max_new_tokens)
    generator = _generator(model_id)
    tokenizer = getattr(generator, "tokenizer", None)
    payload = messages
    if tokenizer is not None and hasattr(tokenizer, "apply_chat_template"):
        for extra in ({"enable_thinking": False}, {}):
            try:
                payload = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, **extra)
                break
            except TypeError:
                continue
            except Exception:
                break
    result = generator(payload, max_new_tokens=max_new_tokens, do_sample=False, return_full_text=False)
    return generated_text_from_pipeline_result(result)


def drills_from_markdown(drill_markdown: str) -> list[str]:
    return [re.sub(r"^[-*]\s*", "", ln.strip()) for ln in (drill_markdown or "").splitlines() if ln.strip().startswith("- ")][:5]


def answer_drills(drill_markdown: str, subject: str, model_id: str | None = None) -> tuple[str, str]:
    """Produce a worked answer key for the drills. Falls back to a self-check method if no model."""
    drills = drills_from_markdown(drill_markdown)
    if not drills:
        return "### Worked answers\n\nBuild a packet first, then I can answer your drills.", "No drills yet."
    if USE_LOCAL_MODEL:
        mid = (model_id or "").strip() or DEFAULT_MODEL_ID
        try:
            messages = [
                {"role": "system", "content": "You are a concise exam tutor. Answer each numbered practice question correctly in 1-2 lines. No preamble, no chain-of-thought. Keep the numbering."},
                {"role": "user", "content": f"Subject: {compact(subject)}\nAnswer these, numbered:\n" + "\n".join(f"{i}. {d}" for i, d in enumerate(drills, 1))},
            ]
            text = strip_hidden_reasoning(_generic_complete(messages, mid))
            if text:
                return "### Worked answers\n\n" + text, f"Answers written by {mid}. Always verify against your own notes."
        except Exception:
            pass
    lines = ["### Worked answers — self-check method", "", "Model answers aren't available right now, so grade yourself:"]
    for i, drill in enumerate(drills, 1):
        lines.append(f"{i}. {drill}")
        lines.append("   - Attempt it closed-book, then check your notes and mark it right or wrong. Turn every wrong one into a line on your final sheet.")
    return "\n".join(lines), "Self-check method (model answers unavailable)."


VISION_MODEL_ID = os.getenv("VISION_MODEL_ID", "openbmb/MiniCPM-V-4.6")
VISION_QUESTION = (
    "This is a photo of a student's syllabus, timetable, textbook page, or notes. "
    "List ONLY the exam topics or chapter headings you can see, as a short comma-separated "
    "list. No introduction and no explanation - just the comma-separated topics."
)


def extract_topics_from_image(image_path: str) -> tuple[str, str]:
    """Read a photo of a syllabus/notes with MiniCPM-V and return (topics_text, status_note).

    MiniCPM-V 4.6 reads the image through its native processor + generate path; an explicit
    MiniCPM-V-4_5 override uses the legacy .chat() path. Outside the resident fast path the model
    is loaded fresh and freed after the call so it never co-resides with another big model in
    memory. Any failure returns an empty string plus a friendly note, so the caller keeps working
    and the student can just type topics.
    """
    if not image_path:
        return "", "No image provided - upload a photo or type your topics."
    try:
        import torch  # noqa: F401 - confirm the runtime has torch before loading a model
    except Exception as exc:  # pragma: no cover - depends on runtime deps
        return "", f"Vision support is unavailable here ({exc}). Type your topics instead."

    native = is_minicpm_v_native(VISION_MODEL_ID)
    messages = _build_vlm_messages(VISION_QUESTION, image_path, native)

    # Fast path: the resident model reads the photo with no reload.
    pair = resident_vlm(VISION_MODEL_ID)
    if pair is not None:
        try:
            import torch

            model, helper = pair
            if torch.cuda.is_available():
                try:
                    if next(model.parameters()).device.type != "cuda":
                        model = model.cuda()
                except Exception:
                    pass
            answer = _run_vlm(model, helper, messages, 320, VISION_MODEL_ID)
            topics = clip_text(compact(answer), 600)
            if not topics:
                return "", "Could not find topics in that photo. Try a clearer image or type them."
            return topics, f"Topics read from your photo with {VISION_MODEL_ID}. Check them before you rely on them."
        except Exception as exc:
            return "", f"Could not read the photo ({type(exc).__name__}). Type your topics instead."

    model = None
    try:
        import torch

        model, helper = _load_vlm_fresh(VISION_MODEL_ID)
        if torch.cuda.is_available():
            model = model.cuda()
        answer = _run_vlm(model, helper, messages, 320, VISION_MODEL_ID)
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
    image_path: str | None = None,
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
            generated, note = model_rescue(data, topics, model_id=model_id, image_path=image_path)
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
    cohere_review = cohere_quality_review(rescue_plan_markdown, drill_markdown, triage_markdown)
    if cohere_review:
        note = f"{note}\n\n{cohere_review}"

    return StudyPlan(
        rescue_plan_markdown,
        drill_markdown,
        triage_markdown,
        final_sheet_html,
        demo_receipt_markdown,
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
