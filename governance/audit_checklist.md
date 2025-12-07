Phase 0 audit checklist (initial run)

1. Policy engine loaded
   - governance/policy-default.yaml present and parsed
   - default policy denies `infra/`, `deploy/`, `nodes/`

2. EpochRecorder extension
   - epoch-v{X}-agent-runs.json files are generated when agent runs occur

3. Sandbox runner
   - docker available and can run the sandbox script
   - network disabled by default
   - forbidden command tokens rejected

4. Project Graph
   - backend/project_graph.py executed for repo root
   - chronicle/project_graph.json produced

5. PR generation
   - pr_generator.py includes guardian_score and risk_score in PR body
   - PR payload contains agent lineage.

6. Red-team prompts
   - tests/test_prompt_injection.py has been executed; log suspicious responses and file a security ticket.

7. Secrets & Vault
   - No agent is allowed to access long-lived secrets
   - Environment secrets must be ephemeral via the vault (mock for Phase 0)
