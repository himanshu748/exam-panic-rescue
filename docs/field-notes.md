# Field Notes

Project: Exam Panic Rescue

## User Problem

Students often hit a point before an exam where they are not really studying anymore. They are rereading everything, switching topics, panicking, and losing the last useful hours.

The first target workflow is a student who has a test soon and can only describe the situation as a messy panic dump: what they half-know, what scares them, and how much time is left. The app now names the panic pattern, gives one proof target, keeps the final artifact focused on stopping the spiral, produces a study receipt for the before/after, and emits a copyable field-note prompt so real-user feedback can be captured after the study block.

Current product stance from user feedback on 2026-06-06: optimize for students like us, practical usefulness, and a live product feel. The demo should prove the product, not become the product. The visible tone should be humble and honest, while the build process quietly does the sponsor/evidence work needed to win.

## Hackathon Fit

- Track: Backyard AI.
- Core app: Gradio Space.
- Model constraint: default model target is `openbmb/MiniCPM4.1-8B`, well under the `<=32B` rule.
- Sponsor target: OpenAI Codex track through Codex-built repo history and README linkage.
- OpenBMB fit: the default small-model path uses `openbmb/MiniCPM4.1-8B` for plan generation when available.
- NVIDIA/Nemotron honesty: the app does not currently claim the Nemotron Quest because the default live model is OpenBMB MiniCPM. An optional `nvidia/Nemotron-Mini-4B-Instruct` fallback path exists behind `USE_NEMOTRON_FALLBACK=1`; claim it only after a real fallback smoke is shown. The useful overlap today is no-cloud-API design plus optional local/`llama.cpp` support.
- Runtime honesty: CPU-only Hugging Face Spaces use the deterministic fallback by default; the current live Space is on ZeroGPU and a 2026-06-06 model-backed smoke returned `Generated with openbmb/MiniCPM4.1-8B on CUDA/ZeroGPU.` GGUF routes should still be shown only after a matching llama.cpp smoke.

## What Changed During Build

- Chose a relatable student panic workflow instead of a generic productivity assistant.
- Kept the app small: one panic dump in, one rescue packet out.
- Added a model-budget strip so judges can see that `<=32B` is a rule ceiling, while free CPU Space hardware still needs an honest fallback.
- Replaced the overflowing examples table with four large panic-case buttons after visual QA showed the table made the demo feel like a spreadsheet.
- Added mobile code wrapping after visual QA showed the copyable field-note block could overflow on a 390px viewport.

## Bonus Quests

- Off-Brand: custom Gradio Blocks layout and CSS.
- Off-Brand evidence: the app includes clearly labeled sample scenarios, a study receipt, collapsed claim proof, and a final-sheet artifact with first-action, proof-before-stopping, and "Do not do" guardrails.
- Sharing is Caring: public-safe app traces are published at https://huggingface.co/datasets/build-small-hackathon/exam-panic-rescue-build-trace.
- Field Notes: this document becomes the concise public report, backed by the app's copyable field-note prompt.
- Fine-tuning runway: `data/readiness_cases.jsonl` is a small public eval seed, but not a fine-tune claim.
- No-cloud-API runway: the app attempts local model inference and has no required external API key.
- Optional `llama.cpp` runway: possible later through `USE_LLAMA_CPP=1`; local `llama-cli` is installed and the app-level OpenBMB MiniCPM4 0.5B GGUF smoke passed. Claim only if final demo/materials explicitly use or show that route.
- Five-quest target: Off-Brand, no-cloud-API design, Field Notes, Sharing is Caring, and optional `llama.cpp`. Skip Well-Tuned unless real data and a real fine-tuned model appear.

## Validation Plan

- Local unit test: `python -m unittest discover -s tests`
- Demo case smoke: `python scripts/readiness_check.py`
- The same biology, physics, history, and math smoke cases are exposed in the app under "Try a sample scenario".
- The same cases are published as JSONL at `data/readiness_cases.jsonl` so reviewers can inspect the tiny eval seed. They are not presented as real-user outcomes.
- Local app smoke: `USE_LOCAL_MODEL=0 python app.py`
- Space smoke: run once and confirm the model note is truthful: either it reports `openbmb/MiniCPM4.1-8B` on CUDA/ZeroGPU-capable hardware or a CPU-only fallback note on free/basic hardware.

Latest verified checks on 2026-06-05:

- Unit tests: `18/18`.
- Demo readiness smoke: `28/28`.
- Staging readiness: `11/11`.
- Codex evidence check: `10/10`.
- Local Space smoke: `4/4`.
- Live Space smoke: `4/4`.
- Full preflight: `26` passed, `3` expected external evidence blockers.

## Submission Checklist

- Public GitHub repo contains Codex-attributed commits.
- Space README links to the public GitHub repo.
- Short demo video shows one panic dump becoming a rescue plan, drill deck, triage clock, panic-pattern readout, proof target, final sheet, study receipt, and field-note prompt.
- Social post links to the Space and names the Backyard AI track.
