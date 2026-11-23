"""Human approval gate for actions that change something (Sprint 2, workspace tools).

A tool that wants to change a file calls request_approval(description). The console UI
registers an approver that shows the description and asks the user. Safety rules:
  - If no approver is registered (unit tests, the evaluation runner), the answer is NO.
  - If the approver raises an error, the answer is NO.
  - Prompts are asked one at a time, even if the model asks for two writes at once.
"""
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger("orvyn")

Approver = Callable[[str], bool]

_approver: Optional[Approver] = None
_lock = threading.Lock()


def set_approver(func: Optional[Approver]) -> None:
    """Register the function that asks the user (or None to remove it)."""
    global _approver
    _approver = func


def clear_approver() -> None:
    """Remove the registered approver, so every request is denied."""
    set_approver(None)


def request_approval(description: str) -> bool:
    """Ask for permission to do something. Returns True only if the user clearly said yes."""
    with _lock:
        if _approver is None:
            logger.info("Approval denied by default (no approver registered): %s", description)
            return False
        try:
            allowed = bool(_approver(description))
        except Exception:  # an approver that fails must never allow the action
            logger.exception("Approver failed; treating as denied")
            return False
    logger.info("Approval %s: %s", "granted" if allowed else "denied", description)
    return allowed
