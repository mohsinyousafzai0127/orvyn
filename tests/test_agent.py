"""Unit tests for the Orvyn agent and error handling (ORV-1, ORV-2, ORV-4). Model is mocked."""
import pytest
from langchain_core.messages import AIMessage

from src import config
from src.agent import Orvyn, message_to_text
from src.errors import friendly_error


class FakeAgent:
    def __init__(self, reply="Hello!", error=None):
        self.reply = reply
        self.error = error
        self.calls = []

    def invoke(self, payload):
        self.calls.append(payload)
        if self.error:
            raise self.error
        return {"messages": list(payload["messages"]) + [AIMessage(content=self.reply)]}


def test_ask_returns_model_reply():
    assert Orvyn(agent=FakeAgent("Hi there")).ask("Hello") == "Hi there"


def test_empty_input_is_rejected_without_calling_agent():
    agent = FakeAgent()
    assert "type a request" in Orvyn(agent=agent).ask("   ").lower()
    assert agent.calls == []


def test_too_long_input_is_rejected():
    agent = FakeAgent()
    reply = Orvyn(agent=agent).ask("x" * (config.MAX_INPUT_CHARS + 1))
    assert "too long" in reply.lower()
    assert agent.calls == []


def test_history_is_kept_between_questions():
    agent = FakeAgent()
    orvyn = Orvyn(agent=agent)
    orvyn.ask("first")
    orvyn.ask("second")
    assert len(agent.calls[1]["messages"]) == 3  # first question, first reply, second question


def test_failed_call_returns_friendly_message_and_keeps_history_clean():
    orvyn = Orvyn(agent=FakeAgent(error=Exception("429 RESOURCE_EXHAUSTED")))
    reply = orvyn.ask("hello")
    assert "rate" in reply.lower()
    assert orvyn.history == []


@pytest.mark.parametrize(
    "exc, expected",
    [
        (ConnectionError("Connection refused"), "connect"),
        (Exception("429 quota exceeded"), "rate"),
        (Exception("API key not valid"), "api key"),
        (Exception("503 UNAVAILABLE"), "unavailable"),
        (Exception("boom"), "went wrong"),
    ],
)
def test_friendly_error_categories(exc, expected):
    message = friendly_error(exc)
    assert expected in message.lower()
    assert "Traceback" not in message


def test_message_to_text_handles_plain_text_and_blocks():
    assert message_to_text("  hi ") == "hi"
    assert message_to_text([{"type": "text", "text": "Hi"}, {"type": "text", "text": " there"}]) == "Hi there"


def test_missing_api_key_raises_config_error(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(config.ConfigError):
        config.get_api_key()
    with pytest.raises(config.ConfigError):
        Orvyn()
