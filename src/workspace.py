"""Sandboxed workspace tools: list, read and write notes inside ONE folder (Sprint 2).

Safety rules:
  - Every path is resolved and must stay inside WORKSPACE_DIR. Names with '..', absolute
    paths, drive letters, '~' and ':' are refused, and so are symlinks that point outside.
  - Only small text files are allowed (.txt, .md, .csv, .json).
  - Every write needs the user's approval (src/approval.py). No approver means no write.
  - Tools never raise: on failure they return text starting with 'ERROR:' so Orvyn can
    report the failure honestly.
"""
import logging
from pathlib import Path

from langchain_core.tools import tool

from src import approval
from src.config import ROOT_DIR

logger = logging.getLogger("orvyn")

WORKSPACE_DIR = ROOT_DIR / "workspace"
ALLOWED_SUFFIXES = {".txt", ".md", ".csv", ".json"}
MAX_FILE_CHARS = 20_000
MAX_LISTED_FILES = 50
PREVIEW_CHARS = 200
RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}


class WorkspaceError(Exception):
    """A request that is not allowed inside the workspace sandbox."""


def resolve_in_workspace(filename: str) -> Path:
    """Return the absolute path for a workspace file name, or raise WorkspaceError."""
    name = (filename or "").strip().replace("\\", "/")
    if not name:
        raise WorkspaceError("No file name was provided.")
    if name.startswith(("/", "~")) or ":" in name:
        raise WorkspaceError("Only files inside the workspace folder are allowed.")
    if ".." in name.split("/"):
        raise WorkspaceError("Only files inside the workspace folder are allowed.")
    try:
        root = WORKSPACE_DIR.resolve()
        target = (root / name).resolve()
    except (OSError, ValueError):
        raise WorkspaceError("That file name is not valid.")
    if root not in target.parents:
        raise WorkspaceError("Only files inside the workspace folder are allowed.")
    if target.suffix.lower() not in ALLOWED_SUFFIXES:
        raise WorkspaceError("Only .txt, .md, .csv and .json files are allowed.")
    if target.stem.upper() in RESERVED_NAMES:
        raise WorkspaceError("That file name is reserved by Windows.")
    return target


def _relative(path: Path) -> str:
    return path.relative_to(WORKSPACE_DIR.resolve()).as_posix()


def list_workspace() -> str:
    """List the files in the workspace folder."""
    root = WORKSPACE_DIR.resolve()
    if not root.is_dir():
        return "The workspace is empty."
    files = sorted(p for p in root.rglob("*") if p.is_file())
    if not files:
        return "The workspace is empty."
    lines = [f"{_relative(p)} ({p.stat().st_size} bytes)" for p in files[:MAX_LISTED_FILES]]
    extra = len(files) - MAX_LISTED_FILES
    if extra > 0:
        lines.append(f"... and {extra} more files")
    return "Files in the workspace: " + "; ".join(lines)


def read_workspace_file(filename: str) -> str:
    """Read a text file from the workspace folder."""
    try:
        path = resolve_in_workspace(filename)
    except WorkspaceError as exc:
        return f"ERROR: {exc}"
    if not path.is_file():
        return f"ERROR: There is no file called '{filename.strip()}' in the workspace."
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "ERROR: That file is not a readable text file."
    except OSError as exc:
        return f"ERROR: Could not read the file ({type(exc).__name__})."
    if not text.strip():
        return f"{_relative(path)} is empty."
    if len(text) > MAX_FILE_CHARS:
        return text[:MAX_FILE_CHARS] + f"\n[Shortened: only the first {MAX_FILE_CHARS} characters are shown.]"
    return text


def write_workspace_file(filename: str, content: str) -> str:
    """Write a text file in the workspace folder, but only if the user approves."""
    try:
        path = resolve_in_workspace(filename)
    except WorkspaceError as exc:
        return f"ERROR: {exc}"
    content = content or ""
    if len(content) > MAX_FILE_CHARS:
        return f"ERROR: The text is too long (limit {MAX_FILE_CHARS} characters). Nothing was saved."

    action = "overwrite" if path.exists() else "create"
    preview = content[:PREVIEW_CHARS] + ("..." if len(content) > PREVIEW_CHARS else "")
    description = (f"Orvyn wants to {action} workspace/{_relative(path)} "
                   f"({len(content)} characters).\nPreview: {preview}")
    if not approval.request_approval(description):
        return "ERROR: The user did not approve the write, so nothing was saved."

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        return f"ERROR: Could not save the file ({type(exc).__name__})."
    logger.info("Workspace file written: %s", path.name)
    return f"Saved {len(content)} characters to workspace/{_relative(path)}."


@tool
def list_files() -> str:
    """List the notes and files in the Orvyn workspace folder."""
    return list_workspace()


@tool
def read_file(filename: str) -> str:
    """Read a text file from the workspace folder, for example 'weather.txt'."""
    return read_workspace_file(filename)


@tool
def write_file(filename: str, content: str) -> str:
    """Save text to a file in the workspace folder, for example 'weather.txt'. The user must approve every write."""
    return write_workspace_file(filename, content)


WORKSPACE_TOOLS = [list_files, read_file, write_file]
