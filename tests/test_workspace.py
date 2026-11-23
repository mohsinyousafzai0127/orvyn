"""Tests for the approval gate and the sandboxed workspace tools (Sprint 2).

All file work happens in a temporary folder. No network, no API, no real approval prompt.
"""
import os

import pytest

from src import approval, config, tools, workspace


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    """Point the workspace at a temp folder and make sure no approver leaks between tests."""
    monkeypatch.setattr(workspace, "WORKSPACE_DIR", tmp_path / "workspace")
    approval.clear_approver()
    yield tmp_path / "workspace"
    approval.clear_approver()


def allow(_description):
    return True


def deny(_description):
    return False


# ---------- path sandbox ----------
@pytest.mark.parametrize("name", [
    "..\\..\\Windows\\win.ini",
    "../outside.txt",
    "notes/../../outside.txt",
    "C:/Windows/win.ini",
    "C:\\Windows\\win.ini",
    "/etc/passwd.txt",
    "~/secret.txt",
    "notes.txt:hidden",
    "",
    "   ",
    "con.txt",
    "script.py",
    "tool.exe",
    "noextension",
])
def test_unsafe_names_are_refused(name):
    with pytest.raises(workspace.WorkspaceError):
        workspace.resolve_in_workspace(name)


@pytest.mark.parametrize("name", ["todo.txt", "notes/today.md", "Report.JSON", "data.csv"])
def test_safe_names_resolve_inside_workspace(name, sandbox):
    path = workspace.resolve_in_workspace(name)
    assert sandbox.resolve() in path.parents


def test_symlink_escaping_the_workspace_is_refused(sandbox, tmp_path):
    sandbox.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("top secret", encoding="utf-8")
    try:
        os.symlink(outside, sandbox / "link", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this machine")
    assert workspace.read_workspace_file("link/secret.txt").startswith("ERROR:")


# ---------- writing and approval ----------
def test_approved_write_creates_the_file(sandbox):
    approval.set_approver(allow)
    result = workspace.write_workspace_file("todo.txt", "buy milk")
    assert result == "Saved 8 characters to workspace/todo.txt."
    assert (sandbox / "todo.txt").read_text(encoding="utf-8") == "buy milk"


def test_denied_write_changes_nothing(sandbox):
    approval.set_approver(deny)
    result = workspace.write_workspace_file("todo.txt", "buy milk")
    assert result.startswith("ERROR:") and "did not approve" in result
    assert not (sandbox / "todo.txt").exists()


def test_write_is_denied_when_no_approver_is_registered(sandbox):
    result = workspace.write_workspace_file("todo.txt", "buy milk")
    assert result.startswith("ERROR:")
    assert not (sandbox / "todo.txt").exists()


def test_failing_approver_means_denied(sandbox):
    def broken(_description):
        raise RuntimeError("terminal closed")

    approval.set_approver(broken)
    assert workspace.write_workspace_file("todo.txt", "x").startswith("ERROR:")
    assert not (sandbox / "todo.txt").exists()


def test_approver_is_told_what_will_happen(sandbox):
    seen = []
    approval.set_approver(lambda d: seen.append(d) or True)
    workspace.write_workspace_file("todo.txt", "buy milk")
    workspace.write_workspace_file("todo.txt", "buy bread")
    assert "create workspace/todo.txt" in seen[0] and "buy milk" in seen[0]
    assert "overwrite workspace/todo.txt" in seen[1]


def test_write_outside_workspace_never_asks_for_approval(sandbox):
    asked = []
    approval.set_approver(lambda d: asked.append(d) or True)
    result = workspace.write_workspace_file("../owned.txt", "hacked")
    assert result.startswith("ERROR:")
    assert asked == []


def test_too_long_text_is_refused_without_asking(sandbox):
    asked = []
    approval.set_approver(lambda d: asked.append(d) or True)
    result = workspace.write_workspace_file("big.txt", "x" * (workspace.MAX_FILE_CHARS + 1))
    assert result.startswith("ERROR:") and asked == []


def test_subfolders_are_created_on_approved_write(sandbox):
    approval.set_approver(allow)
    workspace.write_workspace_file("notes/today.md", "# Today")
    assert (sandbox / "notes" / "today.md").exists()


# ---------- reading and listing ----------
def test_read_returns_file_text(sandbox):
    approval.set_approver(allow)
    workspace.write_workspace_file("a.txt", "hello")
    assert workspace.read_workspace_file("a.txt") == "hello"


def test_read_missing_file_is_an_error(sandbox):
    assert workspace.read_workspace_file("nothing.txt").startswith("ERROR:")


def test_read_outside_workspace_is_refused(sandbox):
    assert workspace.read_workspace_file("C:/Windows/win.ini").startswith("ERROR:")
    assert workspace.read_workspace_file("../.env").startswith("ERROR:")


def test_read_empty_and_binary_files(sandbox):
    sandbox.mkdir(parents=True)
    (sandbox / "empty.txt").write_text("", encoding="utf-8")
    (sandbox / "bin.txt").write_bytes(b"\xff\xfe\x00\x80")
    assert "empty" in workspace.read_workspace_file("empty.txt")
    assert workspace.read_workspace_file("bin.txt").startswith("ERROR:")


def test_long_files_are_shortened(sandbox):
    sandbox.mkdir(parents=True)
    (sandbox / "long.txt").write_text("y" * (workspace.MAX_FILE_CHARS + 50), encoding="utf-8")
    result = workspace.read_workspace_file("long.txt")
    assert "Shortened" in result and len(result) < workspace.MAX_FILE_CHARS + 200


def test_list_when_workspace_is_missing_or_empty(sandbox):
    assert workspace.list_workspace() == "The workspace is empty."
    sandbox.mkdir(parents=True)
    assert workspace.list_workspace() == "The workspace is empty."


def test_list_shows_files_and_limits_long_listings(sandbox):
    sandbox.mkdir(parents=True)
    (sandbox / "b.txt").write_text("12345", encoding="utf-8")
    (sandbox / "a.txt").write_text("1", encoding="utf-8")
    listing = workspace.list_workspace()
    assert listing.index("a.txt (1 bytes)") < listing.index("b.txt (5 bytes)")
    for i in range(workspace.MAX_LISTED_FILES + 3):
        (sandbox / f"f{i:03}.txt").write_text("x", encoding="utf-8")
    assert "more files" in workspace.list_workspace()


# ---------- tools, allowlist and prompt ----------
def test_workspace_tools_are_exposed_to_the_agent():
    assert {t.name for t in workspace.WORKSPACE_TOOLS} == {"list_files", "read_file", "write_file"}
    assert {t.name for t in tools.TOOLS} == {"open_app", "get_weather", "list_files", "read_file", "write_file"}


def test_tool_wrappers_pass_results_through(sandbox):
    approval.set_approver(allow)
    assert workspace.write_file.invoke({"filename": "w.txt", "content": "hi"}).startswith("Saved")
    assert workspace.read_file.invoke({"filename": "w.txt"}) == "hi"
    assert "w.txt" in workspace.list_files.invoke({})


def test_prompt_v2_describes_the_workspace_tools_and_approval():
    text = config.load_system_prompt("v2").lower()
    for word in ("list_files", "read_file", "write_file", "approval", "workspace"):
        assert word in text
