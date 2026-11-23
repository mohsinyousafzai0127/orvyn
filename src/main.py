"""Command-line interface for Orvyn with a live agent trace. Run with: python -m src.main"""
import logging
import sys
import time

from src import approval, config
from src.agent import Orvyn
from src.config import ConfigError
from src.errors import friendly_error, setup_logging
from src.tools import TOOLS
from src.ui import ConsoleUI, parse_command


def _use_utf8() -> None:
    """Make sure symbols such as the degree sign print correctly in cmd.exe."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main() -> int:
    _use_utf8()
    setup_logging()
    ui = ConsoleUI()
    try:
        orvyn = Orvyn()
    except ConfigError as exc:
        ui.error(str(exc))
        return 1
    except Exception as exc:
        logging.getLogger("orvyn").exception("Startup failed")
        ui.error(friendly_error(exc))
        return 1

    approval.set_approver(ui.ask_approval)  # file writes always ask the user first
    ui.banner(config.get_model_name(), config.PROMPT_VERSION, TOOLS)

    while True:
        try:
            user_input = ui.prompt()
        except (EOFError, KeyboardInterrupt):
            ui.info("Goodbye!")
            return 0
        if not user_input.strip():
            continue

        command = parse_command(user_input)
        if command == "exit":
            ui.info("Goodbye!")
            return 0
        if command == "help":
            ui.help()
        elif command == "tools":
            ui.tools(TOOLS)
        elif command == "clear":
            orvyn.reset()
            ui.info("Conversation cleared.")
        elif command == "unknown":
            ui.info("Unknown command. Type /help to see the commands.")
        else:
            started = time.perf_counter()
            with ui.thinking():
                reply = orvyn.ask(user_input, on_step=ui.on_step)
            ui.show_answer(reply)
            ui.summary(time.perf_counter() - started, orvyn.last_tool_calls)


if __name__ == "__main__":
    sys.exit(main())
