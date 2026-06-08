import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["USE_LOCAL_MODEL"] = "0"

ROOT = Path(__file__).resolve().parents[1]

from study_engine import (
    answer_drills,
    DEMO_CASES,
    LLAMA_CPP_FILENAME,
    LLAMA_CPP_HF_SELECTOR,
    LLAMA_CPP_REPO_ID,
    NEMOTRON_FALLBACK_MODEL_ID,
    build_rescue_plan,
    clip_text,
    coach_state,
    cohere_quality_review,
    cohere_review_text_from_response,
    detect_panic,
    detect_weaknesses,
    extract_topics_from_image,
    extract_study_topics,
    extract_topics,
    generated_text_from_llama_cli_output,
    generated_text_from_llama_cpp_result,
    generated_text_from_pipeline_result,
    llama_cli_command,
    model_size_label,
    nemotron_fallback_enabled,
    packet_to_markdown,
    panic_pattern,
    proof_checklist,
    split_model_plan_and_drills,
    StudyInput,
    synthesize_speech,
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

    def test_time_blocks_fit_every_supported_window(self):
        sample_minutes = list(range(15, 721, 15)) + [16, 47, 89, 121, 359, 700]
        for minutes in sample_minutes:
            blocks = time_blocks(minutes)
            self.assertEqual(
                sum(block_minutes for _, block_minutes in blocks),
                minutes,
                f"blocks must sum to the available time at {minutes} min",
            )
            self.assertTrue(
                all(block_minutes > 0 for _, block_minutes in blocks),
                f"every block must be positive at {minutes} min",
            )

    def test_model_practice_questions_become_drills(self):
        generated = (
            "5 practice questions:\n"
            "- Define mitosis vs meiosis in one line.\n"
            "- List the cell cycle checkpoints.\n"
            "- Explain cytokinesis with one example.\n\n"
            "4-step survival plan:\n"
            "1. Make a hit list.\n"
            "2. Drill the weakest topic.\n"
        )
        plan_text, drills = split_model_plan_and_drills(generated)
        self.assertIn("survival plan", plan_text.lower())
        self.assertNotIn("practice questions", plan_text.lower())
        self.assertEqual(len(drills), 3)
        self.assertIn("Define mitosis vs meiosis in one line.", drills)

    def test_unstructured_model_output_keeps_template_drills(self):
        plan_text, drills = split_model_plan_and_drills("Just stay calm and revise your notes.")

        self.assertEqual(drills, [])
        self.assertIn("stay calm", plan_text.lower())

    def test_clip_text_bounds_long_input(self):
        self.assertEqual(len(clip_text("a" * 5000, 2000)), 2000)
        self.assertEqual(clip_text("short"), "short")

    def test_answer_drills_fallback_self_check(self):
        md, note = answer_drills("### Drill deck\n\n- Define mitosis\n- Explain meiosis", "Biology")
        self.assertIn("self-check", md.lower())
        self.assertIn("Define mitosis", md)

    def test_answer_drills_without_drills(self):
        md, note = answer_drills("### Drill deck\n\nnothing here", "Biology")
        self.assertIn("Build a packet", md)

    def test_packet_to_markdown_assembles_and_strips_html(self):
        md = packet_to_markdown(
            "### Rescue plan\n\nDo X",
            "### Drill deck\n\n- d1",
            "### Triage clock\n\n- Panic pattern: calm",
            "<section><h2>Final Sheet for You</h2><p>First action</p></section>",
            "### Study receipt\n\n- Before: ...",
        )
        self.assertIn("Rescue plan", md)
        self.assertIn("Drill deck", md)
        self.assertIn("Final Sheet for You", md)
        self.assertIn("First action", md)
        self.assertNotIn("<section>", md)

    def test_coach_state_walks_through_blocks(self):
        blocks = [("Reset", 5), ("Core", 30), ("Final", 10)]  # 45 min total
        s0 = coach_state(blocks, 0)
        self.assertFalse(s0["done"])
        self.assertEqual(s0["current"], "Reset")
        self.assertEqual(s0["next"], "Core")
        self.assertLessEqual(s0["remaining_s"], 5 * 60)
        s1 = coach_state(blocks, 6 * 60)  # 6 min in -> Core
        self.assertEqual(s1["current"], "Core")
        self.assertEqual(s1["next"], "Final")
        s_end = coach_state(blocks, 50 * 60)
        self.assertTrue(s_end["done"])

    def test_synthesize_speech_handles_empty_text(self):
        path, note = synthesize_speech("", "/tmp/x.wav")
        self.assertIsNone(path)
        self.assertIn("build a packet", note.lower())

    def test_extract_topics_from_image_handles_no_image(self):
        topics, note = extract_topics_from_image("")
        self.assertEqual(topics, "")
        self.assertIn("type your topics", note.lower())

    def test_coach_state_handles_empty_schedule(self):
        self.assertTrue(coach_state([], 0)["done"])

    def test_triage_names_topics_to_skip_when_many(self):
        plan = build_rescue_plan(
            student_name="Aarav", subject="Physics", time_left_minutes=120, exam_format="Mixed",
            panic_note="I go blank in numericals.",
            known_material="work-energy theorem, kinetic energy, potential energy, power, conservation of energy",
            confidence=2,
        )
        self.assertIn("drop these first", plan.triage_markdown.lower())
        self.assertIn("conservation of energy", plan.triage_markdown)

    def test_force_fallback_skips_model_and_stays_complete(self):
        plan = build_rescue_plan(
            student_name="Zoya", subject="History: nationalism in India", time_left_minutes=1440,
            exam_format="Long answer", panic_note="my long answers become messy.",
            known_material="non-cooperation movement, salt march", confidence=3, force_fallback=True,
        )
        self.assertIn("fallback", plan.model_note.lower())
        self.assertIn("Final Sheet", plan.final_sheet_html)
        self.assertIn("Drill deck", plan.drill_markdown)

    def test_build_rescue_plan_accepts_model_choice(self):
        plan = build_rescue_plan(
            student_name="Aarav", subject="Physics", time_left_minutes=120, exam_format="Mixed",
            panic_note="I blank on numericals", known_material="kinetic energy, power", confidence=2,
            model_id="nvidia/Nemotron-Mini-4B-Instruct",
        )
        self.assertIn("Rescue plan", plan.rescue_plan_markdown)
        self.assertIn("Drill deck", plan.drill_markdown)

    def test_model_size_label_marks_tiny_titan_paths(self):
        self.assertEqual(model_size_label("openbmb/MiniCPM4.1-8B"), "8B")
        self.assertEqual(model_size_label("openbmb/MiniCPM4-0.5B"), "0.5B")
        self.assertEqual(model_size_label("nvidia/Nemotron-Mini-4B-Instruct"), "4B")
        self.assertEqual(model_size_label("unknown/model"), "")

    def test_weakness_detection_ignores_substring_false_positives(self):
        # 'summarize'/'assume' contain 'sum' but must not be misread as numerical work.
        self.assertNotIn("worked problems", detect_weaknesses("I need to summarize and assume the rest."))
        # Genuine numerical language is still caught.
        self.assertIn("worked problems", detect_weaknesses("I blank on the sums and numericals."))

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

    def test_nemotron_fallback_is_configured_but_default_off(self):
        self.assertEqual(NEMOTRON_FALLBACK_MODEL_ID, "nvidia/Nemotron-Mini-4B-Instruct")
        self.assertFalse(nemotron_fallback_enabled())

    def test_nemotron_fallback_route_is_after_primary_model_failure(self):
        data = StudyInput(
            student_name="Nia",
            subject="Machine Learning",
            time_left_minutes=90,
            exam_format="Mixed",
            panic_note="I mix up precision and recall.",
            known_material="precision, recall, confusion matrix",
            confidence=2,
        )

        calls = []

        def fake_transformer_rescue(model_id, *_):
            calls.append(model_id)
            if model_id == "openbmb/MiniCPM4.1-8B":
                return None, "primary failed"
            return "5 practice questions:\n- Explain precision vs recall.", "Generated with nvidia/Nemotron-Mini-4B-Instruct on CUDA/ZeroGPU."

        with patch("study_engine.USE_LOCAL_MODEL", True), patch("study_engine.USE_NEMOTRON_FALLBACK", True), patch(
            "study_engine.transformer_rescue", side_effect=fake_transformer_rescue
        ):
            import study_engine

            generated, note = study_engine.model_rescue(data, ["precision", "recall"])

        self.assertEqual(calls, ["openbmb/MiniCPM4.1-8B", "nvidia/Nemotron-Mini-4B-Instruct"])
        self.assertIn("precision vs recall", generated)
        self.assertIn("Nemotron-Mini-4B-Instruct", note)
        self.assertIn("fallback", note)

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

    def test_strips_closed_think_tags_from_model_output(self):
        text = generated_text_from_pipeline_result(
            [{"generated_text": [{"role": "assistant", "content": "<think>private reasoning</think>5 practice questions: Start."}]}]
        )

        self.assertEqual(text, "5 practice questions: Start.")

    def test_preserves_model_markdown_and_unescapes_newlines(self):
        text = generated_text_from_pipeline_result(
            [
                {
                    "generated_text": [
                        {
                            "role": "assistant",
                            "content": "5 practice questions:\\n- Explain precision vs recall.\\n\\n4-step survival plan:\\n1. Start with the confusion matrix.",
                        }
                    ]
                }
            ]
        )

        self.assertNotIn("\\n", text)
        self.assertIn("5 practice questions:\n- Explain precision vs recall.", text)
        self.assertIn("\n\n4-step survival plan:\n1. Start with the confusion matrix.", text)

    def test_drops_incomplete_think_tag_model_output(self):
        text = generated_text_from_pipeline_result(
            [{"generated_text": [{"role": "assistant", "content": "<think>private reasoning that never closes"}]}]
        )

        self.assertEqual(text, "")

    def test_strips_prompt_echo_from_llama_cli_output(self):
        text = generated_text_from_llama_cli_output(
            "Loading model...\nmodel : tiny\n> student panic\n\n1. Reset.\n2. Drill.\n\n[ Prompt: 10 t/s | Generation: 20 t/s ]\nExiting...",
            prompt="student panic",
        )

        self.assertEqual(text, "1. Reset.\n2. Drill.")


if __name__ == "__main__":
    unittest.main()
