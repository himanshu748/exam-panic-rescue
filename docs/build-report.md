# Exam Panic Rescue — Build Report / Field Notes

*A short report for the Build Small Hackathon (Backyard AI track): what I built, why it runs
on small models, and what I learned shipping it on Hugging Face ZeroGPU.*

- Live app: https://huggingface.co/spaces/build-small-hackathon/exam-panic-rescue
- Code: https://github.com/himanshu748/exam-panic-rescue
- Open build traces: https://huggingface.co/datasets/build-small-hackathon/exam-panic-rescue-build-trace

---

## The problem

Every exam season has the same bad hour. Two hours left, the syllabus is a wall, and you're
rereading the same page without retaining a word. You're not studying anymore — you're panicking
with a book open. I wanted a tool that does one thing for that exact moment: tell a stressed
student what to do **next**, and nothing more.

Exam Panic Rescue is deliberately narrow. A student pastes what they half-know, what's scaring
them, and how many minutes are left — or snaps a photo of their syllabus — and gets back one
ranked rescue plan, five practice drills written for their own topics, a triage clock that runs
in real time, and a one-page final sheet to read before they walk in. It can read that sheet
aloud. That's the whole product. The hard part was resisting everything else.

## Small models, on purpose

The hackathon rule is a ceiling: nothing over 32B. I treated it as a design value, not a
limitation. A panicking student doesn't need a frontier model to be told "stop opening new
chapters and protect these five marks." The intelligence that matters here is *judgment under
time pressure*, and small models are more than enough to write good drills and a tight plan — if
you give them a tight job.

| Model | Role |
|-------|------|
| OpenBMB MiniCPM4.1-8B | Writes the rescue plan and the five drills (default engine) |
| OpenBMB MiniCPM-V-4.5 | Reads a photo of a syllabus/notes and extracts the topics |
| OpenBMB VoxCPM2 | Reads the final sheet aloud |
| NVIDIA Nemotron-Mini-4B | Selectable alternate engine — verified live, real output |
| OpenBMB MiniCPM5-1B | A sub-4B option for the smallest footprint |

All five run on Hugging Face ZeroGPU. Every generation prints a runtime note saying exactly which
model ran and on what hardware, so the model behind any output is never ambiguous.

## The lesson that cost me the most: cold starts on a shared GPU

ZeroGPU is free and great, but it has a shape you have to design around: the GPU is only attached
*inside* a decorated function, and that function has a strict time budget. My first version loaded
each model inside that budget. The default model stayed warm and was instant. But the moment a
student picked the Nemotron engine, or uploaded the first photo, the app had to **download several
gigabytes of weights inside the GPU window** — and a cold download plus load plus generation blew
straight through the limit. ZeroGPU aborted the call, and the user got the deterministic fallback
instead of the real model.

The symptom was maddening: the same code that worked beautifully on the second call fell back
instantly on the first. The fix, once I understood it, was small and clean — **prefetch the
weights on the CPU, before ever touching the GPU.** Move the multi-gigabyte download out of the
timed window so the GPU call only pays the fast load-and-generate cost. After that, a cold first
call returns real model output instead of a template. I verified it live: the exact Nemotron call
that used to fall back now returns a real packet.

> The bug taught me the platform. The download wasn't slow — it was in the wrong place.

## Honesty as a feature: never crash, never lie

Because the model can be cold, the GPU can be busy, or a node can fault, I decided early that the
app must **always return a complete, useful packet** — and must always tell the truth about how it
made it. So there's a deterministic study engine underneath every model path. If a model is
unavailable, the student still gets a real plan, drills, and triage clock from templates, with a
runtime note that says plainly "fallback used." Nothing errors out in a student's face, and
nothing pretends a model ran when it didn't.

This turned out to matter for trust: a runtime note that says "Generated with MiniCPM4.1-8B on
ZeroGPU" or "fallback used" is worth more than a confident black box.

## Small things that were not small

- **The time math.** The triage clock splits remaining minutes into blocks. My first version's
  blocks didn't sum back to the total — a rounding leak. Rewriting it with largest-remainder
  apportionment fixed it so the clock is always exactly the time the student actually has, from 15
  minutes to a full day.
- **Designing for a panicking human.** An overflowing examples table became four large one-tap
  panic cases. A dark-mode bug hid dark text on dark surfaces, so I forced the cream light theme
  the design was built for. The copyable field-note block overflowed on a 390px phone until I
  wrapped it.
- **The operational reality of a free Space.** A live ZeroGPU Space is real infrastructure. I hit
  a transient ECC GPU fault (fixed by a restart) and a Space that paused itself after a burst of
  heavy testing. The lesson: treat the live demo like production — verify it end to end, and check
  it's actually *running* before you rely on it.

## What's still open (honest)

- **The real test is a real student.** The Backyard AI track is judged on whether the person you
  built it for actually used it. The app ships a field-note prompt to capture an honest
  before/after — that's the validation I care about most.
- **First-call latency on secondary models.** The prefetch fix trades a fast-but-fake fallback for
  real-but-slower output on a cold first call. For a panic tool, real wins — but warming the model
  before a live demo is still the move.

## Takeaway

A tight job for a small model, an honest fallback under it, and a runtime note that never lies will
get you a tool people can actually trust in their worst hour. You don't need a giant model to
rescue one stressed student.
