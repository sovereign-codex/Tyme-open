"""
git_helpers.py
---------------

Low-level, auditable tools for Tyme's autonomous patching system.

This module provides controlled Git operations:
    • branch creation
    • file writes (with directory creation)
    • structured add/commit
    • authenticated push
    • draft PR creation via GitHub CLI

All shell execution is tightly wrapped and can later be routed
through Tyme’s governance, sandbox policy, or GitHub App tokens.
"""

import subprocess
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional


# ------------------------------------------------------------
#  Core shell executor
# ------------------------------------------------------------

def run_cmd(
    cmd: List[str],
    cwd: str = ".",
    check: bool = True,
    env: Optional[dict] = None
) -> subprocess.CompletedProcess:
    """
    Secure wrapper around subprocess.run.

    Arguments:
        cmd   - command list
        cwd   - working directory
        check - raise on non-zero exit code
        env   - optional environment override

    Returns subprocess.CompletedProcess
    """
    result = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env or os.environ.copy()
    )

    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    return result


# ------------------------------------------------------------
#  Branch creation
# ------------------------------------------------------------

def create_branch_from(base: str, branch: str, cwd: str = ".") -> None:
    """
    Creates a new branch from a base branch (usually "main").

    Steps:
        • fetch origin/<base>
        • checkout -b <branch> origin/<base>
    """
    run_cmd(["git", "fetch", "origin", base], cwd=cwd)
    run_cmd(["git", "checkout", "-b", branch, f"origin/{base}"], cwd=cwd)


# ------------------------------------------------------------
#  File writing helpers
# ------------------------------------------------------------

def write_files_to_worktree(files: List[Dict[str, str]], cwd: str = ".") -> None:
    """
    Writes file contents to working tree.

    files must be a list of dicts:
        { "path": "relative/path/to/file.py", "content": "full text" }

    Parent directories will be created automatically.
    """
    for file_spec in files:
        path = Path(cwd) / file_spec["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file_spec.get("content", ""), encoding="utf-8")


# ------------------------------------------------------------
#  Commit creation
# ------------------------------------------------------------

def stage_and_commit(
    commit_message: str,
    cwd: str = ".",
    author: Optional[Tuple[str, str]] = None
) -> subprocess.CompletedProcess:
    """
    Adds all changes and creates a commit.

    If author=(name, email) is provided, sets:
        GIT_AUTHOR_NAME
        GIT_AUTHOR_EMAIL
        GIT_COMMITTER_NAME
        GIT_COMMITTER_EMAIL
    """
    run_cmd(["git", "add", "-A"], cwd=cwd)

    env = os.environ.copy()
    if author:
        env["GIT_AUTHOR_NAME"] = author[0]
        env["GIT_AUTHOR_EMAIL"] = author[1]
        env["GIT_COMMITTER_NAME"] = author[0]
        env["GIT_COMMITTER_EMAIL"] = author[1]

    result = subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )

    # If git reports "nothing to commit", don't error.
    if result.returncode != 0:
        if "nothing to commit" in result.stderr.lower():
            return result
        raise RuntimeError(
            f"git commit failed:\n{result.stderr}"
        )

    return result


# ------------------------------------------------------------
#  Push helpers
# ------------------------------------------------------------

def push_branch(branch: str, cwd: str = ".") -> None:
    """
    Pushes the current branch to origin with upstream tracking.
    """
    run_cmd(["git", "push", "-u", "origin", branch], cwd=cwd)


# ------------------------------------------------------------
#  PR creation helpers via GH CLI
# ------------------------------------------------------------

def create_draft_pr_via_gh(
    title: str,
    body: str,
    head: str,
    base: str = "main",
    cwd: str = "."
) -> str:
    """
    Creates a draft PR using GitHub CLI:

        gh pr create --draft --title <title> --body <body> \
                     --base <base> --head <head>

    Returns:
        PR URL (string)
    """
    # Create the PR
    run_cmd([
        "gh", "pr", "create",
        "--title", title,
        "--body", body,
        "--base", base,
        "--head", head,
        "--draft"
    ], cwd=cwd)

    # Retrieve PR URL
    result = run_cmd([
        "gh", "pr", "view",
        "--json", "url",
        "--jq", ".url"
    ], cwd=cwd)

    return result.stdout.strip()


# ------------------------------------------------------------
#  END OF MODULE
# ------------------------------------------------------------
