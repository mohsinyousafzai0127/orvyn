"""Produce real log lines for the resilience screenshot (no API key, no internet needed).

A test agent fails twice with a simulated 503 and then answers, after calling a tool, so
logs/orvyn.log gets 'Transient error ... Retry' lines and a 'Tool call' line.

Run from the project root:   python scripts/demo_retry_log.py
Caption the screenshot:      simulated 503 from a test agent (no real API call)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import AIMessage  # noqa: E402

from src.agent import Orvyn  # noqa: E402
from src.errors import setup_logging  # noqa: E402


class FlakyAgent:
    """Fails twice with a 503, then 'calls' the weather tool and answers."""

    def __init__(self):
        self.calls = 0

    def invoke(self, payload):
        self.calls += 1
        if self.calls <= 2:
            raise Exception("503 UNAVAILABLE (simulated)")
        tool_call = AIMessage(content="", tool_calls=[{"name": "get_weather", "args": {"location": "Lahore"}, "id": "demo-1"}])
        answer = AIMessage(content="Recovered after two simulated failures.")
        return {"messages": list(payload["messages"]) + [tool_call, answer]}


def main() -> None:
    setup_logging()
    orvyn = Orvyn(agent=FlakyAgent(), retry_delay=0.5)
    print("Orvyn:", orvyn.ask("What is the weather in Lahore?"))
    print("Now open logs/orvyn.log: it shows the retry lines and the tool call.")


if __name__ == "__main__":
    main()
