# Codex Build Trace

Updated: 2026-06-06

Purpose: public build trace for the Sharing is Caring bonus quest and OpenAI Codex track evidence. It records what changed, why the app stayed small, and which claims are already backed by code or tests.

## Problem Choice

We chose Exam Panic Rescue because the problem is relatable and specific: a student close to an exam is not calmly studying anymore; they are switching topics, rereading notes, and losing the last useful time window to panic.

Rejected directions:

- Generic AI productivity tools: too broad for Backyard AI.
- Modal-credit-only direction: intentionally not targeted so the app stays focused on the student workflow.
- Pure visual/toy concepts: useful as backup for Thousand Token Wood, but weaker than a real student rescue workflow.

## Product Shape

Input:

- Student name.
- Exam subject.
- Panic dump.
- Syllabus, notes, or weak topics.
- Exam format.
- Confidence.
- Minutes left.

Output:

- Rescue plan.
- Drill deck.
- Triage clock.
- Panic-pattern readout.
- Proof target.
- Final sheet.
- Study receipt.
- Field note prompt.
- Model/runtime note.

The app stays intentionally narrow: one stressed student, one exam, one time box.

## Sponsor Strategy

- Hugging Face: Gradio Space under `build-small-hackathon`.
- OpenAI Codex: Codex-assisted app, tests, docs, and iteration trace; final submission needs public GitHub evidence.
- OpenBMB: default model target is `openbmb/MiniCPM4.1-8B`.
- NVIDIA: local-first/no-cloud default with small-model/GPU-friendly framing.
- Cohere: supporting sponsor only for now; optional quality-review hook exists but is disabled by default and not a final claim target unless criteria appear.
- JetBrains: reproducible PyCharm/JetBrains workflow docs.
- Black Forest Labs: visual/delight support through the final-sheet artifact.
- Modal: intentionally excluded by user preference.

## Codex Iterations

1. Selected Exam Panic Rescue over less relatable ideas.
2. Built a Gradio Blocks app with custom UI rather than default Gradio styling.
3. Added deterministic fallback planning so the demo works without a cloud API or model download.
4. Added tests for topic extraction, panic detection, weakness detection, final sheet generation, study receipt generation, Cohere default-off behavior, and llama.cpp result parsing.
5. Switched the default model strategy back to OpenBMB/MiniCPM after the user correctly noted OpenBMB should be default for that prize angle.
6. Added optional sponsor hooks without making them default dependencies.
7. Added private readiness gates so staging, final submission, and sponsor claims are not mixed up.
8. Added a panic-pattern/proof-target layer so outputs feel less generic and more like a real student rescue.
9. Tightened the public sponsor matrix into claim levels so final materials can distinguish "ready now" from "needs live smoke."
10. Added a public claim-status panel in the Gradio UI so judges can see claim discipline without reading private docs.
11. Added a fast review path rail and per-run study receipt so the before/after is visible without narration.
12. Added a model-budget strip and CPU-only Space fallback guard so the demo distinguishes the `<=32B` rule ceiling from practical HF hardware.
13. Replaced the default Gradio Examples table with compact panic-case buttons after visual QA found the table overflowed and distracted from the product.
14. Added mobile code wrapping after visual QA found the copyable field-note block could overflow on a 390px viewport.
15. Removed visible Gemma/comparison-model copy and focused the public app/video story on OpenBMB MiniCPM, with stronger typography and contrast for screenshot/video readability.
16. Added a ZeroGPU-ready Gradio path using `spaces` plus `@spaces.GPU(duration=120)` so the Space can smoke MiniCPM within the available quota after hardware is switched from `cpu-basic`.
17. Shifted visible UI language from judge-demo framing to a student-first product framing: build your rescue packet, follow the low-time learning packet, and keep hackathon proof collapsed.
18. Switched the live Space to ZeroGPU, set `USE_LOCAL_MODEL=1` and `PRELOAD_TRANSFORMER_MODEL=1`, and verified a live MiniCPM response. A follow-up sanitizer removed `<think>` leakage before the final ZeroGPU smoke was accepted.
19. Removed automatic generation on page load and sample-button clicks so the Space only spends ZeroGPU quota after a user explicitly builds a packet. Public copy now labels bundled cases as review samples, not real-user field data.

## Current Evidence

- Local compile passes.
- Unit tests pass across `18` cases.
- Readiness smoke scores `28/28`.
- Local Gradio smoke returned HTTP `200` after the latest UI/output pass.
- Space package audit includes `15` public-safe files and now requires the public build trace, demo script, field notes, development workflow, llama.cpp plan, and sponsor matrix.
- Space smoke checker verifies the public claim-status and student-first product markers in the served app.
- Hugging Face CLI auth verified `HIMANSHUKUMARJHA` and `build-small-hackathon`.
- Public GitHub repo exists with Codex-attributed commits: https://github.com/himanshu748/exam-panic-rescue
- Public Hugging Face Space is published and live-smoke-tested: https://huggingface.co/spaces/build-small-hackathon/exam-panic-rescue
- Live Space runtime smoke passed root HTTP `200`, Gradio `/config` HTTP `200`, required public markers, and no obvious private/internal markers.
- Optional `llama.cpp` CLI app path produced non-fallback model notes with TinyLlama GGUF and an official OpenBMB MiniCPM4 0.5B GGUF local-file route.
- CPU-only Hugging Face Space runtime now defaults to deterministic fallback unless `USE_LOCAL_MODEL=1` is explicitly set after hardware is upgraded or a small GGUF path is configured.
- Hugging Face Space API check on 2026-06-06 reports current/requested hardware as `zero-a10g`.
- Live ZeroGPU generation smoke on 2026-06-06 returned `Generated with openbmb/MiniCPM4.1-8B on CUDA/ZeroGPU.`, produced a study receipt, and confirmed no `<think>` tags in the returned packet.
- Recent Codex-attributed commits published the UI and hardware-honesty passes to GitHub and the Hugging Face Space.
- Latest local visual QA covered desktop `1280px` and mobile `390px` layouts.
- Local browser QA on 2026-06-06 confirmed the no-auto-generation flow: opening the app shows a ready state, loading the physics sample only fills fields, and the build button produces the packet.
- Local HyperFrames demo draft rendered at `/private/tmp/exam-panic-rescue-hyperframes-demo.mp4`; MP4 metadata is `68.0s`, `1920x1080`, H.264, `30fps`, about `18.2MB`. The public demo link is still not final submission evidence until uploaded and approved.

## Open Work Before Final Submission

- MiniCPM generation on the live Space is verified on ZeroGPU; preserve quota and re-test only before recording or submission.
- llama.cpp path is implemented and documented; TinyLlama GGUF and official OpenBMB MiniCPM4 0.5B GGUF local smokes passed. Final Llama Champion claim still needs the demo/materials to explicitly show that route.
- Cohere review hook is implemented but intentionally not targeted unless official Cohere-specific criteria appear.

## Public Trace Rule

Keep this trace public-safe and add final public links when they exist:

- Public GitHub repo: https://github.com/himanshu748/exam-panic-rescue
- Hugging Face Space: https://huggingface.co/spaces/build-small-hackathon/exam-panic-rescue
- Demo video.
- Final field notes.
