"""Retry helper for temporary AI-service failures (rate limits, timeouts, 503)."""
import logging
import time

from src.errors import is_transient

logger = logging.getLogger("orvyn")


def call_with_retry(func, attempts: int = 3, base_delay: float = 1.0, sleep=time.sleep):
    """Call func(). Retry transient errors with exponential backoff (1s, 2s, ...).

    Errors that are not transient (bad API key, unknown errors) are raised at once.
    """
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:
            if attempt == attempts or not is_transient(exc):
                raise
            delay = base_delay * 2 ** (attempt - 1)
            logger.warning("Transient error (%s). Retry %d of %d in %.1fs",
                           type(exc).__name__, attempt, attempts - 1, delay)
            sleep(delay)
