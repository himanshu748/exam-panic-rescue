# Sponsor Coverage

Updated: 2026-06-06

This document exists so the project does not drift into bounty soup. Each sponsor angle must either improve the student demo, satisfy a real rule, or stay explicitly out of scope.

The app keeps the product demo first and puts claim-status proof in a compact collapsible section with the same philosophy: claim now, claim after smoke, or do not claim yet.

Official recheck on 2026-06-06 still points to Backyard AI as the best main track: the app targets a concrete student panic problem, while Thousand Token Wood is optimized for delightful/strange AI-first experiences. The awards page now frames `29` separate awards across main tracks, sponsor awards, and special awards. Modal remains intentionally excluded.

## Current Matrix

| Sponsor or quest | Claim level | Evidence in this project | Remaining gap |
| --- | --- | --- | --- |
| Backyard AI | Primary target | The product solves a concrete low-time study panic workflow for students, with a one-input/one-packet path and visible proof target. This is stronger than Thousand Token Wood because usefulness is the core, not a playful AI toy. | Need one real student/use-case note if possible before final Field Notes claim. |
| Thousand Token Wood | Do not target as main | The app has polish and a bit of delight, but it is not a strange toy/game/story. | Do not dilute the submission by pretending this is the main fit. |
| Community Choice | Secondary target | The product is relatable to students and easy to understand in a short social post. | Needs demo/social packaging that feels useful, humble, and shareable. |
| Hugging Face | Claim now for staging | Gradio Space is live under `build-small-hackathon` at https://huggingface.co/spaces/build-small-hackathon/exam-panic-rescue; upload package audit includes only public-safe files; live Space smoke passed root/config/marker checks. The app is running on ZeroGPU with `spaces` and `@spaces.GPU(duration=120)`. | Final submission still needs demo/social links. |
| OpenAI Codex | Claim public evidence now | Public GitHub repo exists with Codex-attributed commits at https://github.com/himanshu748/exam-panic-rescue, and the Space README links it. The official page now lists an OpenAI Track podium across all submissions. | Final submission still needs demo/social assets and final claim review. |
| OpenBMB | Claim live ZeroGPU generation now | Default model path is `openbmb/MiniCPM4.1-8B`, under the `<=32B` rule and aligned with OpenBMB/MiniCPM special-prize judging. A live ZeroGPU smoke on 2026-06-06 returned `Generated with openbmb/MiniCPM4.1-8B on CUDA/ZeroGPU.` | Preserve the CPU fallback and avoid spending the 40 min/day quota on unnecessary repeated tests. |
| NVIDIA Nemotron Quest | Do not claim | The official award is for standout Nemotron builds. This app defaults to OpenBMB MiniCPM, not Nemotron. | Only revisit if we add and smoke a genuine Nemotron path, which is not currently worth the product distraction. |
| Cohere | Do not target unless criteria appear | Cohere is currently tracked as a supporting sponsor/cash contributor, not a confirmed model-use bounty. Optional `USE_COHERE_REVIEW=1` quality-review hook exists and stays disabled by default; response parsing is tested against the official `message.content[].text` v2 shape. | No product work needed now. Do not spend demo surface on Cohere or claim live integration unless official criteria appear and a key-backed smoke passes. |
| JetBrains | Claim workflow support | `docs/development-workflow.md` documents PyCharm/JetBrains run configurations for app, tests, and readiness smoke without committing `.idea/` noise. | Not a standalone sponsor bounty unless official criteria appear. |
| Black Forest Labs | Claim visual/delight support only | The app produces a visual final-sheet artifact with first action, proof target, and guardrail, plus a compact study receipt; this supports visual/delight judging without changing the core workflow. | Do not imply BFL API/model usage. |
| Modal | Do not claim | Intentionally not targeted because the user rejected Modal as credit-only. | None. |
| Off the Grid | Claim only with cloud hooks disabled | Local processing by default; no external API key required for the demo. Optional model/runtime hooks are explicit opt-ins, and CPU-only HF Spaces use the deterministic fallback by default. ZeroGPU MiniCPM still uses HF-hosted Space hardware, not a third-party API key. | Verify final Space path does not require external calls. |
| Off-Brand | Claim now | Custom Gradio CSS/HTML, clearly labeled sample scenarios, panic-pattern readout, study receipt, a final-sheet card with first-action/proof-target/guardrail sections, and collapsed claim proof rather than a default Gradio layout. | Repeat final visual QA before final submission. |
| Llama Champion | Local evidence ready; final claim conditional | Optional `USE_LLAMA_CPP=1` backend supports direct `llama-cli` via `LLAMA_CPP_BACKEND=cli`; `python3 scripts/llama_runtime_check.py` passes; an official OpenBMB MiniCPM4 0.5B GGUF local-file route produced a non-fallback `Generated locally with llama.cpp CLI` model note. | Claim in final submission only if the demo/materials explicitly use or show the GGUF route. |
| Well-Tuned | Do not claim yet | Public `data/readiness_cases.jsonl` mirrors the app/test judge cases and can seed a tiny eval or future fine-tune experiment. | Needs real data, a published fine-tuned model, and a reason beyond badge-chasing before claiming. |
| Sharing is Caring | Claim after final public links | Public-safe build trace exists in `docs/codex-build-trace.md` and is linked from the Space README. | Need final demo/social links before treating it as final public trace. |
| Field Notes | Claim after final public report pass | `docs/field-notes.md` and `docs/demo-script.md` are drafted; the app exposes the same four sample cases used by readiness smoke, publishes them as JSONL, emits a study receipt, and emits a copyable field-note prompt for real-user follow-up. The sample cases are not presented as field data. | Needs final screenshots, failures, metrics, user result notes, and public links. |
| Bonus Quest Champion | Conditional target | Off-Brand is strong; Off the Grid is defensible only with cloud hooks disabled; Sharing is Caring and Field Notes are close once public links exist; Llama Champion has local evidence but should be claimed only if shown. | Do not chase Well-Tuned or badges that require fake data. |
| Tiny Titan | Do not claim for main Space | The live default model is `openbmb/MiniCPM4.1-8B`, which is not `<=4B`. | Could only claim with a real <=4B default or demo path, but that may weaken OpenBMB 8B quality. |
| Best Demo | Strong target after links | The product has a clear before/after story and visible final sheet; the no-auto-generation flow makes the live demo more reliable. | Needs uploaded demo video and social post URL. |
| Best Agent | Do not claim strongly | The app is a structured rescue workflow, not a true multi-step autonomous agent. | Avoid calling it agentic unless the judging definition allows workflow agents and we add evidence. |
| Judges' Wildcard | Passive upside | Honest, polished, practical, and student-relatable can still fit the wildcard if judges like it. | Do not optimize for wildcard directly. |

## Submission Rule

Before final submission, remove or soften any claim that lacks public evidence. A weaker but honest sponsor matrix is better than a stuffed app that judges cannot trust.
