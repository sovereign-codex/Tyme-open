"""
codex_patch_handler.py
----------------------

The orchestration layer connecting:

    • openai_client (LLM-driven patch synthesis)
    • git_helpers   (branching, writes, commits, pushes, PRs)
    • policy_engine (risk scoring, safety gates)
    • epoch logger  (optional future: run metadata logging)

This is the heart of Tyme's self-rewriting developer loop.
"""

from typing import List, Dict, Optional
from backend.openai_client import synthesize_patch
from backend.git_helpers import (
    create_branch_from,
    write_files_to_worktree,
    stage_and_commit,
    push_branch,
    create_draft_pr_via_gh,
)


# ------------------------------------------------------------
# Result object
# ------------------------------------------------------------

class CodexPatchResult:
    """Structured result returned from codex_patch()."""

    def __init__(
        self,
        ok: bool,
        branch: str,
        pr_url: Optional[str],
        files_changed: List[str],
        commit_message: str,
        policy_notes: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.ok = ok
        self.branch = branch
        self.pr_url = pr_url
        self.files_changed = files_changed
        self.commit_message = commit_message
        self.policy_notes = policy_notes
        self.error = error

    def to_dict(self):
        return {
            "ok": self.ok,
            "branch": self.branch,
            "pr_url": self.pr_url,
            "files_changed": self.files_changed,
            "commit_message": self.commit_message,
            "policy_notes": self.policy_notes,
            "error": self.error,
        }


# ------------------------------------------------------------
# Main orchestrator
# ------------------------------------------------------------

def codex_patch(
    branch: str,
    prompt: str,
    commit_message: str,
    policy_engine=None,
    base_branch: str = "main",
    cwd: str = ".",
) -> CodexPatchResult:
    """
    Orchestrates Tyme's autonomous patch cycle.

    Steps:
        1. Policy screening (optional)
        2. Generate LLM-based patch specification
        3. Create a branch
        4. Apply file changes
        5. Commit them
        6. Push branch
        7. Open draft PR
        8. Return structured result
    """

    # --------------------------------------------------------
    # Step 1: Policy pre-check (optional)
    # --------------------------------------------------------
    policy_notes = None
    if policy_engine:
        try:
            decision = policy_engine.evaluate(prompt)
            policy_notes = decision.notes
            if not decision.allowed:
                return CodexPatchResult(
                    ok=False,
                    branch=branch,
                    pr_url=None,
                    files_changed=[],
                    commit_message=commit_message,
                    policy_notes=policy_notes,
                    error="Policy engine rejected request.",
                )
        except Exception as e:
            return CodexPatchResult(
                ok=False,
                branch=branch,
                pr_url=None,
                files_changed=[],
                commit_message=commit_message,
                policy_notes="Policy engine failed.",
                error=str(e),
            )

    # --------------------------------------------------------
    # Step 2: LLM → patch synthesis
    # --------------------------------------------------------
    try:
        llm_output = synthesize_patch(prompt)
        file_changes: List[Dict[str, str]] = llm_output.get("files", [])
    except Exception as e:
        return CodexPatchResult(
            ok=False,
            branch=branch,
            pr_url=None,
            files_changed=[],
            commit_message=commit_message,
            policy_notes=policy_notes,
            error=f"LLM patch synthesis failed: {e}",
        )

    files_changed = [fc["path"] for fc in file_changes]

    if not file_changes:
        return CodexPatchResult(
            ok=False,
            branch=branch,
            pr_url=None,
            files_changed=[],
            commit_message=commit_message,
            policy_notes=policy_notes,
            error="LLM returned no file changes.",
        )

    # --------------------------------------------------------
    # Step 3: Create branch
    # --------------------------------------------------------
    try:
        create_branch_from(base_branch, branch, cwd=cwd)
    except Exception as e:
        return CodexPatchResult(
            ok=False,
            branch=branch,
            pr_url=None,
            files_changed=files_changed,
            commit_message=commit_message,
            policy_notes=policy_notes,
            error=f"Failed to create branch: {e}",
        )

    # --------------------------------------------------------
    # Step 4: Write files → worktree
    # --------------------------------------------------------
    try:
        write_files_to_worktree(file_changes, cwd=cwd)
    except Exception as e:
        return CodexPatchResult(
            ok=False,
            branch=branch,
            pr_url=None,
            files_changed=files_changed,
            commit_message=commit_message,
            policy_notes=policy_notes,
            error=f"Failed writing files: {e}",
        )

    # --------------------------------------------------------
    # Step 5: Commit
    # --------------------------------------------------------
    try:
        stage_and_commit(commit_message, cwd=cwd)
    except Exception as e:
        return CodexPatchResult(
            ok=False,
            branch=branch,
            pr_url=None,
            files_changed=files_changed,
            commit_message=commit_message,
            policy_notes=policy_notes,
            error=f"Git commit failed: {e}",
        )

    # --------------------------------------------------------
    # Step 6: Push
    # --------------------------------------------------------
    try:
        push_branch(branch, cwd=cwd)
    except Exception as e:
        return CodexPatchResult(
            ok=False,
            branch=branch,
            pr_url=None,
            files_changed=files_changed,
            commit_message=commit_message,
            policy_notes=policy_notes,
            error=f"Push failed: {e}",
        )

    # --------------------------------------------------------
    # Step 7: Create Draft PR
    # --------------------------------------------------------
    try:
        pr_url = create_draft_pr_via_gh(
            title=f"[Tyme Codex] {commit_message}",
            body=f"Automated patch generated via Tyme CMS.\n\nPrompt:\n{prompt}",
            head=branch,
            base="main",
            cwd=cwd,
        )
    except Exception as e:
        return CodexPatchResult(
            ok=False,
            branch=branch,
            pr_url=None,
            files_changed=files_changed,
            commit_message=commit_message,
            policy_notes=policy_notes,
            error=f"PR creation failed: {e}",
        )

    # --------------------------------------------------------
    # Success
    # --------------------------------------------------------
    return CodexPatchResult(
        ok=True,
        branch=branch,
        pr_url=pr_url,
        files_changed=files_changed,
        commit_message=commit_message,
        policy_notes=policy_notes,
        error=None,
    )
