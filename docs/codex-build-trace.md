# Codex Build Trace

Updated: 2026-06-05

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
- Demo receipt.
- Field note prompt.
- Model/runtime note.

The app stays intentionally narrow: one stressed student, one exam, one time box.

## Sponsor Strategy

- Hugging Face: Gradio Space under `build-small-hackathon`.
- OpenAI Codex: Codex-assisted app, tests, docs, and iteration trace; final submission needs public GitHub evidence.
- OpenBMB: default model target is `openbmb/MiniCPM4.1-8B`.
- NVIDIA: local-first/no-cloud default with small-model/GPU-friendly framing.
- Cohere: optional quality-review hook only; disabled by default.
- JetBrains: reproducible PyCharm/JetBrains workflow docs.
- Black Forest Labs: visual/delight support through the final-sheet artifact.
- Modal: intentionally excluded by user preference.

## Codex Iterations

1. Selected Exam Panic Rescue over less relatable ideas.
2. Built a Gradio Blocks app with custom UI rather than default Gradio styling.
3. Added deterministic fallback planning so the demo works without a cloud API or model download.
4. Added tests for topic extraction, panic detection, weakness detection, final sheet generation, demo receipt generation, Cohere default-off behavior, and llama.cpp result parsing.
5. Switched the default model strategy back to OpenBMB/MiniCPM after the user correctly noted OpenBMB should be default for that prize angle.
6. Added optional sponsor hooks without making them default dependencies.
7. Added private readiness gates so staging, final submission, and sponsor claims are not mixed up.
8. Added a panic-pattern/proof-target layer so outputs feel less generic and more like a real student rescue.
9. Tightened the public sponsor matrix into claim levels so final materials can distinguish "ready now" from "needs live smoke."
10. Added a public claim-status panel in the Gradio UI so judges can see claim discipline without reading private docs.
11. Added a 90-second demo path rail and per-run demo receipt so the before/after is visible without narration.

## Current Evidence

- Local compile passes.
- Unit tests pass across `18` cases.
- Readiness smoke scores `28/28`.
- Local Gradio smoke returned HTTP `200` after the latest UI/output pass.
- Space package audit includes `15` public-safe files and now requires the public build trace, demo script, field notes, development workflow, llama.cpp plan, and sponsor matrix.
- Space smoke checker verifies the public claim-status and 90-second demo path markers in the served app.
- Hugging Face CLI auth verified `HIMANSHUKUMARJHA` and `build-small-hackathon`.
- Public GitHub repo exists with Codex-attributed commits: https://github.com/himanshu748/exam-panic-rescue
- Public Hugging Face Space is published and live-smoke-tested: https://huggingface.co/spaces/build-small-hackathon/exam-panic-rescue
- Live Space runtime smoke passed root HTTP `200`, Gradio `/config` HTTP `200`, required public markers, and no obvious private/internal markers.

## Open Work Before Final Submission

- MiniCPM generation on the live Space still needs a manual demo run; the Space smoke currently verifies runtime/config/UI markers.
- llama.cpp path is documented but not live-tested.
- Cohere review hook is implemented but not live-tested with a key.

## Public Trace Rule

Keep this trace public-safe and add final public links when they exist:

- Public GitHub repo: https://github.com/himanshu748/exam-panic-rescue
- Hugging Face Space: https://huggingface.co/spaces/build-small-hackathon/exam-panic-rescue
- Demo video.
- Final field notes.
