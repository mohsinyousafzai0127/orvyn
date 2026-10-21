"""Prompt tests: the system prompt is versioned and contains the honesty rules (ORV-2, ORV-5)."""
import pytest

from src import config


def test_prompt_has_version_header():
    assert "version: v1" in config.load_system_prompt()


def test_prompt_contains_honesty_rules():
    text = config.load_system_prompt().lower()
    assert "error:" in text
    assert "never invent" in text


def test_unknown_prompt_version_raises():
    with pytest.raises(config.ConfigError):
        config.load_system_prompt("v999")
