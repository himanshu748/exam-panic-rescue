import json
import os
import unittest
from pathlib import Path

os.environ["USE_LOCAL_MODEL"] = "0"

ROOT = Path(__file__).resolve().parents[1]

from study_engine import (
    DEMO_CASES,
    LLAMA_CPP_FILENAME,
    LLAMA_CPP_HF_SELECTOR,
    LLAMA_CPP_REPO_ID,
    build_rescue_plan,
    cohere_quality_review,
    cohere_review_text_from_response,
    detect_panic,
    extract_study_topics,
    extract_topics,
    generated_text_from_llama_cli_output,
    generated_text_from_llama_cpp_result,
    llama_cli_command,
    panic_pattern,
    proof_checklist,
    StudyInput,
    time_blocks,
)


class StudyEngineTest(unittest.TestCase):
    def test_extract_topics_from_panic_dump(self):
        topics = extract_topics("work energy theorem, kinetic energy and power")

        self.assertIn("work energy theorem", topics)
        self.assertIn("kinetic energy", topics)
        self.assertIn("power", topics)

    def test_detects_panic_language(self):
        panic = detect_panic("I am panicking and scared I will go blank.")

        self.assertIn("scared", panic)
        self.assertIn("blank", panic)

    def test_panic_sentence_does_not_become_topic_when_syllabus_exists(self):
        topics = extract_study_topics(
            "work energy theorem, kinetic energy, power",
            "I am panicking and go blank in numericals tomorrow.",
        )

        joined = " ".join(topics).lower()
        self.assertIn("work energy theorem", topics)
        self.assertNotIn("panicking", joined)
        self.assertNotIn("tomorrow", joined)

    def test_time_blocks_fit_available_window(self):
        blocks = time_blocks(45)

        self.assertEqual(sum(minutes for _, minutes in blocks), 45)

    def test_build_rescue_plan_has_three_outputs(self):
        plan = build_rescue_plan(
            student_name="Aarav",
            subject="Physics",
            time_left_minutes=120,
            exam_format="Mixed",
            panic_note="I am panicking and go blank in numericals.",
            known_material="work energy theorem, kinetic energy, power",
            confidence=2,
        )

        self.assertIn("Rescue plan", plan.rescue_plan_markdown)
        self.assertIn("Drill deck", plan.drill_markdown)
        self.assertIn("Triage clock", plan.triage_markdown)
        self.assertIn("Final Sheet", plan.final_sheet_html)
        self.assertIn("work energy theorem", plan.final_sheet_html)
        self.assertIn("worked problems", plan.triage_markdown)
        self.assertIn("Panic pattern: blank-out spiral", plan.triage_markdown)
        self.assertIn("Proof target:", plan.triage_markdown)
        self.assertIn("Proof before stopping:", plan.final_sheet_html)
        self.assertIn("Study receipt", plan.demo_receipt_markdown)
        self.assertIn("Practical fit", plan.demo_receipt_markdown)
        self.assertIn("Field note prompt", plan.field_note_markdown)
        self.assertIn("confidence changed from ___/5 to ___/5", plan.field_note_markdown)
        self.assertIn("Copyable field note", plan.field_note_markdown)
        self.assertIn("Would use again? yes / no / maybe", plan.field_note_markdown)
        self.assertIn("Do not do:", plan.final_sheet_html)
        self.assertIn("fallback", plan.model_note.lower())

    def test_panic_pattern_prioritizes_specific_failure_mode(self):
        data = StudyInput(
            student_name="Aarav",
            subject="Physics",
            time_left_minutes=120,
            exam_format="Mixed",
            panic_note="I go blank in numericals.",
            known_material="work-energy theorem",
            confidence=2,
        )

        self.assertEqual(panic_pattern(data, ["memory blank-out", "worked problems"], ["blank"]), "blank-out spiral")

    def test_proof_checklist_matches_exam_format(self):
        proof = proof_checklist("Multiple choice", ["quadratic formula"])

        self.assertIn("Reject two traps", proof)
        self.assertIn("quadratic formula", proof)

    def test_field_note_prompt_uses_panic_pattern_and_topic(self):
        plan = build_rescue_plan(
            student_name="Mira",
            subject="Biology",
            time_left_minutes=45,
            exam_format="Short answer",
            panic_note="I am scared and keep forgetting definitions.",
            known_material="mitosis, meiosis",
            confidence=1,
        )

        self.assertIn("emergency recall loop", plan.field_note_markdown)
        self.assertIn("mitosis", plan.field_note_markdown)

    def test_demo_receipt_summarizes_before_after_path(self):
        plan = build_rescue_plan(
            student_name="Kabir",
            subject="Math",
            time_left_minutes=360,
            exam_format="Multiple choice",
            panic_note="MCQ options trick me and I rush the formula.",
            known_material="quadratic formula, discriminant",
            confidence=2,
        )

        self.assertIn("2/5", plan.demo_receipt_markdown)
        self.assertIn("quadratic formula", plan.demo_receipt_markdown)
        self.assertIn("Reject two traps", plan.demo_receipt_markdown)

    def test_demo_cases_cover_primary_judge_scenarios(self):
        names = {case["name"] for case in DEMO_CASES}

        self.assertEqual(len(DEMO_CASES), 4)
        self.assertIn("physics numericals", names)
        self.assertIn("history long answers", names)
        self.assertIn("math traps", names)

    def test_public_readiness_cases_match_app_demo_cases(self):
        exported = [
            json.loads(line)
            for line in (ROOT / "data" / "readiness_cases.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        self.assertEqual(exported, DEMO_CASES)

    def test_cohere_review_is_disabled_by_default(self):
        review = cohere_quality_review("plan", "drills", "triage")

        self.assertIsNone(review)

    def test_extracts_cohere_v2_review_text(self):
        text = cohere_review_text_from_response(
            {"message": {"content": [{"type": "text", "text": "Cohere quality check: specific and calm."}]}}
        )

        self.assertEqual(text, "Cohere quality check: specific and calm.")

    def test_extracts_multiple_cohere_text_parts(self):
        text = cohere_review_text_from_response(
            {
                "message": {
                    "content": [
                        {"type": "text", "text": "Cohere quality check:"},
                        {"type": "text", "text": "actionable."},
                        {"type": "tool-call", "text": "ignore me"},
                    ]
                }
            }
        )

        self.assertEqual(text, "Cohere quality check: actionable.")

    def test_llama_cpp_defaults_target_openbmb_gguf(self):
        self.assertEqual(LLAMA_CPP_REPO_ID, "openbmb/MiniCPM4.1-8B-GGUF")
        self.assertEqual(LLAMA_CPP_FILENAME, "MiniCPM4.1-8B-Q4_K_M.gguf")
        self.assertEqual(LLAMA_CPP_HF_SELECTOR, "Q4_K_M")

    def test_llama_cli_command_targets_openbmb_hf_selector(self):
        command = llama_cli_command("student panic", max_tokens=32)

        self.assertEqual(command[:3], ["llama-cli", "-hf", "openbmb/MiniCPM4.1-8B-GGUF:Q4_K_M"])
        self.assertIn("-p", command)
        self.assertIn("student panic", command)
        self.assertIn("-n", command)
        self.assertIn("32", command)
        self.assertIn("--single-turn", command)
        self.assertIn("--simple-io", command)
        self.assertIn("--no-display-prompt", command)

    def test_extracts_llama_cpp_chat_completion_text(self):
        text = generated_text_from_llama_cpp_result(
            {"choices": [{"message": {"content": "Cohesive rescue plan."}}]}
        )

        self.assertEqual(text, "Cohesive rescue plan.")

    def test_strips_prompt_echo_from_llama_cli_output(self):
        text = generated_text_from_llama_cli_output(
            "Loading model...\nmodel : tiny\n> student panic\n\n1. Reset.\n2. Drill.\n\n[ Prompt: 10 t/s | Generation: 20 t/s ]\nExiting...",
            prompt="student panic",
        )

        self.assertEqual(text, "1. Reset. 2. Drill.")


if __name__ == "__main__":
    unittest.main()
