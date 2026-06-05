# Demo Script

Updated: 2026-06-05

Goal: one clean demo under 90 seconds.

## Primary Demo Case

Student: `Aarav`

Subject: `Class 11 Physics: work, energy, and power`

Panic dump:

```text
I am panicking. I know formulas but go blank in numericals. The test is tomorrow morning.
```

Syllabus/weak topics:

```text
Work-energy theorem, kinetic energy, potential energy, power, conservation of energy
```

Settings:

- Exam format: `Mixed`
- Confidence: `2`
- Minutes left: `120`

Fast path in the UI: click the built-in `physics numericals` panic case under "Judge-ready panic cases", then run the rescue.

## Talk Track

0-10 seconds:

This is Exam Panic Rescue. It is for one specific Backyard AI user: a student who has stopped studying clearly because the exam panic took over.

10-25 seconds:

Paste the panic dump and the actual topics. The app does not pretend to know the whole syllabus; it uses the student's own notes and time box.
If using the fast path, point out that the built-in case is the same one covered by the readiness smoke test.
Briefly point to the claim-status cards: claim now, claim after smoke, and do not claim yet.

25-50 seconds:

Run the rescue. Show that it extracts real topics, identifies blank-out/numerical/formula weakness, and converts the panic into a short rescue plan.

50-70 seconds:

Show the drill deck and triage clock. These are deliberately practical: what to drill, how long to spend, which panic pattern is showing up, and what proof target the student needs before stopping.

70-90 seconds:

Show the final sheet. This is the student-facing artifact: the last page before the exam. Mention OpenBMB MiniCPM as the default model path and local-first fallback.
Call out the first-action line, proof-before-stopping line, and the "Do not do" guardrail; those are what keep a panicking student from restarting the spiral.
Show the demo receipt as the judge-readable before/after: confidence, panic pattern, first move, leak to patch, and proof of work.
End on the copyable field-note prompt: it is how we capture whether a real student actually used the rescue and what changed.

## What To Avoid Saying

- Do not guarantee marks.
- Do not claim final hackathon submission before Space/Git/demo are ready.
- Do not claim Llama Champion until llama.cpp is live-tested.
- Do not mention Modal in the product story.
- Do not expose account dashboards, redemption links, or credential screens in the recording.

## Strong Closing Line

This is small on purpose: one student, one panic dump, one rescue packet, and one receipt that proves what changed.
