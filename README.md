---
title: Exam Panic Rescue
sdk: gradio
app_file: app.py
license: mit
---

# Exam Panic Rescue

Exam Panic Rescue turns a student's last-minute panic dump into a survival plan, drill deck, triage clock, panic-pattern readout, proof target, final sheet, demo receipt, and field-note prompt.

The first target workflow is a student who has an exam soon, feels stuck, and cannot decide what to study first. The app is intentionally narrow: one stressed student, one exam, one time box, one final sheet.

The app includes four built-in panic cases for fast judging: biology definitions, physics numericals, history long answers, and math MCQ traps. These are the same cases used by the local readiness smoke test and published as [data/readiness_cases.jsonl](data/readiness_cases.jsonl). Each run names the likely panic pattern, gives the student one proof target before they stop studying, produces a short demo receipt, and emits a copyable field-note prompt for real-user follow-up.

The public UI includes a small claim-status panel so reviewers can see which claims are ready now, which need a Space/runtime smoke, and which should not be claimed yet.

## Build Status

This is a staging-ready Build Small project in progress. The app is ready for Space smoke testing; final hackathon submission assets still need the public GitHub link, demo video, social post, and verified runtime claims.

Public build notes and demo prep are drafted in [docs/codex-build-trace.md](docs/codex-build-trace.md) and [docs/demo-script.md](docs/demo-script.md).

## Hackathon Fit

- Track: Backyard AI.
- Build surface: Gradio `Blocks` app hosted as a Hugging Face Space.
- Model rule: the default model target is `openbmb/MiniCPM4.1-8B`, under the `<=32B` limit.
- OpenAI Codex track: built with Codex; public GitHub repo link should be added here before final submission.
- OpenBMB angle: the default local model path targets `openbmb/MiniCPM4.1-8B`.
- NVIDIA/local angle: no cloud API dependency; the app can run locally or on Space hardware, with an optional `llama.cpp` path when a GGUF model is available.
- Cohere angle: optional `USE_COHERE_REVIEW=1` quality-review hook, disabled by default so the main demo stays local-first.
- JetBrains angle: documented PyCharm/JetBrains run workflow for app, tests, and readiness checks.
- Off-Brand angle: custom Gradio layout, built-in judge cases, and a printable final-sheet artifact with a first action and a "do not do" guardrail.

See [docs/sponsor-coverage.md](docs/sponsor-coverage.md) for the current sponsor/bonus matrix. Modal is intentionally not part of the product target.

## Codex Track Checklist

- Public GitHub repo with Codex-attributed commits: pending public push.
- Space README links to that repo: pending public URL.
- Hugging Face Space commit history is useful for staging, but the Codex track still needs the separate public GitHub evidence above.
- Demo video shows one student panic dump becoming a rescue plan, drill deck, triage clock, panic pattern, proof target, final sheet, demo receipt, and field-note prompt.
- Before final submission, this README should include the public GitHub URL and the demo/social links should be live.

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
USE_LOCAL_MODEL=0 python app.py
```

Set `USE_LOCAL_MODEL=1` or omit it on the Space to try the OpenBMB/MiniCPM model path.

Optional Gemma override for local comparison:

```bash
MODEL_ID=google/gemma-4-12B-it python app.py
```

Optional local `llama.cpp` mode:

```bash
USE_LLAMA_CPP=1 python app.py
```

By default this targets `openbmb/MiniCPM4.1-8B-GGUF` with `MiniCPM4.1-8B-Q4_K_M.gguf` for `llama-cpp-python`, or `openbmb/MiniCPM4.1-8B-GGUF:Q4_K_M` for direct `llama-cli`.

To force the direct CLI path:

```bash
USE_LLAMA_CPP=1 LLAMA_CPP_BACKEND=cli python app.py
```

To force a local file:

```bash
USE_LLAMA_CPP=1 LLAMA_CPP_MODEL_PATH=/path/to/MiniCPM4.1-8B-Q4_K_M.gguf python app.py
```

Optional Cohere quality review:

```bash
USE_COHERE_REVIEW=1 COHERE_API_KEY=... python app.py
```

This calls Cohere `v2/chat` with `command-a-plus-05-2026` and parses the v2 `message.content[].text` response shape. It stays disabled for the default local-first demo.

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

The full preflight includes external evidence checks, so it will continue to report missing final public links until GitHub, Space, demo, and social assets exist.

See [docs/field-notes.md](docs/field-notes.md) for the public build report draft.
See [docs/development-workflow.md](docs/development-workflow.md) for local and JetBrains/PyCharm run workflows.
See [docs/llama-cpp-runtime.md](docs/llama-cpp-runtime.md) for the optional Llama Champion runtime path.
