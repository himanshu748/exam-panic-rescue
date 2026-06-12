# Public App Trace Schema

This file documents `data/app_traces_public.jsonl`.

Each row is a public-safe trace of the Exam Panic Rescue app:

- `trace_id`: Stable public trace identifier.
- `trace_type`: Trace category. Current rows are `live_model_run` — captured by calling the live Space's `generate` endpoint.
- `created_date`: Trace creation date.
- `source`: App/runtime that produced the trace.
- `space_url`: Public Hugging Face Space.
- `runtime_mode`: Runtime used for this trace. `zerogpu_minicpm_live` means OpenBMB MiniCPM actually ran on Hugging Face ZeroGPU; `deterministic_fallback` means the no-GPU planner produced it.
- `runtime_note`: The app's own runtime note, naming the exact model and size (e.g. `Generated with openbmb/MiniCPM4.1-8B (8B) on CUDA/ZeroGPU`).
- `input`: The exact public sample input sent to the app.
- `output`: The generated student packet sections returned by the app: rescue plan, drills, triage clock, final sheet, study receipt, and runtime note. Plan and drills are written by the model when `model_was_called` is true.
- `validation`: Boolean checks, including `model_was_called`, required sections, topic coverage, and absence of hidden-reasoning tags.
- `privacy`: Disclosure flags. These are disclosed sample scenarios, not real-user outcomes.

The dataset intentionally avoids private notes, tokens, personal contact details, hidden reasoning, and fake real-user claims.
