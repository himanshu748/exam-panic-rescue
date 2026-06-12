from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["USE_LOCAL_MODEL"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from study_engine import DEMO_CASES, build_rescue_plan


CASES = DEMO_CASES
CHECK_COUNT = 6


def score_case(case: dict[str, object]) -> tuple[int, list[str]]:
    plan = build_rescue_plan(
        student_name=str(case["student_name"]),
        subject=str(case["subject"]),
        time_left_minutes=int(case["time_left_minutes"]),
        exam_format=str(case["exam_format"]),
        panic_note=str(case["panic_note"]),
        known_material=str(case["known_material"]),
        confidence=int(case["confidence"]),
    )
    combined = "\n".join(
        [
            plan.rescue_plan_markdown,
            plan.drill_markdown,
            plan.triage_markdown,
            plan.final_sheet_html,
            plan.demo_receipt_markdown,
            plan.model_note,
        ]
    ).lower()
    checks = {
        "rescue plan": "rescue plan" in plan.rescue_plan_markdown.lower(),
        "five drills": plan.drill_markdown.count("- ") >= 5,
        "triage boundary": "verify facts with your class notes" in plan.triage_markdown.lower(),
        "final sheet": "final sheet" in plan.final_sheet_html.lower(),
        "study receipt": "study receipt" in plan.demo_receipt_markdown.lower(),
        "specific terms": all(str(term).lower() in combined for term in case["must_include"]),
    }
    missing = [name for name, ok in checks.items() if not ok]
    return len(checks) - len(missing), missing


def main() -> int:
    total = 0
    possible = len(CASES) * CHECK_COUNT
    failures = []

    for case in CASES:
        score, missing = score_case(case)
        total += score
        print(f"{case['name']}: {score}/{CHECK_COUNT}")
        if missing:
            failures.append(f"{case['name']}: missing {', '.join(missing)}")

    print(f"\nReadiness smoke score: {total}/{possible}")
    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
