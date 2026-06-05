# Sponsor Coverage

Updated: 2026-06-05

This document exists so the project does not drift into bounty soup. Each sponsor angle must either improve the student demo, satisfy a real rule, or stay explicitly out of scope.

The app keeps the product demo first and puts claim-status proof in a compact collapsible section with the same philosophy: claim now, claim after smoke, or do not claim yet.

## Current Matrix

| Sponsor or quest | Claim level | Evidence in this project | Remaining gap |
| --- | --- | --- | --- |
| Hugging Face | Claim now for staging | Gradio Space is live under `build-small-hackathon` at https://huggingface.co/spaces/build-small-hackathon/exam-panic-rescue; upload package audit includes only public-safe files; live Space smoke passed root/config/marker checks. | Final submission still needs demo/social links. |
| OpenAI Codex | Claim public evidence now | Public GitHub repo exists with Codex-attributed commits at https://github.com/himanshu748/exam-panic-rescue, and the Space README links it. | Final submission still needs demo/social assets and final claim review. |
| OpenBMB | Claim now, verify generation on Space | Default model path is `openbmb/MiniCPM4.1-8B`, under the `<=32B` rule and aligned with OpenBMB/MiniCPM special-prize judging. | Need one manual Space demo run with the model path or a clear fallback note if hardware prevents it. |
| NVIDIA | Claim local-first now; claim model runtime only after smoke | Local-first, no cloud API dependency, CPU/GPU-friendly fallback, and optional `llama.cpp` GGUF runtime path through either direct `llama-cli` or `llama-cpp-python`. Homebrew `llama-cli` and `llama-server` are installed locally, and an app-level TinyLlama GGUF smoke produced a non-fallback `llama.cpp CLI` model note. | Need MiniCPM GGUF non-fallback smoke before making a stronger OpenBMB/runtime claim. |
| Cohere | Do not claim live integration yet | Optional `USE_COHERE_REVIEW=1` quality-review hook uses Cohere `v2/chat` with `command-a-plus-05-2026` when `COHERE_API_KEY` is set; response parsing is tested against the official `message.content[].text` v2 shape; default path makes no cloud call. | Needs key and live test before claiming in final materials. |
| JetBrains | Claim workflow support | `docs/development-workflow.md` documents PyCharm/JetBrains run configurations for app, tests, and readiness smoke without committing `.idea/` noise. | Not a standalone sponsor bounty unless official criteria appear. |
| Black Forest Labs | Claim visual/delight support only | The app produces a visual final-sheet artifact with first action, proof target, and guardrail, plus a compact demo receipt; this supports visual/delight judging without changing the core workflow. | Do not imply BFL API/model usage. |
| Modal | Do not claim | Intentionally not targeted because the user rejected Modal as credit-only. | None. |
| Off the Grid | Claim only with cloud hooks disabled | Local processing by default; no external API key required for the demo. Cohere/Gemma/llama.cpp modes are explicit opt-ins. | Verify final Space path does not require external calls. |
| Off-Brand | Claim now | Custom Gradio CSS/HTML, built-in panic cases, panic-pattern readout, demo receipt, a final-sheet card with first-action/proof-target/guardrail sections, and collapsed claim proof rather than a default Gradio layout. | Repeat final visual QA before final submission. |
| Llama Champion | Do not claim yet | Optional `USE_LLAMA_CPP=1` backend now supports direct `llama-cli` via `LLAMA_CPP_BACKEND=cli` and `openbmb/MiniCPM4.1-8B-GGUF:Q4_K_M`; `python3 scripts/llama_runtime_check.py` passes with installed Homebrew `llama.cpp`; an app-level TinyLlama GGUF override produced a non-fallback `Generated locally with llama.cpp CLI` model note. | Needs MiniCPM GGUF non-fallback generation through llama.cpp before claiming the final app as Llama Champion. |
| Well-Tuned | Do not claim yet | Public `data/readiness_cases.jsonl` mirrors the app/test judge cases and can seed a tiny eval or future fine-tune experiment. | Needs real data, a published fine-tuned model, and a reason beyond badge-chasing before claiming. |
| Sharing is Caring | Claim after final public links | Public-safe build trace exists in `docs/codex-build-trace.md` and is linked from the Space README. | Need final demo/social links before treating it as final public trace. |
| Field Notes | Claim after final public report pass | `docs/field-notes.md` and `docs/demo-script.md` are drafted; the app exposes the same four panic cases used by readiness smoke, publishes them as JSONL, emits a demo receipt, and emits a copyable field-note prompt for real-user follow-up. | Needs final screenshots, failures, metrics, user result notes, and public links. |

## Submission Rule

Before final submission, remove or soften any claim that lacks public evidence. A weaker but honest sponsor matrix is better than a stuffed app that judges cannot trust.
