"""Tests for the console UI helpers and screens. Output is captured, no real terminal needed."""
import io

import pytest
from rich.console import Console

from src import tools
from src.errors import MESSAGES
from src.ui import ConsoleUI, format_args, parse_command, short


def make_ui(answers=None):
    """A UI that writes to a string and answers prompts from a list."""
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=False, width=100, color_system=None)
    queue = list(answers or [])
    return ConsoleUI(console, input_func=lambda prompt: queue.pop(0)), buffer


# ---------- commands and formatting ----------
@pytest.mark.parametrize("text, expected", [
    ("/help", "help"), ("/TOOLS", "tools"), ("  /clear ", "clear"),
    ("/exit", "exit"), ("exit", "exit"), ("Quit", "exit"),
    ("/banana", "unknown"), ("open notepad", None), ("", None),
])
def test_parse_command(text, expected):
    assert parse_command(text) == expected


def test_short_collapses_whitespace_and_truncates():
    assert short("a   b\n c") == "a b c"
    assert short("x" * 300, 20) == "x" * 17 + "..."


def test_format_args_is_compact():
    text = format_args({"filename": "todo.txt", "content": "z" * 200})
    assert text.startswith("filename='todo.txt', content='")
    assert text.endswith("...")
    assert format_args({}) == ""


# ---------- screens ----------
def test_banner_help_and_tools_screens():
    ui, out = make_ui()
    ui.banner("gemini-test", "v2", tools.TOOLS)
    ui.help()
    ui.tools(tools.TOOLS)
    text = out.getvalue()
    assert "Orvyn" in text and "gemini-test" in text and "Tools: 5" in text
    for command in ("/help", "/tools", "/clear", "/exit"):
        assert command in text
    for tool in tools.TOOLS:
        assert tool.name in text


def test_trace_shows_calls_results_and_numbers_the_steps():
    ui, out = make_ui()
    ui.on_step({"type": "tool_call", "name": "get_weather", "args": {"location": "Lahore"}})
    ui.on_step({"type": "tool_result", "name": "get_weather", "content": "Weather in Lahore: 24C", "elapsed": 0.42})
    ui.on_step({"type": "tool_call", "name": "write_file", "args": {"filename": "w.txt", "content": "hi"}})
    ui.on_step({"type": "tool_result", "name": "write_file", "content": "ERROR: The user did not approve", "elapsed": None})
    text = out.getvalue()
    assert "Step 1" in text and "get_weather(location='Lahore')" in text
    assert "Weather in Lahore: 24C" in text and "(0.4s)" in text
    assert "Step 2" in text and "x ERROR: The user did not approve" in text


def test_tool_text_cannot_inject_rich_markup():
    ui, out = make_ui()
    ui.on_step({"type": "tool_result", "name": "read_file", "content": "[bold red]boom[/bold red] [fonts]", "elapsed": None})
    assert "[bold red]boom[/bold red] [fonts]" in out.getvalue()


def test_prompt_resets_the_step_counter():
    ui, out = make_ui(["hello", "again"])
    ui.prompt()
    ui.on_step({"type": "tool_call", "name": "open_app", "args": {}})
    ui.prompt()
    ui.on_step({"type": "tool_call", "name": "open_app", "args": {}})
    assert out.getvalue().count("Step 1") == 2


def test_answers_and_errors_are_shown_in_the_right_panel():
    ui, out = make_ui()
    ui.show_answer("Hello **there**")
    assert "Orvyn" in out.getvalue() and "there" in out.getvalue()
    ui2, out2 = make_ui()
    ui2.show_answer(MESSAGES["network"])
    assert "Problem" in out2.getvalue()


def test_summary_line():
    ui, out = make_ui()
    ui.summary(1.234, ["get_weather", "get_weather", "write_file"])
    ui.summary(0.5, [])
    text = out.getvalue()
    assert "3 tool calls: get_weather, get_weather, write_file | 1.2s" in text
    assert "0 tool calls | 0.5s" in text
    ui.summary(0.5, ["open_app"])
    assert "1 tool call: open_app" in out.getvalue()


# ---------- approval ----------
@pytest.mark.parametrize("answer, expected", [
    ("y", True), ("YES", True), (" yes ", True),
    ("n", False), ("", False), ("sure", False), ("yep", False),
])
def test_only_a_clear_yes_approves(answer, expected):
    ui, out = make_ui([answer])
    assert ui.ask_approval("Orvyn wants to create workspace/todo.txt") is expected
    assert "Approval needed" in out.getvalue() and "workspace/todo.txt" in out.getvalue()


def test_approval_works_while_the_spinner_is_active():
    ui, _ = make_ui(["y"])
    with ui.thinking():
        assert ui.ask_approval("Orvyn wants to create workspace/a.txt") is True
        assert ui._status is not None  # spinner is running again after the question
    assert ui._status is None


def test_approval_prompt_shows_the_y_n_hint(monkeypatch):
    """Rich markup must not swallow the [y/N] hint (uses the real console.input)."""
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=False, width=100, color_system=None)
    monkeypatch.setattr("builtins.input", lambda *a: "y")
    ui = ConsoleUI(console)
    assert ui.ask_approval("Orvyn wants to create workspace/a.txt") is True
    assert "Allow? [y/N]" in buffer.getvalue()
