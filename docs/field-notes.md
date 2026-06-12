# Field Notes

Project: Exam Panic Rescue

## User Problem

Students often hit a point before an exam where they are not really studying anymore. They are rereading everything, switching topics, panicking, and losing the last useful hours.

The first target workflow is a student who has a test soon and can only describe the situation as a messy panic dump: what they half-know, what scares them, and how much time is left. The app names the panic pattern, gives one proof target, keeps the final artifact focused on stopping the spiral, provides a live coach for each study block, and produces a study receipt for the before/after.

Field Notes are judge-facing evidence only. They are intentionally not a visible app output, not part of the generated packet, and not a task for the student during panic mode.

## Hackathon Fit

- Track: Backyard AI.
- Core app: Gradio Space.
- Model constraint: default model target is `openbmb/MiniCPM-V-4_5`, under the `<=32B` rule.
- Sponsor target: OpenAI Codex track through Codex-built repo history and README linkage.
- OpenBMB fit: the default small-model path uses OpenBMB MiniCPM for text and syllabus-photo understanding when hardware is available.
- NVIDIA/Nemotron honesty: `nvidia/Nemotron-Mini-4B-Instruct` is selectable in the UI and should only be claimed with matching smoke evidence.
- Runtime honesty: CPU-only Hugging Face Spaces use the deterministic fallback by default; the current live Space is on ZeroGPU and model notes report exactly which engine ran.

## What Changed During Build

- Chose a relatable student panic workflow instead of a generic productivity assistant.
- Kept the app small: one panic dump in, one rescue packet out.
- Added a model-budget strip so judges can see that `<=32B` is a rule ceiling, while free CPU Space hardware still needs an honest fallback.
- Replaced the overflowing examples table with four large panic-case buttons after visual QA showed the table made the demo feel like a spreadsheet.
- Renamed the opaque reset block to `Reset: pick first target`.
- Upgraded the live coach from a simple countdown into a local deterministic companion with the current action, proof/stop condition, next block preview, manual advance, and a 20-second panic reset.
- Removed the old app-level reflection prompt from the student flow so the product does not ask for evidence while the student is trying to study.

## Bonus Quests

- Off-Brand: custom Gradio Blocks layout and CSS.
- Off-Brand evidence: the app includes clearly labeled sample scenarios, a study receipt, collapsed claim proof, and a final-sheet artifact with first-action, proof-before-stopping, and "Do not do" guardrails.
- Field Notes: this document is the concise public report for judges.
- Sharing is Caring: public-safe app traces are published at https://huggingface.co/datasets/build-small-hackathon/exam-panic-rescue-build-trace.
- Fine-tuning runway: `data/readiness_cases.jsonl` is a small public eval seed, but not a fine-tune claim.
- No-cloud-API runway: the app attempts local model inference and has no required external API key.
- Optional `llama.cpp` runway: possible through `USE_LLAMA_CPP=1`; local `llama-cli` is installed and the app-level OpenBMB MiniCPM4 0.5B GGUF smoke passed. Claim only if final demo/materials explicitly use or show that route.

## Validation Plan

- Local unit test: `python -m unittest discover -s tests`
- Demo case smoke: `python scripts/readiness_check.py`
- The same biology, physics, history, and math smoke cases are exposed in the app under "Try a sample scenario".
- The same cases are published as JSONL at `data/readiness_cases.jsonl` so reviewers can inspect the tiny eval seed. They are not presented as real-user outcomes.
- Local app smoke: `USE_LOCAL_MODEL=0 python app.py`
- Space smoke: run once and confirm the model note is truthful: either it reports model-backed OpenBMB MiniCPM output on CUDA/ZeroGPU-capable hardware or a CPU-only fallback note on free/basic hardware.

Latest verified checks on 2026-06-12:

- Unit tests: `46/46`.
- Demo readiness smoke: `24/24`.
- Staging readiness: `11/11`.
- Codex evidence check: `10/10`.
- Local Space smoke: `4/4`.
- Local browser smoke: generated the physics sample, advanced the coach manually, opened panic reset, confirmed study receipt/runtime, and confirmed no field-note prompt in the UI.

## Submission Checklist

- Public GitHub repo contains Codex-attributed commits.
- Space README links to the public GitHub repo.
- Demo video shows one panic dump becoming a rescue plan, drill deck, triage clock, panic-pattern readout, proof target, live coach, final sheet, and study receipt.
- Field Notes stay in public docs for judges, not in the student UI.
- Social post links to the Space and names the Backyard AI track.
