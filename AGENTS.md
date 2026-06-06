# Repository Guidance

## Project Shape
- This workspace is only for the Build Small Hackathon.
- Do not add unrelated product prototypes or landing pages here.
- The final submission must be a Gradio app hosted as a Hugging Face Space under `build-small-hackathon`.
- Until the June 5, 2026 build window opens, focus on sponsor/bounty tracking, idea scoring, user-problem discovery, and submission readiness.

## Strategy
- Default track: Backyard AI, unless updated bounty details make Thousand Token Wood clearly stronger.
- Prefer ideas that can credibly use MiniCPM/OpenBMB and stay within the `<=32B` model rule.
- Keep the first build small: one clear workflow, one primary input path, one primary output, and a demo under 90 seconds.
- Do not post publicly in Discord or social channels without explicit user approval of the exact wording.

## Documentation
- Use `docs/current-snapshot.md` for the latest verified event status.
- Use `docs/project-plan.md` for the current execution strategy.
- Use `docs/idea-rubric.md` to score candidate ideas before selecting the final build.
- Keep docs current when sponsors, rules, or Discord announcements change.

## Verification
- Before final app work, verify `hf auth whoami` shows `HIMANSHUKUMARJHA` and `build-small-hackathon`.
- For any Gradio app, test locally before uploading to Hugging Face.
- For submission readiness, verify Space link, demo video, social post, and any bonus-quest artifacts.
