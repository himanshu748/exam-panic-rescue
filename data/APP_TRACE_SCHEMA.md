# Public App Trace Schema

This file documents `data/app_traces_public.jsonl`.

Each row is a public-safe trace of the Exam Panic Rescue app:

- `trace_id`: Stable public trace identifier.
- `trace_type`: Trace category. Current rows are `public_app_qa_sample`.
- `created_date`: Trace creation date.
- `source`: App/runtime that produced the trace.
- `space_url`: Public Hugging Face Space.
- `runtime_mode`: Runtime used for this trace.
- `runtime_note`: User-visible runtime note from the app.
- `input`: The exact public sample input loaded into the app.
- `output`: The generated rescue packet sections returned by the app.
- `validation`: Boolean checks for required sections and safety artifacts.
- `privacy`: Disclosure flags. Current traces are sample QA traces, not real-user outcomes.

The dataset intentionally avoids private notes, tokens, personal contact details, hidden reasoning, and fake real-user claims.
