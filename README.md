---
title: Exam Panic Rescue
emoji: 🆘
colorFrom: green
colorTo: yellow
sdk: gradio
sdk_version: 6.0.1
app_file: app.py
python_version: 3.10.13
license: mit
short_description: Last-minute exam rescue on small models (≤32B)
tags:
  - backyard-ai
  - build-small-hackathon
  - education
  - study
  - openbmb
  - minicpm
  - nemotron
  - zerogpu
models:
  - openbmb/MiniCPM-V-4_5
  - openbmb/VoxCPM2
  - nvidia/Nemotron-Mini-4B-Instruct
---

# Exam Panic Rescue

Exam Panic Rescue turns a student's last-minute panic dump into a survival plan, drill deck, triage clock, panic-pattern readout, proof target, final sheet, study receipt, and field-note prompt.

The first target workflow is a student who has an exam soon, feels stuck, and cannot decide what to study first. The app is intentionally narrow: one stressed student, one exam, one time box, one final sheet.

The app includes four clearly labeled sample scenarios for quick evaluation: biology definitions, physics numericals, history long answers, and math MCQ traps. They are not claimed as real-user data; they are the same public readiness cases used by the local smoke test and published as [data/readiness_cases.jsonl](data/readiness_cases.jsonl). A real student should replace the sample with their actual exam, topics, and time left before generating a packet.

The public UI keeps the student workflow first. The build is documented separately in [docs/build-report.md](docs/build-report.md) and the public build-trace dataset, so the product page stays focused on the student rather than on sponsor evidence.

## Build Status

The public Space is live on Hugging Face ZeroGPU at https://huggingface.co/spaces/build-small-hackathon/exam-panic-rescue and has been verified end-to-end (text, vision, voice, the Nemotron engine, and the answer key all returning real model output).

Real-user validation (Backyard AI): a final-year university Machine Learning student used the live app the day before their exam, and one of the model-written drills closely matched a question that actually appeared on the exam. The anonymized session (with consent) is published in the build-trace dataset under the `real_user` config.

Submission assets:

- Demo video: recorded (49.6s walkthrough).
- Social post (X thread, Backyard AI): live at https://x.com/jhahimanshu653/status/2063909355217453142
- Build report / Field Notes ("what I built and what I learned"): [docs/build-report.md](docs/build-report.md) — also hosted in the org at https://huggingface.co/spaces/build-small-hackathon/exam-panic-rescue-field-notes
- Open build traces (incl. the real-user session): https://huggingface.co/datasets/build-small-hackathon/exam-panic-rescue-build-trace

Public build notes and demo prep are drafted in [docs/codex-build-trace.md](docs/codex-build-trace.md) and [docs/demo-script.md](docs/demo-script.md).

Public GitHub evidence repo: https://github.com/himanshu748/exam-panic-rescue

Hardware note: the hackathon rule allows models up to `<=32B`. The public Space runs on Hugging Face ZeroGPU (24 GB) with `USE_LOCAL_MODEL=1`, loading **one model at a time** so it always fits in memory:

- **OpenBMB MiniCPM-V-4.5** — the primary engine. It writes the rescue plan and drills, and (being a vision-language model) can read a photo of the student's syllabus directly in the same call.
- **NVIDIA Nemotron-Mini-4B** — a selectable text-only alternate; at 4B it is the Tiny Titan (`<=4B`) path.
- **OpenBMB VoxCPM2** — reads the final sheet aloud.

The on-screen runtime note always reports exactly which model ran and on what hardware. Weights are prefetched on CPU before the GPU call so a cold first use does not time out, and a deterministic CPU fallback keeps the packet complete if a model is unavailable.

## How A Student Uses It When Time Is Low

1. Paste the messy panic note and the actual topics they half-know.
2. Let the app extract a short hit list instead of rereading the full syllabus.
3. Follow the drill deck for the highest-value leak first.
4. Use the proof target to decide when to stop drilling.
5. Read only the final sheet in the last block so new chapters do not restart the panic spiral.

## Hackathon Fit

- Track: Backyard AI.
- Build surface: Gradio `Blocks` app hosted as a Hugging Face Space.
- Model rule: the default engine is `openbmb/MiniCPM-V-4_5` (~8B), well under the `<=32B` limit.
- OpenAI Codex track: built with Codex; public GitHub repo is linked from this Space README.
- OpenBMB angle: two OpenBMB models cover three capabilities live — `MiniCPM-V-4.5` writes the plan/drills and reads a syllabus photo (text + vision), and `VoxCPM2` reads the final sheet aloud (voice).
- NVIDIA/Nemotron: `nvidia/Nemotron-Mini-4B-Instruct` is a selectable text engine in the UI; at 4B it doubles as the Tiny Titan (`<=4B`) path. MiniCPM-V-4.5 remains the default.
- Cohere note: supporting sponsor only for now; an optional `USE_COHERE_REVIEW=1` hook exists, but the main demo stays local-first and does not claim Cohere usage.
- JetBrains angle: documented PyCharm/JetBrains run workflow for app, tests, and readiness checks.
- Off-Brand angle: custom Gradio layout, clearly labeled sample cases, and a printable final-sheet artifact with a first action and a "do not do" guardrail.
- Best Demo / Community Choice angle: the app now avoids automatic generation, so the live product path is easier to understand in a short video or social post.
- Targetable with live evidence: NVIDIA Nemotron (selectable engine), Tiny Titan (≤4B — Nemotron-Mini-4B is the selectable ≤4B engine). Not claimed: Modal Awards (intentionally excluded), Well-Tuned (no real fine-tune), or Best Agent unless matching evidence is added.
- Bonus quests: Off-Brand (custom UI), Field Notes (public build report), and Sharing is Caring (public build-trace dataset, incl. the anonymized real-user session).
- Public app trace dataset: https://huggingface.co/datasets/build-small-hackathon/exam-panic-rescue-build-trace

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
```

The generation handler is decorated with `@spaces.GPU(duration=120)`. Hugging Face ZeroGPU currently gives PRO and Team users 40 minutes/day of included GPU quota, so final demo prep should use short smoke runs rather than repeated full generations.

### Choosing a model

The default engine is `openbmb/MiniCPM-V-4_5` — a vision-language model that writes the rescue plan and drills and can read a photo of the syllabus directly in the same call. The Advanced panel also offers `nvidia/Nemotron-Mini-4B-Instruct`, a text-only engine that, at 4B, is the Tiny Titan (`<=4B`) path. Override the default with `MODEL_ID`:

```bash
MODEL_ID=nvidia/Nemotron-Mini-4B-Instruct USE_LOCAL_MODEL=1 python app.py
```

Whatever runs, the on-screen runtime note reports the exact model and size (for example, `Generated with openbmb/MiniCPM-V-4_5 (8B) on CUDA/ZeroGPU`), so the model that produced the plan is never ambiguous. When the model writes valid drills they are used directly; otherwise the app falls back to built-in template drills so the packet is always complete.

Read-aloud uses `openbmb/VoxCPM2`. Each model is loaded one at a time and freed after use, so the app stays within the 24 GB ZeroGPU budget regardless of which features the student uses.

## Validation

```bash
python -m unittest discover -s tests
python scripts/readiness_check.py
```

The readiness cases are public JSONL so reviewers can inspect or reuse the tiny eval seed. They are not a fine-tuning claim by themselves.

These two commands are the public validation path. Deeper submission/evidence checks live in
internal scripts that are intentionally kept out of the public repo (see `.hfignore`), so they are
not part of what reviewers need to run.

See [docs/field-notes.md](docs/field-notes.md) for the public build report draft.
See [data/app_traces_public.jsonl](data/app_traces_public.jsonl) for public-safe app traces with inputs, generated outputs, validation flags, and privacy labels.
The same app trace dataset is mirrored on Hugging Face at https://huggingface.co/datasets/build-small-hackathon/exam-panic-rescue-build-trace.
See [docs/development-workflow.md](docs/development-workflow.md) for local and JetBrains/PyCharm run workflows.
