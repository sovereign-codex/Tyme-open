Purpose
-------
Extend `backend/epoch.py` EpochRecorder to record agent-run context, rationale, LLM metadata, and approvals.

New fields to be recorded per epoch entry (recommended additions):
- agent_runs: list of {
    agent_id: str,
    prompt_hash: str,           # SHA256 of prompt for deduping/audit
    prompt_summary: str,        # short summary of the prompt
    llm_provider: str,          # e.g., openai/gpt-4o/claude/quill
    llm_model: str,
    rationale: str,             # LLM-produced rationale, summarized
    diff_summary: str,          # short summary of code diffs proposed/applied
    risk_score: float,          # 0.0 - 1.0 computed by guardian heuristics
    evidence: [                 # list of supporting artifacts (paths/URIs)
      { type: "test_result", path: "chronicle/tests/..." },
      { type: "static_analysis", path: "chronicle/sast/..." }
    ],
    approvals: [
      { role: "engineer", username: "alex", ts: "..." },
      { role: "guardian", username: "tyme-guardian", ts: "..." }
    ],
    approved: boolean
}

Integration
-----------
1. `EpochRecorder.write_epoch(data: Dict)` should accept these fields in `data` and persist them in the epoch file and master log.
2. Add small helper function `record_agent_run(epoch_path, agent_run)` to write agent runs to a structured JSON or YAML sidecar (e.g., `chronicle/epochs/epoch-v{version}-agent-runs.json`).
3. Make the EpochRecorder output machine-readable (JSON) in addition to Markdown to support UI ingestion (phase panels).

Security
--------
* Agent rationale may contain sensitive tokens / references; ensure epoch artifacts are sanitized: mask secrets (use vault references) and store hashes only when necessary.

Suggested patch
----------------
Append the following fields and writing logic to `EpochRecorder.write_epoch`:
- When building `entry`, add:
  - "### Agent Runs" section and list the entries, and also persist `agent_runs.json` alongside `epoch-v{version}.md`.

This change ties every agent action back into an immutable epoch chronicle.
