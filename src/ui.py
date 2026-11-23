"""Console UI for Orvyn, built on the 'rich' library (Sprint 2).

Shows a banner, the live trace of every tool call, the answer in a panel, errors in red and
the approval question for file writes. Rich automatically switches to plain text when colours
are not available (for example if the output is redirected) and uses safe box characters in
old Windows consoles. Text coming from tools or files is shown as plain text, so it can never
change the layout.
"""
from contextlib import contextmanager
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.errors import MESSAGES

COMMANDS = {
    "/help": "help", "/tools": "tools", "/clear": "clear",
    "/exit": "exit", "exit": "exit", "quit": "exit",
}
MAX_RESULT_CHARS = 160
MAX_ARG_CHARS = 60
YES_WORDS = {"y", "yes"}


def parse_command(text: str) -> Optional[str]:
    """Return 'help', 'tools', 'clear', 'exit' or 'unknown' for commands, or None for normal text."""
    cleaned = (text or "").strip().lower()
    if cleaned in COMMANDS:
        return COMMANDS[cleaned]
    if cleaned.startswith("/"):
        return "unknown"
    return None


def short(text, limit: int = MAX_RESULT_CHARS) -> str:
    """Collapse whitespace and cut long text so one trace line stays on one line."""
    flat = " ".join(str(text).split())
    return flat if len(flat) <= limit else flat[: limit - 3] + "..."


def format_args(args: dict) -> str:
    """Format tool arguments like: location='Lahore', content='buy milk...'"""
    return ", ".join(f"{key}={short(repr(value), MAX_ARG_CHARS)}" for key, value in (args or {}).items())


class ConsoleUI:
    """All screen output and keyboard input of the command-line app."""

    def __init__(self, console: Optional[Console] = None, input_func=None):
        self.console = console or Console()
        self._input = input_func or self.console.input
        self._status = None
        self._step = 0

    # ----- static screens -----
    def banner(self, model: str, prompt_version: str, tools) -> None:
        body = Text()
        body.append("Orvyn", style="bold cyan")
        body.append("  AI assistant for Windows\n", style="cyan")
        body.append(f"Model: {model}   Prompt: {prompt_version}   Tools: {len(tools)}\n", style="dim")
        body.append("Type a request, or /help for commands.", style="dim")
        self.console.print(Panel(body, border_style="cyan"))

    def help(self) -> None:
        table = Table(show_header=True, header_style="bold", box=None)
        table.add_column("Command")
        table.add_column("What it does")
        table.add_row("/help", "show this list")
        table.add_row("/tools", "list the tools Orvyn can use")
        table.add_row("/clear", "forget the conversation and start fresh")
        table.add_row("/exit", "leave Orvyn (exit and quit also work)")
        self.console.print(table)

    def tools(self, tools) -> None:
        table = Table(show_header=True, header_style="bold", box=None)
        table.add_column("Tool")
        table.add_column("What it does")
        for tool in tools:
            table.add_row(tool.name, (tool.description or "").splitlines()[0])
        self.console.print(table)

    def info(self, message: str) -> None:
        self.console.print(Text(message, style="dim"))

    def error(self, message: str) -> None:
        self.console.print(Panel(Text(message), title="Problem", border_style="red"))

    # ----- conversation -----
    def prompt(self) -> str:
        self._step = 0
        return self._input("[bold green]You[/bold green] > ")

    @contextmanager
    def thinking(self):
        """Show a spinner while Orvyn works. The spinner is paused for approval questions."""
        # Braille dots need a UTF-8 console; fall back to a plain ASCII spinner otherwise.
        spinner = "dots" if "utf" in (self.console.encoding or "").lower() else "line"
        self._status = self.console.status("[cyan]Orvyn is thinking...[/cyan]", spinner=spinner)
        self._status.start()
        try:
            yield
        finally:
            self._status.stop()
            self._status = None

    def on_step(self, event: dict) -> None:
        """Print one line of the live trace for a tool call or a tool result."""
        if event["type"] == "tool_call":
            self._step += 1
            line = Text.assemble(
                (f"  Step {self._step}  ", "bold cyan"),
                (f"{event['name']}({format_args(event['args'])})", "cyan"),
            )
        else:
            content = event.get("content", "")
            failed = content.startswith("ERROR:")
            elapsed = event.get("elapsed")
            line = Text.assemble(
                ("    x " if failed else "    ok ", "bold red" if failed else "bold green"),
                (short(content), "red" if failed else "default"),
                (f"  ({elapsed:.1f}s)" if elapsed is not None else "", "dim"),
            )
        self.console.print(line)

    def show_answer(self, reply: str) -> None:
        if reply in MESSAGES.values():  # friendly error text from src/errors.py
            self.console.print(Panel(Text(reply), title="Problem", border_style="red"))
        else:
            self.console.print(Panel(Markdown(reply), title="Orvyn", border_style="green"))

    def summary(self, seconds: float, tool_names: list) -> None:
        count = len(tool_names)
        tools = f"{count} tool call{'s' if count != 1 else ''}" + (f": {', '.join(tool_names)}" if count else "")
        self.console.print(Text(f"{tools} | {seconds:.1f}s", style="dim"))

    # ----- approval -----
    def ask_approval(self, description: str) -> bool:
        """Ask the user to approve an action. Only y or yes counts as approval."""
        if self._status is not None:
            self._status.stop()
        try:
            self.console.print(Panel(Text(description), title="Approval needed", border_style="yellow"))
            answer = self._input("[bold yellow]Allow? \\[y/N][/bold yellow] ")
            return answer.strip().lower() in YES_WORDS
        finally:
            if self._status is not None:
                self._status.start()
