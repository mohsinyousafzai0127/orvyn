"""Configuration: environment variables, paths and prompt loading."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT_DIR / "prompts"
LOG_DIR = ROOT_DIR / "logs"

load_dotenv(ROOT_DIR / ".env")

DEFAULT_MODEL = "gemini-3.6-flash"
PROMPT_VERSION = "v1"
MAX_INPUT_CHARS = 2000


class ConfigError(Exception):
    """Raised when Orvyn is not configured correctly (e.g. missing API key)."""


def get_api_key() -> str:
    """Return the Google API key from the environment or raise ConfigError."""
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not key or key == "your-api-key-here":
        raise ConfigError(
            "No Google API key found. Copy .env.example to .env and set "
            "GOOGLE_API_KEY (free key: https://aistudio.google.com/apikey)."
        )
    return key


def get_model_name() -> str:
    """Return the Gemini model name (override with ORVYN_MODEL)."""
    return os.getenv("ORVYN_MODEL", DEFAULT_MODEL)


def load_system_prompt(version: str = PROMPT_VERSION) -> str:
    """Load a versioned system prompt from the prompts/ folder."""
    path = PROMPTS_DIR / f"system_{version}.md"
    if not path.exists():
        raise ConfigError(f"System prompt file not found: {path.name}")
    return path.read_text(encoding="utf-8")
