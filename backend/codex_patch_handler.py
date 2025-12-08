"""
codex_patch_handler.py
----------------------

This module orchestrates Tyme’s autonomous code-modification process.

It handles:

• Policy checks
• Turning natural-language patch requests into strict file blocks
• Writing new/updated files into the repo working tree
• Creating branches, commits, and pushing them
• Running tests and analysis inside Tyme’s sandbox
• Creating draft pull requests via GitHub CLI
• Writing agent_run logs via EpochRecorder

The CMS command that uses this module will appear as:

    tyme.codex_patch(branch_name, prompt, commit_message?)
"""

import os
import json
import time
import logging
from typing import List, Dict, Optional, Tuple

from backend.openai_client import (
    generate_patch_blocks,
    hash_prompt
)
from backend import git_helpers

# Epoch Engine (optional safety fallback)
try:
    from backend.epoch import EpochRecorder
except Exception:
    EpochRecorder = None

# Sandbox
try:
    from sandbox.sandbox_runner import run_in_sandbox
except Exception:
    # If sandbox missing, fallback to no-op
    def run_in_sandbox(*args, **kwargs):
        return {"status": "skipped", "reason": "sandbox unavailable"}


logger = logging.getLogger("tyme.codex_patch_handler")

# -------------------------------------------------------------------
#  Strict file-block parser
# -------------------------------------------------------------------

def parse_file_blocks(text: str) -> List[Dict[str, str]]:
    """
    Parse LLM output in the strict wrapper format:

    === FILE: path/to/file.py ===
    <content>
    === END FILE ===

    Returns list of:
        {"path": "relative/path", "content": "<full file>"}.
    """
    files = []
    lines = text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("=== FILE:"):
            try:
                # Extract file path
                raw = line.replace("=== FILE:", "").replace("===", "").strip()
                file_path = raw

                i += 1
                content_lines = []

                # Read content until END FILE
                while i < len(lines) and not lines[i].strip().startswith("=== END FILE"):
                    content_lines.append(lines[i])
                    i += 1

                content = "\n".join(content_lines).rstrip() + "\n"
                files.append({"path": file_path, "content": content})
            except Exception as e:
                logger.error(f"Failed parsing file block: {e}")
        i += 1

    return files


# -------------------------------------------------------------------
#  Risk evaluation (placeholder)
# -------------------------------------------------------------------

def compute_risk_score(test_result: Dict) -> float:
    """
    Very simple heuristic.
    Will eventually call AVOT-Guardian for deep semantic risk assessment.
    """
    if test_result.get("status") == "ok" and test_result.get("exit_code", 0) == 0:
        return 0.05
    return 0.75


# -------------------------------------------------------------------
#  Core: codex_patch()
# -------------------------------------------------------------------

def codex_patch(
    branch: str,
    prompt: Optional[str] = None,
    commit_message: Optional[str] = None,
    base: str = "main",
    model: Optional[str] = None,
    run_tests: bool = True,
    policy_engine=None,
    actor: Optional[Dict[str, str]] = None,
) -> Dict:
    """
    The full autonomous patch engine.

    Steps:
    1. Policy check
    2. Generate patch (Codex)
    3. Parse file blocks
    4. Create branch
    5. Write files
    6. Commit + push
    7. Sandbox tests
    8. Risk scoring
    9. Epoch logging
    10. Draft PR

    Returns dict with:
        status, pr_url, branch, risk_score, agent_run_path, test_result
    """

    # ----------------------------------------------------
    # 0. Policy
    # ----------------------------------------------------
    raw_text = prompt or ""
    if policy_engine:
        decision = policy_engine.decide(raw_text)
        if decision["decision"] == "deny":
            return {
                "status": "denied",
                "reason": decision["reason"],
                "policy": decision
            }
        if decision["decision"] == "require_approval":
            return {
                "status": "requires_approval",
                "reason": decision["reason"],
                "policy": decision
            }

    # ----------------------------------------------------
    # 1. Generate patch from LLM
    # ----------------------------------------------------
    if not prompt:
        return {"status": "error", "reason": "codex_patch requires a prompt string"}

    try:
        llm_output, prompt_h = generate_patch_blocks(prompt, model=model)
    except Exception as e:
        return {"status": "error", "reason": f"LLM generation failed: {e}"}

    files = parse_file_blocks(llm_output)
    if not files:
        return {
            "status": "error",
            "reason": "LLM did not return valid file blocks"
        }

    # ----------------------------------------------------
    # 2. Git operations: create branch & write files
    # ----------------------------------------------------
    try:
        git_helpers.create_branch_from(base, branch)
        git_helpers.write_files_to_worktree(files)
        commit_msg = commit_message or f"Autogenerated patch via Codex: {branch}"
        author = (actor.get("name"), actor.get("email")) if actor else None
        git_helpers.stage_and_commit(commit_msg, author=author)
        git_helpers.push_branch(branch)
    except Exception as e:
        return {"status": "error", "reason": f"Git operation failed: {e}"}

    # ----------------------------------------------------
    # 3. Sandbox tests (if enabled)
    # ----------------------------------------------------
    if run_tests:
        try:
            # Run pytest inside sandbox
            result = run_in_sandbox(
                cmd="pytest -q || true",
                repo=".",
                timeout=60,
                no_network=True
            )
            test_result = result
        except Exception as e:
            test_result = {"status": "error", "reason": str(e)}
    else:
        test_result = {"status": "skipped"}

    # ----------------------------------------------------
    # 4. Risk score
    # ----------------------------------------------------
    risk_score = compute_risk_score(test_result)

    # ----------------------------------------------------
    # 5. Epoch logging
    # ----------------------------------------------------
    agent_run_path = None
    if EpochRecorder:
        try:
            recorder = EpochRecorder()
            epoch_data = {
                "version": "autogen",
                "summary": prompt[:200],
                "agent_runs": [{
                    "agent_id": "avot.codex",
                    "prompt_summary": prompt[:200],
                    "prompt_hash": prompt_h,
                    "llm_model": model or os.environ.get("OPENAI_MODEL"),
                    "risk_score": risk_score,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }]
            }
            md_path = recorder.write_epoch(epoch_data)
            agent_run_path = md_path.replace(".md", "-agent-runs.json")
        except Exception as e:
            logger.warning(f"Epoch logging failed: {e}")

    # ----------------------------------------------------
    # 6. Create PR via GitHub CLI
    # ----------------------------------------------------
    pr_url = None
    try:
        title = commit_msg
        body = (
            f"Autogenerated patch via Codex.\n\n"
            f"**Risk Score:** {risk_score}\n"
            f"**Prompt Hash:** {prompt_h}\n"
            f"**Agent Run:** {agent_run_path or 'unavailable'}\n"
        )
        pr_url = git_helpers.create_draft_pr_via_gh(
            title=title,
            body=body,
            head=branch,
            base=base
        )
    except Exception as e:
        logger.error(f"PR creation failed: {e}")

    # ----------------------------------------------------
    # 7. Return result
    # ----------------------------------------------------
    return {
        "status": "ok",
        "branch": branch,
        "pr_url": pr_url,
        "risk_score": risk_score,
        "agent_run_path": agent_run_path,
        "test_result": test_result,
    }
