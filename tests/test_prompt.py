"""Prompt tests: prompts are versioned and contain the honesty and safety rules."""
import pytest

from src import config


def test_default_prompt_is_v2():
    assert "version: v2" in config.load_system_prompt()


def test_v1_is_still_available():
    assert "version: v1" in config.load_system_prompt("v1")


def test_v2_contains_honesty_and_safety_rules():
    text = config.load_system_prompt("v2").lower()
    assert "error:" in text
    assert "never invent" in text
    assert "never reveal" in text
    assert "open_app" in text


def test_unknown_prompt_version_raises():
    with pytest.raises(config.ConfigError):
        config.load_system_prompt("v999")
