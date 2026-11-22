"""Tests for the evaluation runner logic. No API calls."""
import json

from evaluation.run_eval import evaluate_case, run_cases, write_reports


def test_passing_case_has_no_failures():
    case = {"must_include_any": ["Islamabad"], "expect_no_tool": True}
    assert evaluate_case(case, "The capital is Islamabad.", []) == []


def test_missing_required_word_fails():
    assert evaluate_case({"must_include_any": ["Islamabad"]}, "I am not sure.", [])


def test_forbidden_text_fails():
    case = {"must_not_include": ["http"]}
    assert evaluate_case(case, "See http://fake.example", [])


def test_expected_tool_missing_fails():
    assert evaluate_case({"expect_tools": ["get_weather"]}, "Sunny", [])
    assert evaluate_case({"expect_tools": ["get_weather"]}, "Sunny", ["get_weather"]) == []


def test_unexpected_tool_use_fails():
    assert evaluate_case({"expect_no_tool": True}, "Done", ["open_app"])


def test_curly_apostrophes_are_normalised():
    assert evaluate_case({"must_include_any": ["can't"]}, "Sorry, I can\u2019t do that.", []) == []


class FakeOrvyn:
    def __init__(self):
        self.last_tool_calls = []

    def ask(self, text):
        self.last_tool_calls = ["get_weather"] if "weather" in text else []
        return "It is sunny in Lahore." if "weather" in text else "Hello"


def test_run_cases_and_reports(tmp_path):
    cases = [
        {"id": "a", "category": "tool use", "prompt": "weather in Lahore", "expect_tools": ["get_weather"]},
        {"id": "b", "category": "normal", "prompt": "hi", "must_include_any": ["missing-word"]},
    ]
    results = run_cases(cases, FakeOrvyn, delay=0)
    assert [r["passed"] for r in results] == [True, False]

    json_path, md_path = write_reports(results, "vtest", out_dir=tmp_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["passed"] == 1 and data["total"] == 2
    assert "| a | tool use | PASS |" in md_path.read_text(encoding="utf-8")
