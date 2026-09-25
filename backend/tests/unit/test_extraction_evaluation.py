import json
import subprocess
import sys

from procureflow.scripts.evaluate_extraction import evaluate


def test_synthetic_extraction_evaluation_is_repeatable():
    first = evaluate()
    assert first == evaluate()
    assert len(first) == 4
    for case in first:
        assert case["expected_line_items"] == case["actual_line_items"] == 3
        assert case["unmatched_items"] == 1
        assert case["buyer_review_required"] is True
    clean = [case for case in first if case["fixture"] != "edge_case_warnings.csv"]
    assert all(not case["differences"] for case in clean)
    imperfect = next(case for case in first if case["fixture"] == "edge_case_warnings.csv")
    assert imperfect["differences"] == ["line 3 unit_price: expected None, actual 0"]
    assert imperfect["warning_count"] > 0


def test_evaluation_command_outputs_parseable_json():
    result = subprocess.run(
        [sys.executable, "-m", "procureflow.scripts.evaluate_extraction"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    assert len(json.loads(result.stdout)) == 4
