from __future__ import annotations

import os
import re
import tempfile
import time

import gradio as gr

try:
    import spaces
except ImportError:  # Local tests should not require the HF Spaces runtime package.
    class _SpacesFallback:
        @staticmethod
        def GPU(*args, **kwargs):
            def decorator(fn):
                return fn

            return decorator

    spaces = _SpacesFallback()

from study_engine import (
    DEMO_CASES,
    EXAMPLE_INPUT,
    VISION_MODEL_ID,
    VOICE_MODEL_ID,
    answer_drills,
    build_rescue_plan,
    coach_state,
    ensure_weights,
    extract_topics_from_image,
    packet_to_markdown,
    synthesize_speech,
    time_blocks,
)


CSS = """
:root {
  --ink: #071613;
  --muted: #1c342f;
  --muted-soft: #27423c;
  --paper: #f4e2c5;
  --card: #fffaf0;
  --card-solid: #fff8ea;
  --field: #fffef9;
  --line: #5e5545;
  --green: #005844;
  --green-dark: #032f28;
  --coral: #84231b;
  --gold: #755004;
  --blue: #073e58;
  --graph: rgba(7, 62, 88, 0.11);
  --shadow: rgba(37, 29, 16, 0.20);
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
  font-family: "Trebuchet MS", "Segoe UI", ui-sans-serif, system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
  min-height: 100vh;
}

.gradio-container,
.gradio-container * {
  text-shadow: none !important;
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
  border: 1px solid rgba(7, 22, 19, 0.34);
  border-radius: 24px;
  background:
    linear-gradient(135deg, #fffaf0, #f4d9aa);
  box-shadow: 0 18px 48px rgba(37, 29, 16, 0.18);
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
  background: rgba(0, 88, 68, 0.16);
  color: var(--green-dark);
  font-size: 14px;
  font-weight: 900;
  letter-spacing: 0.10em;
  padding: 8px 12px;
  text-transform: uppercase;
}

.hero h1 {
  position: relative;
  margin: 14px 0 8px;
  font-family: Georgia, "Times New Roman", ui-serif, serif;
  color: var(--ink);
  font-size: clamp(34px, 5vw, 58px);
  line-height: 0.98;
  letter-spacing: -0.045em;
  max-width: 860px;
}

.hero p {
  margin: 0;
  max-width: 720px;
  color: var(--muted);
  font-size: clamp(17px, 2vw, 20px);
  font-weight: 750;
  line-height: 1.55;
}

.hero-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.hero-steps span {
  border: 1px solid rgba(7, 22, 19, 0.32);
  border-radius: 999px;
  background: #fffdf7;
  color: var(--ink);
  font-size: 15px;
  font-weight: 900;
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
  border: 1px solid rgba(7, 22, 19, 0.30);
  border-radius: 18px;
  background: #fffdf7;
  padding: 12px;
}

.hero-proof b {
  display: block;
  color: var(--coral);
  font-family: Georgia, "Times New Roman", ui-serif, serif;
  font-size: clamp(22px, 3vw, 30px);
  letter-spacing: -0.04em;
  line-height: 0.95;
}

.hero-proof span {
  display: block;
  margin-top: 5px;
  color: var(--ink);
  font-size: 15px;
  font-weight: 850;
  line-height: 1.42;
}

.demo-status {
  display: grid;
  grid-template-columns: 1.25fr 1fr 1fr;
  gap: 10px;
  margin-top: 16px;
}

.status-card {
  border: 1px solid rgba(7, 22, 19, 0.32);
  border-radius: 20px;
  background: #fff8ea;
  box-shadow: 0 16px 40px rgba(37, 29, 16, 0.13);
  padding: 13px 14px;
}

.status-card b {
  display: block;
  color: var(--green-dark);
  font-size: 14px;
  letter-spacing: 0.10em;
  text-transform: uppercase;
}

.status-card span {
  display: block;
  margin-top: 5px;
  color: var(--muted);
  font-size: 15px;
  font-weight: 750;
  line-height: 1.45;
}

.model-budget {
  display: grid;
  grid-template-columns: 1.2fr repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.budget-card {
  border: 1px solid rgba(7, 22, 19, 0.34);
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
  font-size: 14px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.budget-card span {
  display: block;
  margin-top: 6px;
  color: var(--muted);
  font-size: 15px;
  font-weight: 750;
  line-height: 1.45;
}

#main-workspace {
  gap: 18px;
  margin-top: 20px;
  align-items: flex-start;
}

.input-card,
.output-stack {
  border: 1px solid rgba(7, 22, 19, 0.34);
  border-radius: 26px;
  background: var(--card);
  box-shadow: 0 18px 52px rgba(37, 29, 16, 0.16);
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
  font-family: Georgia, "Times New Roman", ui-serif, serif;
  color: var(--ink);
  font-size: 26px;
  letter-spacing: -0.02em;
}

.section-title p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 16px;
  font-weight: 750;
  line-height: 1.5;
}

.panel {
  border: 1px solid rgba(7, 22, 19, 0.30);
  border-radius: 20px;
  background: #fffef9;
  box-shadow: none;
  margin-bottom: 10px;
  padding: 13px 15px;
}

.panel h3 {
  color: var(--green-dark);
  font-family: Georgia, "Times New Roman", ui-serif, serif;
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
  border-color: rgba(7, 22, 19, 0.48) !important;
  background: var(--field) !important;
  color: var(--ink) !important;
  font-size: 16px !important;
  font-weight: 750 !important;
  line-height: 1.45 !important;
}

.input-card label,
.input-card .wrap label {
  color: var(--ink) !important;
  font-size: 15px !important;
  font-weight: 900 !important;
}

.gradio-container input::placeholder,
.gradio-container textarea::placeholder {
  color: #4f625d !important;
  opacity: 1 !important;
}

.gradio-container .prose,
.gradio-container .markdown,
.gradio-container .prose p,
.gradio-container .prose li,
.gradio-container .prose span,
.gradio-container .markdown p,
.gradio-container .markdown li,
.gradio-container .markdown span {
  color: var(--ink) !important;
  font-size: 16px !important;
  font-weight: 700;
  line-height: 1.55;
}

.gradio-container .prose h1,
.gradio-container .prose h2,
.gradio-container .prose h3,
.gradio-container .markdown h1,
.gradio-container .markdown h2,
.gradio-container .markdown h3 {
  color: var(--ink) !important;
  font-weight: 900 !important;
}

.gradio-container .block-info,
.gradio-container .form .secondary-wrap,
.gradio-container label span,
.gradio-container .wrap span {
  color: var(--muted) !important;
  font-size: 14px !important;
  font-weight: 700 !important;
  opacity: 1 !important;
}

.primary-action button, button.primary-action {
  background: var(--green) !important;
  border-color: var(--green) !important;
  border-radius: 16px !important;
  color: white !important;
  font-weight: 850 !important;
  min-height: 46px;
  box-shadow: 0 12px 28px rgba(0, 108, 91, 0.24);
}

.primary-action button:hover, button.primary-action:hover {
  background: var(--green-dark) !important;
}

.secondary-action button, button.secondary-action {
  border-color: var(--coral) !important;
  color: var(--coral) !important;
  background: #fff7ed !important;
  border-radius: 16px !important;
  font-weight: 800 !important;
  min-height: 46px;
}

/* Force the cream/light design even when the visitor's device is in dark mode. */
.gradio-container, .gradio-container.dark, .dark {
  color-scheme: light;
  --body-background-fill: var(--paper);
  --background-fill-primary: var(--field);
  --background-fill-secondary: var(--card-solid);
  --block-background-fill: var(--card);
  --block-label-background-fill: var(--card);
  --block-title-background-fill: var(--card);
  --input-background-fill: var(--field);
  --body-text-color: var(--ink);
  --body-text-color-subdued: var(--muted);
  --block-label-text-color: var(--ink);
  --block-title-text-color: var(--ink);
  --block-info-text-color: var(--muted);
  --border-color-primary: rgba(7, 22, 19, 0.34);
  --border-color-accent: rgba(0, 88, 68, 0.34);
}
.gradio-container.dark .input-card,
.gradio-container.dark .output-stack,
.dark .input-card,
.dark .output-stack {
  background: var(--card) !important;
}

#model-note {
  margin-top: 10px;
  border-left: 4px solid var(--gold);
  border-radius: 12px;
  background: rgba(189, 143, 34, 0.10);
  padding: 10px 12px;
  font-size: 15px;
  font-weight: 800;
  color: #241800;
}

.runtime-label {
  margin: 4px 0 -4px;
  color: var(--green-dark);
  font-size: 14px;
  font-weight: 850;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.final-sheet {
  border: 1px solid rgba(7, 22, 19, 0.42);
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(189, 143, 34, 0.25), transparent 34%),
    linear-gradient(135deg, rgba(0, 98, 79, 0.13), #fffef9);
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
  font-family: Georgia, "Times New Roman", ui-serif, serif;
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
  font-weight: 900;
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
  font-size: 15px;
  font-weight: 750;
}

.demo-cases {
  margin-top: 14px;
  border: 1px dashed rgba(7, 22, 19, 0.36);
  border-radius: 18px;
  background: #fffaf0;
  box-shadow: none;
  padding: 12px;
}

.demo-cases h2 {
  margin: 0 0 6px;
  font-family: Georgia, "Times New Roman", ui-serif, serif;
  color: var(--ink);
  font-size: 25px;
  letter-spacing: -0.02em;
}

.demo-cases p {
  margin: 0 0 12px;
  color: var(--muted);
  font-size: 15px;
  font-weight: 750;
}

.case-list {
  gap: 8px;
}

.case-button button {
  justify-content: flex-start !important;
  width: 100%;
  min-height: 44px;
  border: 1px solid rgba(0, 88, 68, 0.36) !important;
  border-radius: 15px !important;
  background: #fffef9 !important;
  color: var(--ink) !important;
  font-size: 15px !important;
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
  border: 1px solid rgba(7, 22, 19, 0.30);
  border-radius: 16px;
  background: #fffef9;
  padding: 12px;
  box-shadow: none;
}

.claim-card b {
  display: block;
  color: var(--green-dark);
  font-size: 14px;
  letter-spacing: 0.10em;
  text-transform: uppercase;
}

.claim-card span {
  display: block;
  margin-top: 6px;
  color: var(--muted);
  font-size: 15px;
  font-weight: 750;
  line-height: 1.42;
}

.proof-details {
  margin-top: 18px;
  border: 1px solid rgba(7, 22, 19, 0.30);
  border-radius: 20px;
  background: #fffaf0;
  padding: 12px 14px;
}

.proof-details summary {
  cursor: pointer;
  color: var(--green-dark);
  font-size: 15px;
  font-weight: 900;
}

.proof-details p {
  color: var(--muted);
  font-size: 15px;
  font-weight: 750;
  line-height: 1.5;
}

.hackathon-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: center;
  margin-top: 20px;
  padding: 14px;
  border: 1px solid rgba(7, 22, 19, 0.22);
  border-radius: 18px;
  background: #fffaf0;
}

.hackathon-footer span {
  border: 1px solid rgba(0, 88, 68, 0.30);
  border-radius: 999px;
  background: #fffef9;
  color: var(--green-dark);
  font-size: 13px;
  font-weight: 850;
  letter-spacing: 0.04em;
  padding: 6px 12px;
}

.runtime-note-tag {
  display: inline-block;
  margin: 0 0 6px;
  color: var(--green-dark);
  font-size: 13px;
  font-weight: 850;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.coach-card {
  border: 1px solid rgba(7, 22, 19, 0.30);
  border-radius: 18px;
  background: #fffef9;
  padding: 14px 16px;
  margin-bottom: 10px;
}

.coach-idle {
  color: var(--muted);
  font-size: 15px;
  font-weight: 750;
  line-height: 1.45;
}

.coach-live {
  background: radial-gradient(circle at top right, rgba(0, 108, 91, 0.16), transparent 50%), #fffef9;
  border-color: rgba(0, 88, 68, 0.42);
}

.coach-now {
  color: var(--green-dark);
  font-size: 18px;
  font-weight: 900;
  letter-spacing: 0.02em;
}

.coach-time {
  font-family: Georgia, "Times New Roman", ui-serif, serif;
  color: var(--coral);
  font-size: clamp(34px, 6vw, 46px);
  line-height: 1.05;
  letter-spacing: -0.03em;
  margin: 2px 0;
}

.coach-next {
  color: var(--muted);
  font-size: 14px;
  font-weight: 800;
}

.coach-done {
  background: rgba(0, 108, 91, 0.12);
  border-color: rgba(0, 88, 68, 0.42);
  color: var(--green-dark);
  font-size: 16px;
  font-weight: 850;
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
    <h1>When time is low, stop rereading everything.</h1>
    <p>A practical study rescue for students in the final crunch: paste what you know, what scares you, and how much time is left. Get one ranked path, five drills, a triage clock, and the last sheet to read before the exam.</p>
    <div class="hero-steps" aria-label="Rescue flow">
      <span>1. Dump the panic</span>
      <span>2. Rank the leaks</span>
      <span>3. Drill only what matters</span>
      <span>4. Walk in with a final sheet</span>
    </div>
    <div class="hero-proof" aria-label="Rescue packet contents">
      <div><b>5</b><span>practice drills generated from the student's own topics</span></div>
      <div><b>1</b><span>proof target before the student stops studying</span></div>
      <div><b>0</b><span>new chapters in the last block; protect marks from what is already possible</span></div>
    </div>
  </div>
</section>
"""


CLAIM_STATUS_HTML = """
<details class="proof-details">
  <summary>Hackathon build proof and claim status</summary>
  <p><strong>How to review fast:</strong> load a sample scenario only to understand the flow, replace it with real exam details when using the product, build the rescue packet, then check the proof target/final sheet and runtime note.</p>
  <section class="claim-strip" aria-label="Public claim status">
    <div class="claim-card">
      <b>Claim now</b>
      <span>Backyard AI main track, OpenBMB MiniCPM on ZeroGPU, OpenAI Codex evidence, and Off-Brand custom UI.</span>
    </div>
    <div class="claim-card">
      <b>Claim after links</b>
      <span>Best Demo, Community Choice, Field Notes, and Sharing-style build trace once the public video/social/report links exist.</span>
    </div>
    <div class="claim-card">
      <b>Do not claim yet</b>
      <span>Modal, Nemotron, Tiny Titan, fine-tuning, or Best Agent unless matching evidence exists.</span>
    </div>
  </section>
  <section class="model-budget" aria-label="Runtime claim status">
    <div class="budget-card"><b>Model budget</b><span>MiniCPM4.1-8B fits the <=32B rule; hardware is the real gate.</span></div>
    <div class="budget-card"><b>ZeroGPU verified</b><span>Live Space smoke generated with MiniCPM on CUDA/ZeroGPU; keep calls focused inside quota.</span></div>
    <div class="budget-card"><b>Default target</b><span>OpenBMB MiniCPM stays the submission-aligned model path when hardware can run it.</span></div>
  </section>
</details>
"""


FOOTER_HTML = """
<footer class="hackathon-footer">
  <span>Built for the Build Small Hackathon</span>
  <span>Backyard AI track</span>
  <span>OpenBMB MiniCPM · ≤32B</span>
  <span>Runs as a Gradio Space on Hugging Face</span>
  <a href="https://huggingface.co/spaces/build-small-hackathon/exam-panic-rescue-field-notes" target="_blank" rel="noopener noreferrer" style="text-decoration:none"><span style="background:#005844;color:#fff;border-color:#005844">📓 Read the build report →</span></a>
</footer>
"""


@spaces.GPU(duration=120)
def _gpu_build_plan(
    student_name: str,
    subject: str,
    time_left_minutes: int,
    exam_format: str,
    panic_note: str,
    known_material: str,
    confidence: int,
    model_choice: str = "openbmb/MiniCPM4.1-8B",
):
    return build_rescue_plan(
        student_name,
        subject,
        time_left_minutes,
        exam_format,
        panic_note,
        known_material,
        confidence,
        model_id=model_choice,
    )


def generate(
    student_name: str,
    subject: str,
    time_left_minutes: int,
    exam_format: str,
    panic_note: str,
    known_material: str,
    confidence: int,
    model_choice: str = "openbmb/MiniCPM4.1-8B",
):
    # Download weights on CPU first so a cold model never eats the GPU duration budget.
    ensure_weights(model_choice)
    try:
        plan = _gpu_build_plan(
            student_name,
            subject,
            time_left_minutes,
            exam_format,
            panic_note,
            known_material,
            confidence,
            model_choice,
        )
    except Exception:
        # A ZeroGPU worker timeout/abort is raised here in the main process and is not
        # catchable inside the GPU call, so fall back to the deterministic packet rather
        # than surfacing an error to the student.
        plan = build_rescue_plan(
            student_name,
            subject,
            time_left_minutes,
            exam_format,
            panic_note,
            known_material,
            confidence,
            force_fallback=True,
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


@spaces.GPU(duration=120)
def _gpu_extract_from_photo(image_path):
    return extract_topics_from_image(image_path)


def extract_from_photo(image_path):
    if not image_path:
        return gr.update(), "Upload a photo first, or just type your topics."
    ensure_weights(VISION_MODEL_ID)
    try:
        topics, note = _gpu_extract_from_photo(image_path)
    except Exception:
        return gr.update(), "Photo reading is busy right now (GPU hiccup). Try again, or just type your topics in."
    if topics:
        return topics, note
    return gr.update(), note


def download_packet(rescue, drill, triage, final_sheet_html, receipt):
    md = packet_to_markdown(rescue, drill, triage, final_sheet_html, receipt)
    path = os.path.join(tempfile.gettempdir(), "exam-panic-rescue-packet.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(md)
    return path


@spaces.GPU(duration=120)
def _gpu_read_aloud(text, out_path):
    return synthesize_speech(text, out_path)


def read_aloud(final_sheet_html):
    raw = final_sheet_html or ""
    # Voice only works once a real packet has been generated. The generated final sheet always
    # contains this kicker; the idle placeholder does not — so this gates out the placeholder
    # (no model load, no audio) until the student has actually built a packet.
    if "Last page before the exam" not in raw:
        return gr.update(value=None, visible=False), "Build your rescue packet first — then tap Read aloud to hear your final sheet."
    text = re.sub(r"<[^>]+>", " ", raw)
    out = os.path.join(tempfile.gettempdir(), "exam-panic-rescue-final-sheet.wav")
    ensure_weights(VOICE_MODEL_ID)
    try:
        path, note = _gpu_read_aloud(text, out)
    except Exception:
        return gr.update(visible=False), "Read-aloud is busy right now (GPU hiccup). Try again in a moment."
    if path:
        return gr.update(value=path, visible=True), note
    return gr.update(visible=False), note


@spaces.GPU(duration=120)
def _gpu_show_answers(drill_markdown, subject, model_choice):
    answers, _note = answer_drills(drill_markdown, subject, model_choice)
    return answers


def show_answers(drill_markdown, subject, model_choice="openbmb/MiniCPM4.1-8B"):
    ensure_weights(model_choice)
    try:
        return _gpu_show_answers(drill_markdown, subject, model_choice)
    except Exception:
        return "### Worked answers\n\nThe model is busy right now (GPU hiccup). Try again in a moment — or self-check each drill against your notes and mark it right or wrong."


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


def load_biology_case():
    return load_case(0)


def load_physics_case():
    return load_case(1)


def load_history_case():
    return load_case(2)


def load_math_case():
    return load_case(3)


CASE_LOADERS = [load_biology_case, load_physics_case, load_history_case, load_math_case]


# The whole design is built for a light/cream surface, so force light mode even when the
# visitor's device is in dark mode (otherwise dark Gradio surfaces hide the dark label text).
FORCE_LIGHT_JS = """
() => {
  try {
    const url = new URL(window.location.href);
    if (url.searchParams.get('__theme') !== 'light') {
      url.searchParams.set('__theme', 'light');
      window.location.replace(url.toString());
    }
  } catch (e) {}
}
"""


# Build Small Hackathon submission Space (resume).
with gr.Blocks(title="Exam Panic Rescue") as demo:
    gr.HTML(f"<style>{CSS}</style>", container=False)
    with gr.Column(elem_classes=["app-shell"]):
        gr.HTML(HERO_HTML, container=False)
        gr.HTML(
            """
<section class="demo-status" aria-label="Study status">
  <div class="status-card"><b>Start here</b><span>Paste your real exam details first. Samples are only there to show the flow.</span></div>
  <div class="status-card"><b>ZeroGPU live</b><span>MiniCPM runs only when you build a packet; CPU fallback remains if hardware is switched back.</span></div>
  <div class="status-card"><b>Low-time rule</b><span>Do not learn everything. Choose marks to protect, drill one leak, then make the final sheet.</span></div>
</section>
""",
            container=False,
        )
        gr.HTML(
            """
<section class="model-budget" aria-label="Low-time study method">
  <div class="budget-card"><b>First 2 minutes</b><span>Write what you remember, circle one leak, and stop opening new chapters.</span></div>
  <div class="budget-card"><b>Main block</b><span>Drill the highest-value topic with one format-specific proof target.</span></div>
  <div class="budget-card"><b>Final block</b><span>Read only the final sheet: first action, protected marks, and the do-not-do guardrail.</span></div>
</section>
""",
            container=False,
        )

        with gr.Row(equal_height=False, elem_id="main-workspace"):
            with gr.Column(scale=5, min_width=320, elem_classes=["input-card"]):
                gr.HTML(
                    """
<div class="section-title">
  <h2>Build your rescue packet</h2>
  <p>Paste a real panic dump, actual topics, and time left. If you load a sample, treat it as a template and replace it before studying.</p>
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
                with gr.Accordion("📷 Or snap your syllabus / notes", open=False):
                    syllabus_image = gr.Image(
                        label="Photo of a syllabus, timetable, textbook page, or notes",
                        type="filepath",
                        height=180,
                    )
                    extract_btn = gr.Button("Extract topics from photo", elem_classes=["secondary-action"])
                    vision_note = gr.Markdown(
                        "Upload a photo, then click Extract — OpenBMB MiniCPM-V reads it and fills the topics box above. Always check what it found."
                    )
                with gr.Accordion("⚙️ Advanced: choose the small model", open=False):
                    model_choice = gr.Dropdown(
                        label="Generation model (all ≤32B)",
                        choices=[
                            ("OpenBMB MiniCPM4.1-8B — default", "openbmb/MiniCPM4.1-8B"),
                            ("NVIDIA Nemotron-Mini-4B", "nvidia/Nemotron-Mini-4B-Instruct"),
                            ("OpenBMB MiniCPM5-1B — tiny (≤4B)", "openbmb/MiniCPM5-1B"),
                        ],
                        value="openbmb/MiniCPM4.1-8B",
                        info="Pick which small model writes your plan. The runtime note shows exactly what ran.",
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
                    maximum=1440,
                    value=EXAMPLE_INPUT["time_left_minutes"],
                    step=15,
                    info="From 15 minutes up to a full day (1440 min). The plan changes with the time you have.",
                )
                with gr.Row():
                    run = gr.Button("Build my rescue packet", variant="primary", elem_classes=["primary-action"])
                    example = gr.Button("Load example", elem_classes=["secondary-action"])
                inputs = [student_name, subject, time_left_minutes, exam_format, panic_note, known_material, confidence]
                with gr.Column(elem_classes=["demo-cases"]):
                    gr.HTML(
                        """
<h2>Try a sample scenario</h2>
<p>Samples do not claim real-user data. They only show how the rescue changes for short answers, numericals, long answers, and MCQ traps.</p>
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
  <h2>Your low-time learning packet</h2>
  <p>Follow this top to bottom: reset, drill, protect marks, stop the spiral, and keep one receipt of what changed.</p>
</div>
""",
                    container=False,
                )
                gr.HTML('<div class="runtime-label">Live coach</div>', container=False)
                coach_start = gr.State(None)
                coach_display = gr.HTML(
                    value='<div class="coach-card coach-idle">Build a packet, then press <b>Start coaching</b> to run your triage clock in real time — it tells you what to do now and pings when to switch.</div>',
                    container=False,
                )
                with gr.Row():
                    coach_start_btn = gr.Button("Start coaching", elem_classes=["primary-action"])
                    coach_reset_btn = gr.Button("Reset", elem_classes=["secondary-action"])
                coach_timer = gr.Timer(1.0, active=False)
                rescue_output = gr.Markdown(
                    value="### Ready when you are\n\nPaste the real exam details, then click **Build my rescue packet**. Nothing is generated until you ask for it.",
                    elem_classes=["panel"],
                )
                drill_output = gr.Markdown(
                    value="### Drill deck\n\nFive drills appear here after generation — written by MiniCPM when the model runs, with built-in templates as a reliable fallback.",
                    elem_classes=["panel"],
                )
                answers_btn = gr.Button("Show worked answers", elem_classes=["secondary-action"])
                answers_output = gr.Markdown(
                    value="### Worked answers\n\nBuild a packet, then reveal model-written answers to self-check your drills.",
                    elem_classes=["panel"],
                )
                triage_output = gr.Markdown(
                    value="### Triage clock\n\nThe time blocks will appear here after generation.",
                    elem_classes=["panel"],
                )
                final_sheet_output = gr.HTML(
                    value='<div class="final-sheet"><h3>Final sheet</h3><p>Build a packet to create the one-page sheet to read before the exam.</p></div>',
                    elem_classes=["panel"],
                )
                with gr.Row():
                    download_btn = gr.DownloadButton("⬇ Download / print", elem_classes=["secondary-action"])
                    read_btn = gr.Button("🔊 Read aloud", elem_classes=["secondary-action"])
                read_audio = gr.Audio(label="Final sheet, read aloud", type="filepath", interactive=False, visible=False)
                read_note = gr.Markdown(
                    "Tip: build a packet, then tap Read aloud to hear your final sheet (OpenBMB VoxCPM2)."
                )
                with gr.Accordion("More — study receipt · field note · runtime", open=False):
                    demo_receipt_output = gr.Markdown(
                        value="### Study receipt\n\nA short before/after receipt will appear here after generation.",
                        elem_classes=["panel"],
                    )
                    field_note_output = gr.Markdown(
                        value="### Field note prompt\n\nAfter a real study block, use this section to capture honest feedback. Do not invent results.",
                        elem_classes=["panel"],
                    )
                    gr.HTML('<div class="runtime-label">Runtime note</div>', container=False)
                    model_note = gr.Markdown(
                        value="No generation yet. When you build a packet, this Space runs a small model (default OpenBMB MiniCPM4.1-8B, ≤32B) on ZeroGPU, or a deterministic fallback on CPU. This note always reports exactly what ran.",
                        elem_id="model-note",
                    )

        outputs = [
            rescue_output,
            drill_output,
            triage_output,
            final_sheet_output,
            demo_receipt_output,
            field_note_output,
            model_note,
        ]
        gr.HTML(FOOTER_HTML, container=False)
    demo.load(js=FORCE_LIGHT_JS)
    run.click(generate, inputs=inputs + [model_choice], outputs=outputs, scroll_to_output=True, api_name="generate")

    def _start_coach(minutes):
        return time.time(), gr.Timer(active=True)

    def _reset_coach():
        return (
            None,
            gr.Timer(active=False),
            '<div class="coach-card coach-idle">Coach reset. Press <b>Start coaching</b> to run your triage clock.</div>',
        )

    def _tick_coach(start_ts, minutes):
        if not start_ts:
            return gr.update()
        state = coach_state(time_blocks(int(minutes or 60)), time.time() - start_ts)
        if state["done"]:
            return '<div class="coach-card coach-done">Time is up. Read only your final sheet, then walk in.</div>'
        rs = state["remaining_s"]
        nxt = f'Next: {state["next"]}' if state["next"] else "Last block — finish strong"
        return (
            '<div class="coach-card coach-live">'
            f'<div class="coach-now">Now: {state["current"]}</div>'
            f'<div class="coach-time">{rs // 60:02d}:{rs % 60:02d} left</div>'
            f'<div class="coach-next">{nxt} · block {state["index"] + 1}/{state["count"]}</div>'
            "</div>"
        )

    coach_start_btn.click(_start_coach, inputs=[time_left_minutes], outputs=[coach_start, coach_timer])
    coach_reset_btn.click(_reset_coach, outputs=[coach_start, coach_timer, coach_display])
    coach_timer.tick(_tick_coach, inputs=[coach_start, time_left_minutes], outputs=[coach_display])
    extract_btn.click(extract_from_photo, inputs=[syllabus_image], outputs=[known_material, vision_note], api_name="extract_topics")
    download_btn.click(
        download_packet,
        inputs=[rescue_output, drill_output, triage_output, final_sheet_output, demo_receipt_output],
        outputs=download_btn,
    )
    read_btn.click(read_aloud, inputs=[final_sheet_output], outputs=[read_audio, read_note], api_name="read_aloud")
    answers_btn.click(show_answers, inputs=[drill_output, subject, model_choice], outputs=[answers_output], api_name="show_answers")
    example.click(load_example, outputs=inputs, queue=False)
    for case_button, case_index in case_buttons:
        case_button.click(CASE_LOADERS[case_index], outputs=inputs, queue=False)


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
        show_error=True,
    )
