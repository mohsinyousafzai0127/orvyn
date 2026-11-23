"""Tests for the live agent trace. No API key: a scripted fake model drives the REAL agent graph."""
import pytest
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from src import approval, tools, workspace
from src.agent import Orvyn


class FakeToolModel(GenericFakeChatModel):
    """A fake chat model that can be given tools, so create_agent accepts it."""

    def bind_tools(self, tools, **kwargs):
        return self


def call(name, args, call_id):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def make_orvyn(*scripted):
    agent = create_agent(model=FakeToolModel(messages=iter(scripted)), tools=tools.TOOLS, system_prompt="test")
    return Orvyn(agent=agent, retry_delay=0)


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "WORKSPACE_DIR", tmp_path / "workspace")
    monkeypatch.setattr(tools.requests, "get", fake_weather_get)
    approval.clear_approver()
    yield tmp_path / "workspace"
    approval.clear_approver()


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def fake_weather_get(url, params=None, timeout=None):
    if "geocoding" in url:
        return FakeResponse({"results": [{"name": params["name"], "country": "Pakistan", "latitude": 1, "longitude": 2}]})
    return FakeResponse({"current": {"temperature_2m": 20.0, "wind_speed_10m": 5.0, "weather_code": 0}})


# ---------- the real agent graph with scripted model ----------
def test_multi_step_task_streams_every_step_in_order(sandbox):
    approval.set_approver(lambda description: True)
    orvyn = make_orvyn(
        call("get_weather", {"location": "Rawalpindi"}, "c1"),
        call("get_weather", {"location": "Lahore"}, "c2"),
        call("write_file", {"filename": "weather.txt", "content": "Both cities are clear."}, "c3"),
        AIMessage(content="Saved the comparison to weather.txt."),
    )
    events = []
    reply = orvyn.ask("Compare the weather and save it", on_step=events.append)

    assert reply == "Saved the comparison to weather.txt."
    assert [(e["type"], e["name"]) for e in events] == [
        ("tool_call", "get_weather"), ("tool_result", "get_weather"),
        ("tool_call", "get_weather"), ("tool_result", "get_weather"),
        ("tool_call", "write_file"), ("tool_result", "write_file"),
    ]
    assert events[0]["args"] == {"location": "Rawalpindi"}
    assert "Rawalpindi" in events[1]["content"] and events[1]["elapsed"] is not None
    assert events[5]["content"].startswith("Saved")
    assert (sandbox / "weather.txt").read_text(encoding="utf-8") == "Both cities are clear."
    assert orvyn.last_tool_calls == ["get_weather", "get_weather", "write_file"]


def test_denied_write_is_traced_as_an_error_and_nothing_is_saved(sandbox):
    approval.set_approver(lambda description: False)
    orvyn = make_orvyn(
        call("write_file", {"filename": "todo.txt", "content": "buy milk"}, "c1"),
        AIMessage(content="You did not approve it, so nothing was saved."),
    )
    events = []
    orvyn.ask("Save a note", on_step=events.append)
    assert events[1]["content"].startswith("ERROR:")
    assert not (sandbox / "todo.txt").exists()


def test_escape_attempt_is_traced_as_an_error(sandbox):
    orvyn = make_orvyn(
        call("read_file", {"filename": "C:/Windows/win.ini"}, "c1"),
        AIMessage(content="I cannot read files outside the workspace."),
    )
    events = []
    orvyn.ask("Read win.ini", on_step=events.append)
    assert events[1]["type"] == "tool_result" and events[1]["content"].startswith("ERROR:")


def test_conversation_continues_after_a_streamed_question():
    orvyn = make_orvyn(AIMessage(content="First answer."), AIMessage(content="Second answer."))
    assert orvyn.ask("one", on_step=lambda e: None) == "First answer."
    assert orvyn.ask("two", on_step=lambda e: None) == "Second answer."
    assert len(orvyn.history) == 4  # two questions and two answers


def test_streaming_and_plain_mode_give_the_same_reply():
    plain = make_orvyn(call("get_weather", {"location": "Lahore"}, "c1"), AIMessage(content="Clear in Lahore."))
    streamed = make_orvyn(call("get_weather", {"location": "Lahore"}, "c1"), AIMessage(content="Clear in Lahore."))
    assert plain.ask("weather?") == streamed.ask("weather?", on_step=lambda e: None) == "Clear in Lahore."


# ---------- streaming behaviour with a simple fake agent ----------
class StreamAgent:
    def __init__(self, chunks=None, error=None):
        self.chunks = chunks or []
        self.error = error

    def stream(self, payload, stream_mode=None):
        assert stream_mode == "values"
        if self.error:
            raise self.error
        yield from self.chunks


def test_streaming_failure_returns_a_friendly_message():
    orvyn = Orvyn(agent=StreamAgent(error=Exception("403 permission denied: API key not valid")), retry_delay=0)
    assert "api key" in orvyn.ask("hi", on_step=lambda e: None).lower()
    assert orvyn.history == []


def test_streaming_with_no_output_is_handled_gracefully():
    orvyn = Orvyn(agent=StreamAgent(chunks=[]), retry_delay=0)
    reply = orvyn.ask("hi", on_step=lambda e: None)
    assert "went wrong" in reply.lower()


def test_reset_clears_the_conversation():
    orvyn = make_orvyn(AIMessage(content="Hi."))
    orvyn.ask("hello", on_step=lambda e: None)
    orvyn.reset()
    assert orvyn.history == [] and orvyn.last_tool_calls == []
