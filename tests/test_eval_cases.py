"""Format test for the evaluation prompt set (owned by the Product Owner). No API calls."""
import json
from pathlib import Path

CASES_FILE = Path(__file__).resolve().parent.parent / "evaluation" / "prompts.json"
REQUIRED_CATEGORIES = {"normal", "tool use", "unsupported", "hallucination", "prompt injection", "ambiguous"}


def load():
    return json.loads(CASES_FILE.read_text(encoding="utf-8"))


def test_at_least_twelve_cases():
    assert len(load()) >= 12


def test_every_case_has_required_fields_and_unique_id():
    cases = load()
    assert len({c["id"] for c in cases}) == len(cases)
    for case in cases:
        assert case["id"] and case["category"] and case["prompt"]


def test_every_category_is_covered():
    assert REQUIRED_CATEGORIES <= {c["category"] for c in load()}


def test_every_case_states_an_expected_behaviour():
    keys = {"must_include_any", "must_not_include", "expect_tools", "expect_no_tool"}
    for case in load():
        assert keys & set(case), f"{case['id']} has no expected behaviour"
