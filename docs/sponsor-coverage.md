# Sponsor Coverage

Updated: 2026-06-06

This document exists so the project does not drift into bounty soup. Each sponsor angle must either improve the student demo, satisfy a real rule, or stay explicitly out of scope.

The app keeps the product demo first and puts claim-status proof in a compact collapsible section with the same philosophy: claim now, claim after smoke, or do not claim yet.

Official recheck on 2026-06-06 still points to Backyard AI as the best main track: the app targets a concrete student panic problem, while Thousand Token Wood is optimized for delightful/strange AI-first experiences. The awards page now frames `29` separate awards across main tracks, sponsor awards, and special awards. Modal remains intentionally excluded.

## Current Matrix

| Award or sponsor | Claim level | Evidence in this project | Remaining gap |
| --- | --- | --- | --- |
| Backyard AI | Primary target | The product solves a concrete low-time study panic workflow for students, with a one-input/one-packet path and visible proof target. This is stronger than Thousand Token Wood because usefulness is the core, not a playful AI toy. | Need one real student/use-case note if possible before final Field Notes claim. |
| Thousand Token Wood | Do not target as main | The app has polish and a bit of delight, but it is not a strange toy/game/story. | Do not dilute the submission by pretending this is the main fit. |
| Community Choice | Secondary target | The product is relatable to students and easy to understand in a short social post. | Needs demo/social packaging that feels useful, humble, and shareable. |
| Hugging Face | Claim now for staging | Gradio Space is live under `build-small-hackathon` at https://huggingface.co/spaces/build-small-hackathon/exam-panic-rescue; upload package audit includes only public-safe files; live Space smoke passed root/config/marker checks. The app is running on ZeroGPU with `spaces` and `@spaces.GPU(duration=120)`. | Final submission still needs demo/social links. |
| OpenAI Codex | Claim public evidence now | Public GitHub repo exists with Codex-attributed commits at https://github.com/himanshu748/exam-panic-rescue, and the Space README links it. The official page now lists an OpenAI Track podium across all submissions. | Final submission still needs demo/social assets and final claim review. |
| OpenBMB | Claim live ZeroGPU generation now | Default model path is `openbmb/MiniCPM4.1-8B`, under the `<=32B` rule and aligned with OpenBMB/MiniCPM special-prize judging. A live ZeroGPU smoke on 2026-06-06 returned `Generated with openbmb/MiniCPM4.1-8B on CUDA/ZeroGPU.` | Preserve the CPU fallback and avoid spending the 40 min/day quota on unnecessary repeated tests. |
| NVIDIA Nemotron Quest | Do not claim yet | The official award is for standout Nemotron builds. This app defaults to OpenBMB MiniCPM, but an optional `nvidia/Nemotron-Mini-4B-Instruct` fallback exists behind `USE_NEMOTRON_FALLBACK=1`. | Revisit only after a real Nemotron fallback smoke passes and final materials show it without distracting from OpenBMB. |
| Cohere | Do not target unless criteria appear | Cohere is currently tracked as a supporting sponsor/cash contributor, not a confirmed model-use bounty. Optional `USE_COHERE_REVIEW=1` quality-review hook exists and stays disabled by default; response parsing is tested against the official `message.content[].text` v2 shape. | No product work needed now. Do not spend demo surface on Cohere or claim live integration unless official criteria appear and a key-backed smoke passes. |
| JetBrains | Claim workflow support | `docs/development-workflow.md` documents PyCharm/JetBrains run configurations for app, tests, and readiness smoke without committing `.idea/` noise. | Not a standalone sponsor bounty unless official criteria appear. |
| Black Forest Labs | Claim visual/delight support only | The app produces a visual final-sheet artifact with first action, proof target, and guardrail, plus a compact study receipt; this supports visual/delight judging without changing the core workflow. | Do not imply BFL API/model usage. |
| Modal | Do not claim | Intentionally not targeted because the user rejected Modal as credit-only. | None. |
| Off-Brand | Claim now | Custom Gradio CSS/HTML, clearly labeled sample scenarios, panic-pattern readout, study receipt, a final-sheet card with first-action/proof-target/guardrail sections, and collapsed claim proof rather than a default Gradio layout. | Repeat final visual QA before final submission. |
| Tiny Titan | Do not claim for main Space | The live default model is `openbmb/MiniCPM4.1-8B`, which is not `<=4B`. | Could only claim with a real <=4B default or demo path, but that may weaken OpenBMB 8B quality. |
| Best Demo | Strong target after links | The product has a clear before/after story and visible final sheet; the no-auto-generation flow makes the live demo more reliable. | Needs uploaded demo video and social post URL. |
| Best Agent | Do not claim strongly | The app is a structured rescue workflow, not a true multi-step autonomous agent. | Avoid calling it agentic unless the judging definition allows workflow agents and we add evidence. |
| Judges' Wildcard | Passive upside | Honest, polished, practical, and student-relatable can still fit the wildcard if judges like it. | Do not optimize for wildcard directly. |
| Bonus Quest Champion | Target 5 of 6 | Off-Brand is strong; no-cloud-API design is preserved with Cohere disabled; Field Notes are public-drafted; Sharing is Caring is backed by public app traces at https://huggingface.co/datasets/build-small-hackathon/exam-panic-rescue-build-trace; optional `llama.cpp` evidence exists for the fifth path. | Do not chase Well-Tuned with fake data. Show `llama.cpp` in final materials before claiming all five. |

## Submission Rule

Before final submission, remove or soften any claim that lacks public evidence. A weaker but honest sponsor matrix is better than a stuffed app that judges cannot trust.
