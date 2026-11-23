"""Unit tests for tools (Sprint 1 weather, Sprint 2 app launcher). No real app launches, no network."""
import pytest

from src import tools


class FakeResponse:
    def __init__(self, data, status=200):
        self.data = data
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise tools.requests.HTTPError("bad status")

    def json(self):
        return self.data


def fake_weather_get(url, params=None, timeout=None):
    if "geocoding" in url:
        return FakeResponse(
            {"results": [{"name": "Rawalpindi", "country": "Pakistan", "latitude": 33.6, "longitude": 73.0}]}
        )
    return FakeResponse({"current": {"temperature_2m": 24.5, "wind_speed_10m": 7.2, "weather_code": 0}})


@pytest.fixture
def windows(monkeypatch):
    """Pretend to run on Windows and record which executables would be launched."""
    launched = []
    monkeypatch.setattr(tools.sys, "platform", "win32")
    monkeypatch.setattr(tools.subprocess, "Popen", lambda args, *a, **k: launched.append(args))
    return launched


# ---------- app launcher ----------
def test_open_calculator(windows):
    assert tools.launch_app("calculator") == "Calculator opened."
    assert windows == [["calc.exe"]]


def test_alias_and_case_are_handled(windows):
    assert tools.launch_app("  CALC ") == "Calculator opened."
    assert tools.launch_app("Notepad") == "Notepad opened."
    assert windows == [["calc.exe"], ["notepad.exe"]]


def test_unlisted_app_is_refused_without_launching(windows):
    result = tools.launch_app("registry editor")
    assert result.startswith("ERROR:") and "not on the allowed list" in result
    assert windows == []


def test_command_chaining_attempt_is_refused(windows):
    result = tools.launch_app("notepad && del C:\\important")
    assert result.startswith("ERROR:")
    assert windows == []


def test_empty_app_name_is_rejected(windows):
    assert tools.launch_app("   ").startswith("ERROR:")
    assert windows == []


def test_app_launch_fails_off_windows(monkeypatch):
    monkeypatch.setattr(tools.sys, "platform", "linux")
    assert tools.launch_app("notepad").startswith("ERROR:")


def test_launch_error_is_reported(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(tools.sys, "platform", "win32")
    monkeypatch.setattr(tools.subprocess, "Popen", boom)
    assert tools.launch_app("paint").startswith("ERROR:")


def test_browser_opens(monkeypatch):
    monkeypatch.setattr(tools.sys, "platform", "win32")
    monkeypatch.setattr(tools.webbrowser, "open", lambda url: True)
    assert tools.launch_app("browser") == "Browser opened."


# ---------- weather ----------
def test_weather_success(monkeypatch):
    monkeypatch.setattr(tools.requests, "get", fake_weather_get)
    result = tools.fetch_weather("Rawalpindi")
    assert "Rawalpindi" in result and "24.5" in result and "clear sky" in result


def test_weather_unknown_place(monkeypatch):
    monkeypatch.setattr(tools.requests, "get", lambda *a, **k: FakeResponse({}))
    assert tools.fetch_weather("Nowhereville").startswith("ERROR:")


def test_weather_network_failure(monkeypatch):
    def boom(*a, **k):
        raise tools.requests.ConnectionError("no internet")

    monkeypatch.setattr(tools.requests, "get", boom)
    assert tools.fetch_weather("Rawalpindi").startswith("ERROR:")


def test_weather_empty_location():
    assert tools.fetch_weather("   ").startswith("ERROR:")


# ---------- allowlist ----------
def test_only_allowlisted_tools_are_exposed():
    assert {t.name for t in tools.TOOLS} == {"open_app", "get_weather", "list_files", "read_file", "write_file"}


def test_tool_wrapper_passes_failure_through(monkeypatch):
    monkeypatch.setattr(tools, "launch_app", lambda name: "ERROR: simulated")
    assert tools.open_app.invoke({"app_name": "notepad"}).startswith("ERROR:")
