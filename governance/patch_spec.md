Patch & Review Engine (v0.1)

Purpose:
 - Represent agent proposals as patch objects with metadata, risk score, and required approvals.

Patch Object Schema:
{
  "patch_id": "uuid",
  "agent_id": "avot.fabricator",
  "title": "Short title",
  "summary": "Longer human-readable summary",
  "diff": "...",                 # unified diff or path -> hunk list
  "files_changed": ["a/b.py", ...],
  "risk_score": 0.64,            # guardian computed
  "tests_run": {                 # results of auto-gates
      "unit_tests": {"status": "pass", "details": "..."},
      "sast_scan": {"status": "pass", "findings": []},
      "secret_scan": {"status": "pass", "findings": []}
  },
  "policy_decision": {
      "decision": "require_approval",
      "rule_id": "apply_patch"
  },
  "approvals": [
     {"role": "engineer", "username": "alex", "ts": "..." }
  ],
  "approved": false,
  "timestamp": "..."
}

Operations:
 - create_patch(patch): persists patch object + creates PR draft (offline)
 - run_auto_gates(patch_id): triggers tests and static analysis in sandbox
 - compute_risk(patch_id): calls Guardian heuristics
 - request_approval(patch_id, approval_spec)
 - apply_patch(patch_id): only if approved and gates passed. Application happens in ephemeral branch + PR created.

Audit:
 - All operations produce epoch entries (agent runs) with `diff_summary`, `risk_score`, and evidence paths.

UI:
 - Patch cards appear in Tyme Hall and VS Code plugin with Diff + Rationale + Tests + Approvals.
