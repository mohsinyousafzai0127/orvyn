"""Live tests against the real Gemini API. Run with: set RUN_LIVE_TESTS=1 && pytest (Windows)."""
import os

import pytest

from src import tools
from src.agent import Orvyn

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.getenv("RUN_LIVE_TESTS") != "1", reason="Set RUN_LIVE_TESTS=1 to call the real API"),
]

FAILURE_WORDS = ("couldn't", "couldn’t", "could not", "unable", "failed", "error", "not able", "can't", "can’t", "cannot")


def test_live_gemini_answers_a_question():
    reply = Orvyn().ask("In one sentence, what is an AI agent?")
    assert len(reply) > 20


def test_live_orvyn_does_not_claim_success_when_tool_fails(monkeypatch):
    monkeypatch.setattr(tools, "launch_calculator", lambda: "ERROR: Could not open Calculator (simulated failure).")
    reply = Orvyn().ask("Please open the calculator.").lower()
    assert any(word in reply for word in FAILURE_WORDS), reply
