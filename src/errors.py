"""Turn technical exceptions into friendly messages and log the details."""
import logging

from src.config import LOG_DIR

logger = logging.getLogger("orvyn")


def setup_logging() -> None:
    """Send technical details to logs/orvyn.log (never shown to the user)."""
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=LOG_DIR / "orvyn.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def friendly_error(exc: Exception) -> str:
    """Return a safe, understandable message for an exception."""
    text = f"{type(exc).__name__} {exc}".lower()
    if any(k in text for k in ("429", "quota", "rate limit", "resource_exhausted", "resourceexhausted")):
        return "Orvyn is being rate-limited by the AI service. Please wait a minute and try again."
    if any(k in text for k in ("api key", "api_key", "401", "403", "permission_denied", "unauthenticated")):
        return "The AI service rejected the API key. Please check GOOGLE_API_KEY in your .env file."
    if any(k in text for k in ("connect", "timeout", "timed out", "network", "getaddrinfo", "name resolution")):
        return "I couldn't connect to the AI service. Please check your internet connection and try again."
    if any(k in text for k in ("503", "unavailable", "overloaded")):
        return "The AI service is temporarily unavailable. Please try again shortly."
    return "Something went wrong while handling that request. Please try again."
