"""Tools Orvyn may call.

Only the functions in TOOLS are exposed to the model (an allowlist), so it can
never run arbitrary commands. Tools never raise: on failure they return text
starting with 'ERROR:' so the agent can report the failure honestly.
"""
import subprocess
import sys
import webbrowser

import requests
from langchain_core.tools import tool

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = 10
BROWSER_URL = "https://www.google.com"

# Only these applications can be opened. No shell is ever used.
ALLOWED_APPS = {
    "calculator": "calc.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "file explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
}
APP_ALIASES = {
    "calc": "calculator",
    "windows calculator": "calculator",
    "text editor": "notepad",
    "mspaint": "paint",
    "explorer": "file explorer",
    "files": "file explorer",
    "taskmgr": "task manager",
}

WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "fog", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 71: "light snow",
    73: "snow", 75: "heavy snow", 80: "rain showers", 95: "thunderstorm",
}


def normalize_app_name(name: str) -> str:
    """Lower-case the name and map common aliases (for example 'calc')."""
    key = (name or "").strip().lower()
    return APP_ALIASES.get(key, key)


def launch_app(app_name: str) -> str:
    """Open an allowlisted Windows application."""
    key = normalize_app_name(app_name)
    if not key:
        return "ERROR: No application name was provided."
    if key != "browser" and key not in ALLOWED_APPS:
        allowed = ", ".join(sorted(list(ALLOWED_APPS) + ["browser"]))
        return f"ERROR: '{app_name.strip()}' is not on the allowed list. Allowed apps: {allowed}."
    if sys.platform != "win32":
        return "ERROR: Opening applications is only supported on Windows."
    try:
        if key == "browser":
            if not webbrowser.open(BROWSER_URL):
                return "ERROR: Could not open the browser."
        else:
            subprocess.Popen([ALLOWED_APPS[key]])
    except OSError as exc:
        return f"ERROR: Could not open {key} ({type(exc).__name__})."
    return f"{key.title()} opened."


def fetch_weather(location: str) -> str:
    """Get current weather for a place from the free Open-Meteo API."""
    location = (location or "").strip()
    if not location:
        return "ERROR: No location was provided."
    try:
        geo = requests.get(
            GEOCODING_URL, params={"name": location, "count": 1}, timeout=REQUEST_TIMEOUT
        )
        geo.raise_for_status()
        results = geo.json().get("results")
        if not results:
            return f"ERROR: Could not find a place called '{location}'."
        place = results[0]

        forecast = requests.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,wind_speed_10m,weather_code",
            },
            timeout=REQUEST_TIMEOUT,
        )
        forecast.raise_for_status()
        current = forecast.json()["current"]
        condition = WEATHER_CODES.get(current.get("weather_code"), "unspecified conditions")
        return (
            f"Weather in {place['name']}, {place.get('country', '')}: "
            f"{current['temperature_2m']}°C, {condition}, "
            f"wind {current['wind_speed_10m']} km/h (live data from Open-Meteo)."
        )
    except (requests.RequestException, KeyError, ValueError):
        return "ERROR: Could not retrieve weather data right now."


@tool
def open_app(app_name: str) -> str:
    """Open an allowed Windows application: calculator, notepad, paint, file explorer, task manager or browser."""
    return launch_app(app_name)


@tool
def get_weather(location: str) -> str:
    """Get the current real weather for a city, for example 'Rawalpindi'."""
    return fetch_weather(location)


TOOLS = [open_app, get_weather]
