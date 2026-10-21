"""Unit tests for tools (ORV-3). No real app launches, no network."""
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


def test_calculator_opens(monkeypatch):
    monkeypatch.setattr(tools.sys, "platform", "win32")
    monkeypatch.setattr(tools.subprocess, "Popen", lambda *a, **k: None)
    assert tools.launch_calculator() == "Calculator opened."


def test_calculator_fails_off_windows(monkeypatch):
    monkeypatch.setattr(tools.sys, "platform", "linux")
    assert tools.launch_calculator().startswith("ERROR:")


def test_calculator_launch_error_is_reported(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("calc.exe missing")

    monkeypatch.setattr(tools.sys, "platform", "win32")
    monkeypatch.setattr(tools.subprocess, "Popen", boom)
    assert tools.launch_calculator().startswith("ERROR:")


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


def test_only_allowlisted_tools_are_exposed():
    assert {t.name for t in tools.TOOLS} == {"open_calculator", "get_weather"}


def test_tool_wrapper_passes_failure_through(monkeypatch):
    monkeypatch.setattr(tools, "launch_calculator", lambda: "ERROR: simulated")
    assert tools.open_calculator.invoke({}).startswith("ERROR:")
