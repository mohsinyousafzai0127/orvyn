"""Orvyn agent: Gemini model + versioned system prompt + allowlisted tools."""
import logging
import time

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from src import config
from src.errors import friendly_error
from src.resilience import call_with_retry
from src.tools import TOOLS

logger = logging.getLogger("orvyn")


def build_agent():
    """Create the LangChain agent. Raises ConfigError if the API key is missing."""
    model = ChatGoogleGenerativeAI(
        model=config.get_model_name(),
        google_api_key=config.get_api_key(),
    )
    return create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=config.load_system_prompt(),
    )


def message_to_text(content) -> str:
    """Gemini may return a plain string or a list of content blocks."""
    if isinstance(content, str):
        return content.strip()
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts).strip()


def extract_tool_names(messages) -> list:
    """Return the names of tools called in these messages and log each call."""
    names = []
    for message in messages:
        for call in getattr(message, "tool_calls", None) or []:
            names.append(call["name"])
            logger.info("Tool call: %s args=%s", call["name"], call.get("args"))
    return names


def emit_step_events(message, on_step, started) -> None:
    """Turn one new message into trace events for the console: tool_call and tool_result.

    `started` remembers when each tool call was announced so the result can show a duration
    (for write_file this includes the time you spend answering the approval question).
    """
    for call in getattr(message, "tool_calls", None) or []:
        started[call.get("id")] = time.perf_counter()
        on_step({"type": "tool_call", "name": call["name"], "args": call.get("args") or {}})
    if getattr(message, "type", "") == "tool":
        began = started.pop(getattr(message, "tool_call_id", None), None)
        on_step({
            "type": "tool_result",
            "name": getattr(message, "name", None) or "tool",
            "content": message_to_text(message.content),
            "elapsed": (time.perf_counter() - began) if began is not None else None,
        })


class Orvyn:
    """A conversation with Orvyn. Keeps history between questions."""

    def __init__(self, agent=None, retry_delay: float = 1.0):
        self.agent = agent if agent is not None else build_agent()
        self.retry_delay = retry_delay
        self.history = []
        self.last_tool_calls = []  # tool names used for the latest question

    def reset(self) -> None:
        """Forget the conversation (used by the /clear command)."""
        self.history = []
        self.last_tool_calls = []

    def _run_streaming(self, sent, on_step):
        """Run the agent step by step and report each tool call and result to on_step.

        If a temporary error forces a retry, steps shown before the failure may appear again.
        """
        final = None
        seen = len(sent)  # everything after the messages we sent in is new
        started = {}
        for chunk in self.agent.stream({"messages": sent}, stream_mode="values"):
            final = chunk
            messages = chunk["messages"]
            for message in messages[seen:]:
                emit_step_events(message, on_step, started)
            seen = max(seen, len(messages))
        if final is None:
            raise RuntimeError("The agent returned nothing.")
        return final

    def ask(self, user_input: str, on_step=None) -> str:
        """Send a message to Orvyn and return a safe, readable reply.

        If on_step is given, it is called with a dict for every tool call and tool result
        while Orvyn works (the live trace in the console).
        """
        text = (user_input or "").strip()
        if not text:
            return "Please type a request for me."
        if len(text) > config.MAX_INPUT_CHARS:
            return f"That message is too long. Please keep it under {config.MAX_INPUT_CHARS} characters."

        self.last_tool_calls = []
        sent = self.history + [("user", text)]
        started = time.perf_counter()
        try:
            if on_step is None:
                run = lambda: self.agent.invoke({"messages": sent})  # noqa: E731
            else:
                run = lambda: self._run_streaming(sent, on_step)  # noqa: E731
            result = call_with_retry(run, base_delay=self.retry_delay)
            messages = result["messages"]
            reply = message_to_text(messages[-1].content)
        except Exception as exc:  # never crash the app; log details, show a friendly message
            logger.exception("Agent call failed")
            return friendly_error(exc)

        self.last_tool_calls = extract_tool_names(messages[len(sent):])
        logger.info("Reply in %.2fs; tools used: %s",
                    time.perf_counter() - started, self.last_tool_calls or "none")
        self.history = messages
        return reply or "I couldn't produce a response. Please try rephrasing."
