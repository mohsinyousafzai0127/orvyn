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


class Orvyn:
    """A conversation with Orvyn. Keeps history between questions."""

    def __init__(self, agent=None, retry_delay: float = 1.0):
        self.agent = agent if agent is not None else build_agent()
        self.retry_delay = retry_delay
        self.history = []
        self.last_tool_calls = []  # tool names used for the latest question

    def ask(self, user_input: str) -> str:
        """Send a message to Orvyn and return a safe, readable reply."""
        text = (user_input or "").strip()
        if not text:
            return "Please type a request for me."
        if len(text) > config.MAX_INPUT_CHARS:
            return f"That message is too long. Please keep it under {config.MAX_INPUT_CHARS} characters."

        self.last_tool_calls = []
        sent = self.history + [("user", text)]
        started = time.perf_counter()
        try:
            result = call_with_retry(
                lambda: self.agent.invoke({"messages": sent}),
                base_delay=self.retry_delay,
            )
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
