"""Tests for retry with backoff and tool-call tracking (Sprint 2). No real waiting, no API."""
import pytest
from langchain_core.messages import AIMessage

from src.agent import Orvyn, extract_tool_names
from src.errors import classify_error, is_transient
from src.resilience import call_with_retry


class Flaky:
    """Fails with `error` a number of times, then succeeds."""

    def __init__(self, failures, error):
        self.failures = failures
        self.error = error
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return "ok"


def test_classify_error_categories():
    assert classify_error(Exception("429 quota")) == "rate_limit"
    assert classify_error(Exception("API key not valid")) == "auth"
    assert classify_error(ConnectionError("refused")) == "network"
    assert classify_error(Exception("503 UNAVAILABLE")) == "unavailable"
    assert classify_error(Exception("boom")) == "unknown"


def test_only_temporary_errors_are_transient():
    assert is_transient(Exception("429 quota"))
    assert not is_transient(Exception("API key not valid"))
    assert not is_transient(Exception("boom"))


def test_retry_succeeds_after_transient_failures():
    delays = []
    func = Flaky(2, Exception("503 UNAVAILABLE"))
    assert call_with_retry(func, attempts=3, base_delay=1.0, sleep=delays.append) == "ok"
    assert func.calls == 3
    assert delays == [1.0, 2.0]  # exponential backoff


def test_retry_gives_up_after_attempt_limit():
    delays = []
    func = Flaky(10, Exception("429 quota"))
    with pytest.raises(Exception, match="429"):
        call_with_retry(func, attempts=3, sleep=delays.append)
    assert func.calls == 3


def test_non_transient_error_is_not_retried():
    func = Flaky(10, Exception("403 API key not valid"))
    with pytest.raises(Exception):
        call_with_retry(func, attempts=3, sleep=lambda d: None)
    assert func.calls == 1


class FlakyAgent:
    def __init__(self, failures):
        self.failures = failures
        self.calls = 0

    def invoke(self, payload):
        self.calls += 1
        if self.calls <= self.failures:
            raise Exception("429 RESOURCE_EXHAUSTED")
        return {"messages": list(payload["messages"]) + [AIMessage(content="Recovered")]}


def test_orvyn_recovers_from_a_temporary_rate_limit():
    agent = FlakyAgent(failures=2)
    assert Orvyn(agent=agent, retry_delay=0).ask("hello") == "Recovered"
    assert agent.calls == 3


def test_orvyn_shows_friendly_message_when_retries_run_out():
    reply = Orvyn(agent=FlakyAgent(failures=10), retry_delay=0).ask("hello")
    assert "rate" in reply.lower()


def test_tool_calls_are_extracted_and_remembered():
    message = AIMessage(content="", tool_calls=[{"name": "open_app", "args": {"app_name": "notepad"}, "id": "1"}])
    assert extract_tool_names([("user", "hi"), message]) == ["open_app"]


def test_last_tool_calls_is_reset_for_each_question():
    class ToolAgent:
        def invoke(self, payload):
            call = {"name": "get_weather", "args": {"location": "Lahore"}, "id": "1"}
            return {"messages": list(payload["messages"]) + [AIMessage(content="", tool_calls=[call]),
                                                              AIMessage(content="Sunny")]}

    orvyn = Orvyn(agent=ToolAgent(), retry_delay=0)
    orvyn.ask("weather in Lahore?")
    assert orvyn.last_tool_calls == ["get_weather"]
    orvyn.ask("   ")  # rejected input does not call the agent
    assert orvyn.last_tool_calls == ["get_weather"]
