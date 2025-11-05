# Maintenance Tasks Proposal

## Typo Fix
- **Issue**: The AVOTs module heading in the scroll content uses the mixed-case label "Avots" instead of the branded uppercase "AVOTs", causing inconsistent presentation with the launch buttons.
- **Location**: `scrolls/avots.html`, line 1.
- **Proposed Task**: Update the heading text to "AVOTs" to match the casing used elsewhere in the UI (e.g., the AVOTs launcher button).

## Bug Fix
- **Issue**: The configuration points `scrollPath` to `public/scrolls`, but the project stores scroll HTML files under the top-level `scrolls/` directory, so any consumer of the config will read from the wrong location.
- **Location**: `config/tymeconfig.json`, line 4; actual scroll files reside in `scrolls/`.
- **Proposed Task**: Correct the configuration to reference the existing `scrolls/` directory so module loaders resolve the files properly.

## Documentation Discrepancy Fix
- **Issue**: The use-case documentation advertises "Real-time AVOT syncing to GitHub repos", yet the `sync_repo_to_avot` implementation is only a stub that prints a placeholder message.
- **Location**: `docs/1-USE_CASES.md`, line 5 and `src/avot_sync.py`, lines 1-3.
- **Proposed Task**: Either implement the advertised real-time sync or revise the documentation to clarify that the feature is not yet available.

## Test Improvement
- **Issue**: There are no automated tests covering the core `AVOTTyme.respond` interaction, leaving the CLI agent loop unverified.
- **Location**: `src/agents/avot_tyme.py`, lines 3-13 (no corresponding test module exists in the repository root).
- **Proposed Task**: Add a unit test that instantiates `AVOTTyme` and asserts its `respond` method returns the expected formatted string, ensuring regressions are caught.
