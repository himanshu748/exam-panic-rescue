# Field Notes

Project: Exam Panic Rescue

## User Problem

Students often hit a point before an exam where they are not really studying anymore. They are rereading everything, switching topics, panicking, and losing the last useful hours.

The first target workflow is a student who has a test soon and can only describe the situation as a messy panic dump: what they half-know, what scares them, and how much time is left. The app now names the panic pattern, gives one proof target, keeps the final artifact focused on stopping the spiral, produces a demo receipt for the before/after, and emits a copyable field-note prompt so real-user feedback can be captured after the study block.

## Hackathon Fit

- Track: Backyard AI.
- Core app: Gradio Space.
- Model constraint: default model target is `openbmb/MiniCPM4.1-8B`, well under the `<=32B` rule.
- Sponsor target: OpenAI Codex track through Codex-built repo history and README linkage.
- OpenBMB fit: the default small-model path uses `openbmb/MiniCPM4.1-8B` for plan generation when available.
- NVIDIA/local fit: the app has no cloud API dependency and can run with local or Space hardware, with optional `llama.cpp` support. A small TinyLlama GGUF smoke passed through the CLI path; OpenBMB MiniCPM GGUF still needs a non-fallback smoke before claiming Llama Champion.

## Bonus Quests

- Off-Brand: custom Gradio Blocks layout and CSS.
- Off-Brand evidence: the app includes built-in panic cases, a demo receipt, collapsed claim proof, and a final-sheet artifact with first-action, proof-before-stopping, and "Do not do" guardrails.
- Sharing is Caring: publish the Codex trace or build log before final submission.
- Field Notes: this document becomes the concise public report, backed by the app's copyable field-note prompt.
- Well-Tuned runway: `data/readiness_cases.jsonl` is a small public eval seed, but not a fine-tune claim.
- Off the Grid: the app attempts local model inference and has no cloud API dependency.
- Llama Champion: possible later through `USE_LLAMA_CPP=1`; local `llama-cli` is installed and the app-level TinyLlama GGUF smoke passed, but the OpenBMB GGUF path still needs a non-fallback generation smoke before claiming.

## Validation Plan

- Local unit test: `python -m unittest discover -s tests`
- Demo case smoke: `python scripts/readiness_check.py`
- The same biology, physics, history, and math smoke cases are exposed in the app under "Try another panic case".
- The same cases are published as JSONL at `data/readiness_cases.jsonl` so reviewers can inspect the tiny eval set.
- Local app smoke: `USE_LOCAL_MODEL=0 python app.py`
- Space smoke: run once with the default model path and confirm the model note reports `openbmb/MiniCPM4.1-8B`.

## Submission Checklist

- Public GitHub repo contains Codex-attributed commits.
- Space README links to the public GitHub repo.
- Short demo video shows one panic dump becoming a rescue plan, drill deck, triage clock, panic-pattern readout, proof target, final sheet, demo receipt, and field-note prompt.
- Social post links to the Space and names the Backyard AI track.
