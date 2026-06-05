from __future__ import annotations

import os

import gradio as gr

from study_engine import DEMO_CASES, EXAMPLE_INPUT, build_rescue_plan


CSS = """
:root {
  --ink: #132022;
  --muted: #536463;
  --paper: #f4f1e8;
  --card: rgba(255, 252, 242, 0.92);
  --line: #c9c2af;
  --green: #006c5b;
  --green-dark: #06483f;
  --coral: #b74336;
  --gold: #b98717;
  --blue: #1f5574;
  --graph: rgba(31, 85, 116, 0.10);
  --shadow: rgba(37, 29, 16, 0.12);
}

.gradio-container {
  background:
    radial-gradient(circle at 8% 8%, rgba(183, 67, 54, 0.18), transparent 26%),
    radial-gradient(circle at 92% 4%, rgba(0, 108, 91, 0.18), transparent 24%),
    linear-gradient(var(--graph) 1px, transparent 1px),
    linear-gradient(90deg, var(--graph) 1px, transparent 1px),
    var(--paper);
  background-size: auto, 24px 24px, 24px 24px, auto;
  color: var(--ink);
  font-family: "Avenir Next", "Segoe UI", ui-sans-serif, system-ui, sans-serif;
  min-height: 100vh;
}

.app-shell {
  max-width: 1240px;
  margin: 0 auto;
  padding: 24px clamp(14px, 3vw, 34px) 38px;
}

.hero {
  position: relative;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(260px, 0.65fr);
  gap: 22px;
  border: 1px solid rgba(19, 32, 34, 0.18);
  border-radius: 30px;
  background:
    linear-gradient(135deg, rgba(255, 252, 242, 0.96), rgba(246, 230, 199, 0.78)),
    repeating-linear-gradient(135deg, transparent 0 18px, rgba(31, 85, 116, 0.05) 18px 20px);
  box-shadow: 0 24px 70px var(--shadow);
  padding: clamp(20px, 4vw, 38px);
}

.hero:after {
  content: "";
  position: absolute;
  right: -92px;
  top: -102px;
  width: 260px;
  height: 260px;
  border-radius: 999px;
  border: 38px solid rgba(183, 67, 54, 0.12);
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  border: 1px solid rgba(0, 108, 91, 0.28);
  border-radius: 999px;
  background: rgba(0, 108, 91, 0.08);
  color: var(--green-dark);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.10em;
  padding: 8px 12px;
  text-transform: uppercase;
}

.hero h1 {
  position: relative;
  margin: 16px 0 10px;
  font-family: ui-serif, Georgia, "Times New Roman", serif;
  font-size: clamp(38px, 7vw, 76px);
  line-height: 0.92;
  letter-spacing: -0.055em;
  max-width: 780px;
}

.hero p {
  margin: 0;
  max-width: 720px;
  color: #405150;
  font-size: clamp(15px, 2vw, 18px);
  line-height: 1.58;
}

.hero-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}

.hero-steps span {
  border: 1px solid rgba(19, 32, 34, 0.14);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.62);
  color: #2e4242;
  font-size: 13px;
  font-weight: 700;
  padding: 8px 11px;
}

.hero-proof {
  position: relative;
  z-index: 1;
  align-self: stretch;
  display: grid;
  gap: 12px;
}

.proof-card {
  border: 1px solid rgba(19, 32, 34, 0.15);
  border-radius: 22px;
  background: rgba(19, 32, 34, 0.92);
  color: #fffaf0;
  padding: 18px;
}

.proof-card strong {
  display: block;
  font-family: ui-serif, Georgia, "Times New Roman", serif;
  font-size: 30px;
  line-height: 1;
}

.proof-card span {
  display: block;
  margin-top: 7px;
  color: rgba(255, 250, 240, 0.76);
  font-size: 13px;
  line-height: 1.4;
}

#main-workspace {
  gap: 18px;
  margin-top: 20px;
  align-items: flex-start;
}

.input-card,
.output-stack {
  border: 1px solid rgba(19, 32, 34, 0.16);
  border-radius: 26px;
  background: var(--card);
  box-shadow: 0 18px 52px rgba(37, 29, 16, 0.08);
  padding: clamp(14px, 2vw, 20px);
}

.section-title {
  margin-bottom: 14px;
}

.section-title h2 {
  margin: 0;
  font-family: ui-serif, Georgia, "Times New Roman", serif;
  font-size: 24px;
  letter-spacing: -0.02em;
}

.section-title p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.45;
}

.panel {
  border: 1px solid rgba(19, 32, 34, 0.13);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: none;
  padding: 8px;
}

.panel h3 {
  color: var(--green-dark);
  font-family: ui-serif, Georgia, "Times New Roman", serif;
  letter-spacing: -0.01em;
}

.input-card textarea,
.input-card input,
.input-card select {
  border-radius: 14px !important;
}

.input-card label,
.input-card .wrap label {
  color: #243636 !important;
  font-weight: 750 !important;
}

.primary-action button {
  background: var(--green) !important;
  border-color: var(--green) !important;
  border-radius: 16px !important;
  min-height: 46px;
  box-shadow: 0 12px 28px rgba(0, 108, 91, 0.24);
}

.primary-action button:hover {
  background: var(--green-dark) !important;
}

.secondary-action button {
  border-color: var(--coral) !important;
  color: var(--coral) !important;
  border-radius: 16px !important;
  min-height: 46px;
}

#model-note {
  margin-top: 10px;
  border-left: 4px solid var(--gold);
  border-radius: 12px;
  background: rgba(189, 143, 34, 0.10);
  padding: 10px 12px;
  font-size: 13px;
  color: #443715;
}

.final-sheet {
  border: 1px solid rgba(19, 32, 34, 0.30);
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(189, 143, 34, 0.25), transparent 34%),
    linear-gradient(135deg, rgba(0, 108, 91, 0.10), rgba(255, 255, 255, 0.94));
  padding: clamp(16px, 3vw, 24px);
  color: var(--ink);
}

.sheet-kicker {
  color: var(--coral);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.final-sheet h2 {
  margin: 4px 0 14px;
  font-family: ui-serif, Georgia, "Times New Roman", serif;
  font-size: clamp(27px, 4vw, 42px);
  line-height: 0.98;
  letter-spacing: -0.045em;
}

.sheet-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.sheet-grid h3 {
  margin: 0 0 8px;
  color: var(--blue);
}

.sheet-rule {
  border-left: 4px solid var(--green);
  margin: 12px 0 0;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(0, 108, 91, 0.09);
  font-weight: 700;
}

.sheet-action,
.sheet-proof,
.sheet-warning {
  margin: 12px 0 0;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(31, 85, 116, 0.10);
}

.sheet-proof {
  border: 1px solid rgba(31, 85, 116, 0.20);
}

.sheet-warning {
  border: 1px solid rgba(183, 67, 54, 0.24);
  background: rgba(183, 67, 54, 0.10);
}

.sheet-footer {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.demo-cases {
  margin-top: 18px;
  border: 1px solid rgba(19, 32, 34, 0.16);
  border-radius: 24px;
  background: rgba(255, 252, 242, 0.80);
  box-shadow: 0 14px 40px rgba(37, 29, 16, 0.08);
  padding: clamp(14px, 2vw, 20px);
}

.demo-cases h2 {
  margin: 0 0 6px;
  font-family: ui-serif, Georgia, "Times New Roman", serif;
  font-size: 24px;
  letter-spacing: -0.02em;
}

.demo-cases p {
  margin: 0 0 12px;
  color: var(--muted);
  font-size: 13px;
}

.claim-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.claim-card {
  border: 1px solid rgba(19, 32, 34, 0.16);
  border-radius: 20px;
  background: rgba(255, 252, 242, 0.82);
  padding: 14px 16px;
  box-shadow: 0 14px 38px rgba(37, 29, 16, 0.07);
}

.claim-card b {
  display: block;
  color: var(--green-dark);
  font-size: 12px;
  letter-spacing: 0.10em;
  text-transform: uppercase;
}

.claim-card span {
  display: block;
  margin-top: 6px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.45;
}

.demo-rail {
  display: grid;
  grid-template-columns: minmax(220px, 0.8fr) minmax(0, 1.2fr);
  gap: 14px;
  margin-top: 18px;
  border: 1px solid rgba(19, 32, 34, 0.16);
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(19, 32, 34, 0.92), rgba(6, 72, 63, 0.88)),
    radial-gradient(circle at 88% 14%, rgba(189, 143, 34, 0.18), transparent 30%);
  color: #fffaf0;
  box-shadow: 0 18px 52px rgba(37, 29, 16, 0.14);
  padding: clamp(15px, 2vw, 20px);
}

.demo-rail b {
  display: block;
  color: #f4d283;
  font-size: 12px;
  letter-spacing: 0.11em;
  text-transform: uppercase;
}

.demo-rail strong {
  display: block;
  margin-top: 8px;
  font-family: ui-serif, Georgia, "Times New Roman", serif;
  font-size: clamp(24px, 3vw, 34px);
  line-height: 1.04;
  letter-spacing: -0.035em;
}

.demo-rail p,
.demo-rail li {
  color: rgba(255, 250, 240, 0.82);
  font-size: 13px;
  line-height: 1.45;
}

.demo-rail p {
  margin: 10px 0 0;
}

.demo-rail ol {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  list-style: none;
  margin: 0;
  padding: 0;
  counter-reset: demo-step;
}

.demo-rail li {
  counter-increment: demo-step;
  border: 1px solid rgba(255, 250, 240, 0.16);
  border-radius: 18px;
  background: rgba(255, 250, 240, 0.08);
  padding: 12px;
}

.demo-rail li:before {
  content: counter(demo-step);
  display: inline-grid;
  place-items: center;
  width: 24px;
  height: 24px;
  margin-bottom: 9px;
  border-radius: 999px;
  background: #f4d283;
  color: var(--green-dark);
  font-weight: 900;
}

@media (prefers-reduced-motion: no-preference) {
  .primary-action button,
  .secondary-action button {
    transition: transform 150ms ease-out, background-color 150ms ease-out, box-shadow 150ms ease-out;
  }

  .primary-action button:hover,
  .secondary-action button:hover {
    transform: translateY(-1px);
  }
}

@media (max-width: 940px) {
  .hero {
    grid-template-columns: 1fr;
  }

  #main-workspace {
    flex-direction: column !important;
  }

  #main-workspace > .column,
  #main-workspace > div {
    width: 100% !important;
    min-width: 100% !important;
  }
}

@media (max-width: 640px) {
  .app-shell {
    padding: 12px 10px 24px;
  }

  .hero {
    border-radius: 22px;
    padding: 18px;
  }

  .hero-steps span {
    width: 100%;
  }

  .input-card,
  .output-stack {
    border-radius: 20px;
    padding: 12px;
  }

  .sheet-grid {
    grid-template-columns: 1fr;
  }

  .claim-strip {
    grid-template-columns: 1fr;
  }

  .demo-rail {
    grid-template-columns: 1fr;
  }

  .demo-rail ol {
    grid-template-columns: 1fr;
  }

  .primary-action,
  .secondary-action {
    flex: 1 1 100%;
  }
}
"""


HERO_HTML = """
<section class="hero">
  <div>
    <div class="eyebrow">Backyard AI · OpenBMB MiniCPM · local-first rescue</div>
    <h1>Stop the spiral. Build the next 90 minutes.</h1>
    <p>Exam Panic Rescue turns a messy panic dump into one calm plan, five drills, a triage clock, a final sheet, a demo receipt, and a copyable field note a student can use before and after the exam crunch.</p>
    <div class="hero-steps" aria-label="Demo flow">
      <span>1. Dump the panic</span>
      <span>2. Rank the leaks</span>
      <span>3. Drill only what matters</span>
      <span>4. Walk in with a final sheet</span>
    </div>
  </div>
  <div class="hero-proof" aria-label="Hackathon proof points">
    <div class="proof-card"><strong>8B</strong><span>Default target: OpenBMB MiniCPM4.1, under the 32B rule and aligned with the special prize.</span></div>
    <div class="proof-card"><strong>28/28</strong><span>Local readiness smoke across biology, physics, history, and math panic cases.</span></div>
  </div>
</section>
"""


CLAIM_STATUS_HTML = """
<section class="claim-strip" aria-label="Public claim status">
  <div class="claim-card">
    <b>Claim now</b>
    <span>Backyard AI workflow, OpenBMB MiniCPM default target, Off-Brand Gradio UI, and local-first fallback.</span>
  </div>
  <div class="claim-card">
    <b>Claim after smoke</b>
    <span>Hugging Face Space runtime, Codex public repo evidence, and any MiniCPM-on-Space runtime claim.</span>
  </div>
  <div class="claim-card">
    <b>Do not claim yet</b>
    <span>Llama Champion, Cohere live review, Well-Tuned, or final submission until those checks are proven.</span>
  </div>
</section>
"""


DEMO_RAIL_HTML = """
<section class="demo-rail" aria-label="90-second demo path">
  <div>
    <b>90-second demo path</b>
    <strong>Make the judge see the before/after immediately.</strong>
    <p>Use the built-in physics case first, then show the proof target, final sheet, and copyable field note.</p>
  </div>
  <ol>
    <li>Load a panic case.</li>
    <li>Click Build rescue plan.</li>
    <li>Point to the proof target and final sheet.</li>
    <li>Copy the field note for follow-up evidence.</li>
  </ol>
</section>
"""


DEMO_EXAMPLES = [
    [
        case["student_name"],
        case["subject"],
        case["time_left_minutes"],
        case["exam_format"],
        case["panic_note"],
        case["known_material"],
        case["confidence"],
    ]
    for case in DEMO_CASES
]


def generate(
    student_name: str,
    subject: str,
    time_left_minutes: int,
    exam_format: str,
    panic_note: str,
    known_material: str,
    confidence: int,
):
    plan = build_rescue_plan(
        student_name,
        subject,
        time_left_minutes,
        exam_format,
        panic_note,
        known_material,
        confidence,
    )
    return (
        plan.rescue_plan_markdown,
        plan.drill_markdown,
        plan.triage_markdown,
        plan.final_sheet_html,
        plan.demo_receipt_markdown,
        plan.field_note_markdown,
        plan.model_note,
    )


def load_example():
    return (
        EXAMPLE_INPUT["student_name"],
        EXAMPLE_INPUT["subject"],
        EXAMPLE_INPUT["time_left_minutes"],
        EXAMPLE_INPUT["exam_format"],
        EXAMPLE_INPUT["panic_note"],
        EXAMPLE_INPUT["known_material"],
        EXAMPLE_INPUT["confidence"],
    )


with gr.Blocks(title="Exam Panic Rescue") as demo:
    gr.HTML(f"<style>{CSS}</style>", container=False)
    with gr.Column(elem_classes=["app-shell"]):
        gr.HTML(HERO_HTML, container=False)
        gr.HTML(CLAIM_STATUS_HTML, container=False)
        gr.HTML(DEMO_RAIL_HTML, container=False)

        with gr.Row(equal_height=False, elem_id="main-workspace"):
            with gr.Column(scale=5, min_width=320, elem_classes=["input-card"]):
                gr.HTML(
                    """
<div class="section-title">
  <h2>What is happening?</h2>
  <p>Use rough student language. The app is better when the panic is specific.</p>
</div>
""",
                    container=False,
                )
                student_name = gr.Textbox(
                    label="Student",
                    value=EXAMPLE_INPUT["student_name"],
                    lines=1,
                    info="First name is enough.",
                )
                subject = gr.Textbox(
                    label="Exam subject",
                    value=EXAMPLE_INPUT["subject"],
                    lines=2,
                    info="Include class/chapter if useful.",
                )
                panic_note = gr.Textbox(
                    label="Panic dump",
                    value=EXAMPLE_INPUT["panic_note"],
                    lines=5,
                    info="What feels scary, blank, messy, or urgent?",
                )
                known_material = gr.Textbox(
                    label="Syllabus, notes, or weak topics",
                    value=EXAMPLE_INPUT["known_material"],
                    lines=5,
                    info="Paste chapter headings, topics, mistakes, or rough notes.",
                )
                with gr.Row():
                    exam_format = gr.Dropdown(
                        label="Exam format",
                        choices=["Mixed", "Multiple choice", "Short answer", "Long answer"],
                        value=EXAMPLE_INPUT["exam_format"],
                        info="This changes the drill style.",
                    )
                    confidence = gr.Slider(
                        label="Confidence",
                        minimum=1,
                        maximum=5,
                        value=EXAMPLE_INPUT["confidence"],
                        step=1,
                        info="1 = frozen, 5 = steady.",
                    )
                time_left_minutes = gr.Slider(
                    label="Minutes left",
                    minimum=15,
                    maximum=720,
                    value=EXAMPLE_INPUT["time_left_minutes"],
                    step=15,
                    info="The plan changes if there are 45 minutes vs. a full day.",
                )
                with gr.Row():
                    run = gr.Button("Build rescue plan", variant="primary", elem_classes=["primary-action"])
                    example = gr.Button("Load example", elem_classes=["secondary-action"])

            with gr.Column(scale=7, min_width=340, elem_classes=["output-stack"]):
                gr.HTML(
                    """
<div class="section-title">
  <h2>The rescue packet</h2>
  <p>Designed for a demo under 90 seconds: plan, drills, clock, final sheet, demo receipt, and field note.</p>
</div>
""",
                    container=False,
                )
                rescue_output = gr.Markdown(elem_classes=["panel"])
                drill_output = gr.Markdown(elem_classes=["panel"])
                triage_output = gr.Markdown(elem_classes=["panel"])
                final_sheet_output = gr.HTML(elem_classes=["panel"])
                demo_receipt_output = gr.Markdown(elem_classes=["panel"])
                field_note_output = gr.Markdown(elem_classes=["panel"])
                model_note = gr.Markdown(elem_id="model-note")

        inputs = [student_name, subject, time_left_minutes, exam_format, panic_note, known_material, confidence]
        outputs = [
            rescue_output,
            drill_output,
            triage_output,
            final_sheet_output,
            demo_receipt_output,
            field_note_output,
            model_note,
        ]
        with gr.Column(elem_classes=["demo-cases"]):
            gr.HTML(
                """
<h2>Judge-ready panic cases</h2>
<p>Use these to show that the workflow handles different subjects, clocks, and exam formats without prompt gymnastics.</p>
""",
                container=False,
            )
            gr.Examples(
                examples=DEMO_EXAMPLES,
                inputs=inputs,
                label="Load a panic case",
            )
    run.click(generate, inputs=inputs, outputs=outputs)
    panic_note.submit(generate, inputs=inputs, outputs=outputs)
    example.click(load_example, outputs=inputs).then(generate, inputs=inputs, outputs=outputs)
    demo.load(generate, inputs=inputs, outputs=outputs)


if __name__ == "__main__":
    demo.queue().launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
    )
