---
title: Exam Panic Rescue
sdk: gradio
app_file: app.py
python_version: 3.10.13
license: mit
---

# Exam Panic Rescue

Exam Panic Rescue turns a student's last-minute panic dump into a survival plan, drill deck, triage clock, panic-pattern readout, proof target, final sheet, study receipt, and field-note prompt.

The first target workflow is a student who has an exam soon, feels stuck, and cannot decide what to study first. The app is intentionally narrow: one stressed student, one exam, one time box, one final sheet.

The app includes four clearly labeled sample scenarios for quick evaluation: biology definitions, physics numericals, history long answers, and math MCQ traps. They are not claimed as real-user data; they are the same public readiness cases used by the local smoke test and published as [data/readiness_cases.jsonl](data/readiness_cases.jsonl). A real student should replace the sample with their actual exam, topics, and time left before generating a packet.

The public UI keeps the student workflow first and puts build-proof/claim status in a small collapsible section so sponsor evidence does not distract from the product.

## Build Status

This is a staging-ready Build Small project in progress. The public Space is live and smoke-tested at https://huggingface.co/spaces/build-small-hackathon/exam-panic-rescue. Final hackathon submission assets still need the demo video, social post, and verified optional runtime claims.

Public build notes and demo prep are drafted in [docs/codex-build-trace.md](docs/codex-build-trace.md) and [docs/demo-script.md](docs/demo-script.md).

Public GitHub evidence repo: https://github.com/himanshu748/exam-panic-rescue

Hardware note: the hackathon rule allows models up to `<=32B`, but the live Gradio Space hardware still determines what is practical. The public Space is now running on Hugging Face ZeroGPU with `USE_LOCAL_MODEL=1` and `PRELOAD_TRANSFORMER_MODEL=1`. A live smoke on 2026-06-06 generated with `openbmb/MiniCPM4.1-8B` and returned `Generated with openbmb/MiniCPM4.1-8B on CUDA/ZeroGPU.` CPU fallback remains in the code if hardware is switched back.

## How A Student Uses It When Time Is Low

1. Paste the messy panic note and the actual topics they half-know.
2. Let the app extract a short hit list instead of rereading the full syllabus.
3. Follow the drill deck for the highest-value leak first.
4. Use the proof target to decide when to stop drilling.
5. Read only the final sheet in the last block so new chapters do not restart the panic spiral.

## Hackathon Fit

- Track: Backyard AI.
- Build surface: Gradio `Blocks` app hosted as a Hugging Face Space.
- Model rule: the default model target is `openbmb/MiniCPM4.1-8B`, under the `<=32B` limit.
- OpenAI Codex track: built with Codex; public GitHub repo is linked from this Space README.
- OpenBMB angle: the default model path targets `openbmb/MiniCPM4.1-8B`, with a verified ZeroGPU Gradio handler for the live Space path.
- NVIDIA/Nemotron note: not a submitted claim right now because the live default is OpenBMB MiniCPM, not Nemotron. The useful overlap is the no-cloud-API/local-runtime design and optional `llama.cpp` path.
- Cohere note: supporting sponsor only for now; an optional `USE_COHERE_REVIEW=1` hook exists, but the main demo stays local-first and does not claim Cohere usage.
- JetBrains angle: documented PyCharm/JetBrains run workflow for app, tests, and readiness checks.
- Off-Brand angle: custom Gradio layout, clearly labeled sample cases, and a printable final-sheet artifact with a first action and a "do not do" guardrail.
- Best Demo / Community Choice angle: the app now avoids automatic generation, so the live product path is easier to understand in a short video or social post.
- Not claimed: Modal Awards, NVIDIA Nemotron Quest, Tiny Titan, Well-Tuned, or Best Agent unless matching evidence is added.

See [docs/sponsor-coverage.md](docs/sponsor-coverage.md) for the current sponsor/bonus matrix. Modal is intentionally not part of the product target.

## Codex Track Checklist

- Public GitHub repo with Codex-attributed commits: https://github.com/himanshu748/exam-panic-rescue
- Space README links to that repo: ready.
- Hugging Face Space commit history is useful for staging, but the Codex track still needs the separate public GitHub evidence above.
- Demo video shows one student panic dump becoming a rescue plan, drill deck, triage clock, panic pattern, proof target, final sheet, study receipt, and field-note prompt.
- Before final submission, the demo/social links should be live.

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
USE_LOCAL_MODEL=0 python app.py
```

Set `USE_LOCAL_MODEL=1` to try the OpenBMB/MiniCPM model path after the hardware can handle it. On a Hugging Face CPU-only Space, the app defaults to the deterministic fallback unless that flag is explicitly set.

ZeroGPU Space route:

```bash
# Current live Space settings:
# 1. Hardware: ZeroGPU
# 2. Variable: USE_LOCAL_MODEL=1
# 3. Variable: PRELOAD_TRANSFORMER_MODEL=1
```

The generation handler is decorated with `@spaces.GPU(duration=120)`. Hugging Face ZeroGPU currently gives PRO and Team users 40 minutes/day of included GPU quota, so final demo prep should use short smoke runs rather than repeated full generations.

Optional local `llama.cpp` mode:

```bash
USE_LLAMA_CPP=1 python app.py
```

By default this targets `openbmb/MiniCPM4.1-8B-GGUF` with `MiniCPM4.1-8B-Q4_K_M.gguf` for `llama-cpp-python`, or `openbmb/MiniCPM4.1-8B-GGUF:Q4_K_M` for direct `llama-cli`.

To force the direct CLI path:

```bash
USE_LLAMA_CPP=1 LLAMA_CPP_BACKEND=cli python app.py
```

To force a local file, including the verified small OpenBMB MiniCPM4 0.5B GGUF route:

```bash
USE_LLAMA_CPP=1 \
LLAMA_CPP_MODEL_PATH=/path/to/MiniCPM4-0.5B-QAT-Int4_gptq_aware_q4_0.gguf \
python app.py
```

Optional Cohere quality review:

```bash
USE_COHERE_REVIEW=1 COHERE_API_KEY=... python app.py
```

This calls Cohere `v2/chat` with `command-a-plus-05-2026` and parses the v2 `message.content[].text` response shape. It stays disabled for the default local-first demo and should not be treated as a submission claim unless official Cohere-specific criteria appear.

## Validation

```bash
python -m unittest discover -s tests
python scripts/readiness_check.py
```

The readiness cases are public JSONL so reviewers can inspect or reuse the tiny eval seed. They are not a fine-tuning claim by themselves.

Submission preflight:

```bash
python scripts/preflight_check.py
```

The full preflight includes external evidence checks, so it will continue to report missing final public links until the demo video and social assets exist.

See [docs/field-notes.md](docs/field-notes.md) for the public build report draft.
See [docs/development-workflow.md](docs/development-workflow.md) for local and JetBrains/PyCharm run workflows.
See [docs/llama-cpp-runtime.md](docs/llama-cpp-runtime.md) for the optional `llama.cpp` runtime path.
