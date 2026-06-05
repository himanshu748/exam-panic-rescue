# Sponsor Coverage

Updated: 2026-06-05

This document exists so the project does not drift into bounty soup. Each sponsor angle must either improve the student demo, satisfy a real rule, or stay explicitly out of scope.

The app also shows a compact public claim-status panel with the same philosophy: claim now, claim after smoke, or do not claim yet.

## Current Matrix

| Sponsor or quest | Claim level | Evidence in this project | Remaining gap |
| --- | --- | --- | --- |
| Hugging Face | Claim after staging upload | Gradio app intended for a Space under `build-small-hackathon`; `hf auth whoami` verified `HIMANSHUKUMARJHA` and org access on 2026-06-05; upload package audit includes only public-safe files; local fallback smoke returned HTTP `200`. | Space is not created/uploaded yet. |
| OpenAI Codex | Claim after public GitHub evidence | Codex is being used for app, tests, docs, and iteration; official email recheck confirms entry requires public GitHub/Codex evidence and README repo link before submission. | Public Git repo, Codex-attributed commits, and README repo link are still missing. |
| OpenBMB | Claim now, verify on Space | Default model path is `openbmb/MiniCPM4.1-8B`, under the `<=32B` rule and aligned with OpenBMB/MiniCPM special-prize judging. | Need one Space smoke run with the model path or a clear fallback note if hardware prevents it. |
| NVIDIA | Claim local-first now; claim runtime only after smoke | Local-first, no cloud API dependency, CPU/GPU-friendly fallback, and optional `llama.cpp` GGUF runtime path through either direct `llama-cli` or `llama-cpp-python`. | Need live runtime smoke before making a stronger performance/runtime claim. |
| Cohere | Do not claim live integration yet | Optional `USE_COHERE_REVIEW=1` quality-review hook uses Cohere `v2/chat` with `command-a-plus-05-2026` when `COHERE_API_KEY` is set; response parsing is tested against the official `message.content[].text` v2 shape; default path makes no cloud call. | Needs key and live test before claiming in final materials. |
| JetBrains | Claim workflow support | `docs/development-workflow.md` documents PyCharm/JetBrains run configurations for app, tests, and readiness smoke without committing `.idea/` noise. | Not a standalone sponsor bounty unless official criteria appear. |
| Black Forest Labs | Claim visual/delight support only | The app produces a visual final-sheet artifact with first action, proof target, and guardrail, plus a compact demo receipt; this supports visual/delight judging without changing the core workflow. | Do not imply BFL API/model usage. |
| Modal | Do not claim | Intentionally not targeted because the user rejected Modal as credit-only. | None. |
| Off the Grid | Claim only with cloud hooks disabled | Local processing by default; no external API key required for the demo. Cohere/Gemma/llama.cpp modes are explicit opt-ins. | Verify final Space path does not require external calls. |
| Off-Brand | Claim now | Custom Gradio CSS/HTML, built-in judge cases, 90-second demo path rail, panic-pattern readout, demo receipt, and a final-sheet card with first-action, proof target, and guardrail sections rather than default UI. | Repeat final visual QA after staging upload. |
| Llama Champion | Do not claim yet | Optional `USE_LLAMA_CPP=1` backend now supports direct `llama-cli` via `LLAMA_CPP_BACKEND=cli` and `openbmb/MiniCPM4.1-8B-GGUF:Q4_K_M`, plus `llama-cpp-python` with `MiniCPM4.1-8B-Q4_K_M.gguf`; internal checker verifies config and honest fallback. | Needs live llama.cpp runtime test before claiming. |
| Well-Tuned | Do not claim yet | Public `data/readiness_cases.jsonl` mirrors the app/test judge cases and can seed a tiny eval or future fine-tune experiment. | Needs real data, a published fine-tuned model, and a reason beyond badge-chasing before claiming. |
| Sharing is Caring | Claim after public links | Public-safe build trace exists in `docs/codex-build-trace.md`. | Need public trace after repo/Space are stable. |
| Field Notes | Claim after final public report pass | `docs/field-notes.md` and `docs/demo-script.md` are drafted; the app exposes the same four panic cases used by readiness smoke, publishes them as JSONL, emits a demo receipt, and emits a copyable field-note prompt for real-user follow-up. | Needs final screenshots, failures, metrics, user result notes, and public links. |

## Submission Rule

Before final submission, remove or soften any claim that lacks public evidence. A weaker but honest sponsor matrix is better than a stuffed app that judges cannot trust.
