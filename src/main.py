"""Command-line interface for Orvyn. Run with: python -m src.main"""
import logging
import sys

from src.agent import Orvyn
from src.config import ConfigError
from src.errors import friendly_error, setup_logging

EXIT_WORDS = {"exit", "quit"}


def main() -> int:
    setup_logging()
    try:
        orvyn = Orvyn()
    except ConfigError as exc:
        print(f"Orvyn: {exc}")
        return 1
    except Exception as exc:
        logging.getLogger("orvyn").exception("Startup failed")
        print(f"Orvyn: {friendly_error(exc)}")
        return 1

    print("Orvyn is ready. Type 'exit' to quit.")
    while True:
        try:
            user_input = input("\nYou: ")
        except (EOFError, KeyboardInterrupt):
            print("\nOrvyn: Goodbye!")
            return 0
        if user_input.strip().lower() in EXIT_WORDS:
            print("Orvyn: Goodbye!")
            return 0
        print(f"Orvyn: {orvyn.ask(user_input)}")


if __name__ == "__main__":
    sys.exit(main())
