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
  --card-solid: #fffaf0;
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

.gradio-container button:focus-visible,
.gradio-container textarea:focus-visible,
.gradio-container input:focus-visible,
.gradio-container select:focus-visible {
  outline: 3px solid rgba(0, 108, 91, 0.34) !important;
  outline-offset: 2px !important;
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
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
  border: 1px solid rgba(19, 32, 34, 0.18);
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(255, 252, 242, 0.98), rgba(246, 230, 199, 0.74));
  box-shadow: 0 18px 48px rgba(37, 29, 16, 0.10);
  padding: clamp(18px, 3vw, 30px);
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
  margin: 14px 0 8px;
  font-family: ui-serif, Georgia, "Times New Roman", serif;
  font-size: clamp(34px, 5vw, 58px);
  line-height: 0.98;
  letter-spacing: -0.045em;
  max-width: 860px;
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
  margin-top: 14px;
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
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 18px;
  max-width: 880px;
}

.hero-proof div {
  border: 1px solid rgba(19, 32, 34, 0.13);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.58);
  padding: 12px;
}

.hero-proof b {
  display: block;
  color: var(--coral);
  font-family: ui-serif, Georgia, "Times New Roman", serif;
  font-size: clamp(22px, 3vw, 30px);
  letter-spacing: -0.04em;
  line-height: 0.95;
}

.hero-proof span {
  display: block;
  margin-top: 5px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 750;
  line-height: 1.35;
}

.demo-status {
  display: grid;
  grid-template-columns: 1.25fr 1fr 1fr;
  gap: 10px;
  margin-top: 16px;
}

.status-card {
  border: 1px solid rgba(19, 32, 34, 0.14);
  border-radius: 20px;
  background: rgba(255, 250, 240, 0.78);
  box-shadow: 0 16px 40px rgba(37, 29, 16, 0.08);
  padding: 13px 14px;
}

.status-card b {
  display: block;
  color: var(--green-dark);
  font-size: 12px;
  letter-spacing: 0.10em;
  text-transform: uppercase;
}

.status-card span {
  display: block;
  margin-top: 5px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.4;
}

.model-budget {
  display: grid;
  grid-template-columns: 1.2fr repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.budget-card {
  border: 1px solid rgba(19, 32, 34, 0.15);
  border-radius: 20px;
  background: var(--card-solid);
  padding: 13px 14px;
}

.budget-card:first-child {
  background:
    radial-gradient(circle at top right, rgba(0, 108, 91, 0.16), transparent 46%),
    var(--card-solid);
}

.budget-card b {
  display: block;
  color: var(--ink);
  font-size: 13px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.budget-card span {
  display: block;
  margin-top: 6px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.42;
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

@media (min-width: 941px) {
  .input-card {
    position: sticky;
    top: 16px;
  }
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
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(255, 250, 240, 0.74));
  box-shadow: none;
  margin-bottom: 10px;
  padding: 10px 12px;
}

.panel h3 {
  color: var(--green-dark);
  font-family: ui-serif, Georgia, "Times New Roman", serif;
  letter-spacing: -0.01em;
}

.panel h3:first-child {
  margin-top: 0;
}

.panel ul,
.final-sheet ul {
  padding-left: 1.15rem;
}

.panel li,
.final-sheet li {
  margin-bottom: 5px;
}

.output-stack pre,
.output-stack code {
  max-width: 100% !important;
  white-space: pre-wrap !important;
  word-break: break-word !important;
}

.output-stack pre {
  overflow-x: auto !important;
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
  color: white !important;
  font-weight: 850 !important;
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
  font-weight: 800 !important;
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

.runtime-label {
  margin: 4px 0 -4px;
  color: var(--green-dark);
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0.12em;
  text-transform: uppercase;
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
  margin-top: 14px;
  border: 1px dashed rgba(19, 32, 34, 0.20);
  border-radius: 18px;
  background: rgba(255, 252, 242, 0.64);
  box-shadow: none;
  padding: 12px;
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

.case-list {
  gap: 8px;
}

.case-button button {
  justify-content: flex-start !important;
  width: 100%;
  min-height: 44px;
  border: 1px solid rgba(0, 108, 91, 0.18) !important;
  border-radius: 15px !important;
  background: rgba(255, 250, 240, 0.72) !important;
  color: #243636 !important;
  font-size: 13px !important;
  font-weight: 800 !important;
  text-align: left !important;
}

.case-button button:hover {
  border-color: rgba(0, 108, 91, 0.36) !important;
  background: rgba(0, 108, 91, 0.08) !important;
}

.claim-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.claim-card {
  border: 1px solid rgba(19, 32, 34, 0.16);
  border-radius: 16px;
  background: rgba(255, 252, 242, 0.70);
  padding: 12px;
  box-shadow: none;
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

.proof-details {
  margin-top: 18px;
  border: 1px solid rgba(19, 32, 34, 0.14);
  border-radius: 20px;
  background: rgba(255, 252, 242, 0.68);
  padding: 12px 14px;
}

.proof-details summary {
  cursor: pointer;
  color: var(--green-dark);
  font-weight: 800;
}

.proof-details p {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.45;
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

  .demo-status,
  .model-budget {
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

  .hero-proof {
    grid-template-columns: 1fr;
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

  .primary-action,
  .secondary-action {
    flex: 1 1 100%;
  }
}
"""


HERO_HTML = """
<section class="hero">
  <div>
    <div class="eyebrow">Exam Panic Rescue</div>
    <h1>Paste the panic. Get the rescue packet.</h1>
    <p>A tiny study coach for the final crunch: it turns one messy panic dump into a calm plan, five drills, a triage clock, and the last sheet to read before walking into the exam.</p>
    <div class="hero-steps" aria-label="Demo flow">
      <span>1. Dump the panic</span>
      <span>2. Rank the leaks</span>
      <span>3. Drill only what matters</span>
      <span>4. Walk in with a final sheet</span>
    </div>
    <div class="hero-proof" aria-label="Rescue packet contents">
      <div><b>5</b><span>practice drills generated from the student's own topics</span></div>
      <div><b>1</b><span>proof target before the student stops studying</span></div>
      <div><b>90s</b><span>judge demo path: panic to final sheet</span></div>
    </div>
  </div>
</section>
"""


CLAIM_STATUS_HTML = """
<details class="proof-details">
  <summary>Build proof and claim status</summary>
  <p><strong>90-second demo path:</strong> load a panic case, build the rescue plan, show the proof target/final sheet, then copy the field note.</p>
  <section class="claim-strip" aria-label="Public claim status">
    <div class="claim-card">
      <b>Claim now</b>
      <span>Backyard AI workflow, OpenBMB MiniCPM default target, Off-Brand Gradio UI, and local-first fallback.</span>
    </div>
    <div class="claim-card">
      <b>Claim after smoke</b>
      <span>MiniCPM generation on Space, Llama Champion, and final submission.</span>
    </div>
    <div class="claim-card">
      <b>Do not claim yet</b>
      <span>Well-Tuned or any untested runtime prize until real evidence exists.</span>
    </div>
  </section>
</details>
"""


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


def load_case(index: int):
    case = DEMO_CASES[index]
    return (
        case["student_name"],
        case["subject"],
        case["time_left_minutes"],
        case["exam_format"],
        case["panic_note"],
        case["known_material"],
        case["confidence"],
    )


with gr.Blocks(title="Exam Panic Rescue") as demo:
    gr.HTML(f"<style>{CSS}</style>", container=False)
    with gr.Column(elem_classes=["app-shell"]):
        gr.HTML(HERO_HTML, container=False)
        gr.HTML(
            """
<section class="demo-status" aria-label="Demo status">
  <div class="status-card"><b>Loaded case</b><span>Physics numericals: formula panic, 120 minutes left, confidence 2/5.</span></div>
  <div class="status-card"><b>Space-safe</b><span>CPU-only Spaces use the deterministic fallback; upgraded hardware can test MiniCPM or Gemma.</span></div>
  <div class="status-card"><b>Best judge path</b><span>Click once, then show triage clock, proof target, final sheet, and field note.</span></div>
</section>
""",
            container=False,
        )
        gr.HTML(
            """
<section class="model-budget" aria-label="Model budget">
  <div class="budget-card"><b>Model budget</b><span>The hackathon ceiling is <=32B parameters, but hardware is the real gate.</span></div>
  <div class="budget-card"><b>HF CPU basic</b><span>2 vCPU, 16GB RAM, 50GB disk: great for the product demo, not for a 27B live model.</span></div>
  <div class="budget-card"><b>Default target</b><span>OpenBMB MiniCPM stays the submission-aligned model path when hardware can run it.</span></div>
  <div class="budget-card"><b>Gemma 27B</b><span>Comparison only: needs accepted license access plus upgraded GPU-class hardware.</span></div>
</section>
""",
            container=False,
        )

        with gr.Row(equal_height=False, elem_id="main-workspace"):
            with gr.Column(scale=5, min_width=320, elem_classes=["input-card"]):
                gr.HTML(
                    """
<div class="section-title">
  <h2>Run the demo</h2>
  <p>The physics case is loaded. Change it or pick another panic case below, then build the rescue packet.</p>
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
                inputs = [student_name, subject, time_left_minutes, exam_format, panic_note, known_material, confidence]
                with gr.Column(elem_classes=["demo-cases"]):
                    gr.HTML(
                        """
<h2>Try another panic case</h2>
<p>One click loads a different subject, time window, and exam format. No spreadsheet table, just demo paths.</p>
""",
                        container=False,
                    )
                    case_buttons = []
                    with gr.Column(elem_classes=["case-list"]):
                        for index, case in enumerate(DEMO_CASES):
                            label = f"{case['name'].title()} · {case['time_left_minutes']} min · {case['exam_format']}"
                            case_buttons.append(
                                (
                                    gr.Button(
                                        label,
                                        size="lg",
                                        elem_classes=["case-button"],
                                    ),
                                    index,
                                )
                            )

            with gr.Column(scale=7, min_width=340, elem_classes=["output-stack"]):
                gr.HTML(
                    """
<div class="section-title">
  <h2>The rescue packet</h2>
  <p>This is the product: the plan, drills, clock, final sheet, receipt, and field note in one screen.</p>
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
                gr.HTML('<div class="runtime-label">Runtime note</div>', container=False)
                model_note = gr.Markdown(elem_id="model-note")

        outputs = [
            rescue_output,
            drill_output,
            triage_output,
            final_sheet_output,
            demo_receipt_output,
            field_note_output,
            model_note,
        ]
        gr.HTML(CLAIM_STATUS_HTML, container=False)
    run.click(generate, inputs=inputs, outputs=outputs, scroll_to_output=True)
    panic_note.submit(generate, inputs=inputs, outputs=outputs, scroll_to_output=True)
    example.click(load_example, outputs=inputs).then(generate, inputs=inputs, outputs=outputs, scroll_to_output=True)
    for case_button, case_index in case_buttons:
        case_button.click(lambda index=case_index: load_case(index), outputs=inputs).then(
            generate,
            inputs=inputs,
            outputs=outputs,
            scroll_to_output=True,
        )
    demo.load(generate, inputs=inputs, outputs=outputs)


if __name__ == "__main__":
    demo.queue().launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
    )
