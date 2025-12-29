# Succession Protocol (Phase-10)

This protocol defines how stewardship is transferred or dissolved without creating
implicit authority. All actions are human-initiated, transparent, and auditable.

## Planned succession (voluntary handoff)
1. **Notice period:** The outgoing steward provides at least 30 days' notice.
2. **Overlap window:** Outgoing and incoming stewards overlap for at least one review cycle.
3. **Knowledge transfer:**
   - Review stewardship artifacts together.
   - Document historical context, open risks, and continuity concerns.
4. **Registry update:** Update `codex/stewardship/steward_registry.json` via PR with:
   - Updated roles, status, and term dates.
   - Clear notes about the transition.
5. **Public record:** Summarize the handoff in the PR description and release notes.

## Emergency succession
Emergency triggers include loss of access, prolonged inactivity, organizational failure,
incapacitation, or death.

1. **Activation:** A remaining steward or trusted human initiates a PR to nominate interim
   stewards and to document the emergency.
2. **Verification:** Provide evidence (e.g., inactivity duration, contact attempts) in PR notes.
3. **Interim assignment:** Assign temporary roles with explicit limits.
4. **Stabilization window:** Hold an emergency stewardship review within 30 days to confirm
   or revise interim appointments.
5. **Audit:** Document the emergency handoff and ensure continuity checklist completion.

## Revocation
Revocation is a protective mechanism, not a punitive one.

**Conditions:**
- Material breach of stewardship limits.
- Misrepresentation or hidden reassignment of authority.
- Sustained inaction that threatens continuity.

**Process:**
1. Any steward or trusted human may initiate a revocation PR with evidence.
2. Require at least two human reviewers not involved in the complaint.
3. Update the registry with `status: revoked` and record rationale in notes.

## Dissolution
If no stewards remain or continuity cannot be sustained:
1. Declare **archival mode** explicitly in the steward registry.
2. Freeze stewardship roles; no appointments occur until constitutional process restarts.
3. Preserve all artifacts and history; ensure read-only access.
4. Authority remains OFF indefinitely.

Archival mode is reversible only through the constitutional process.
