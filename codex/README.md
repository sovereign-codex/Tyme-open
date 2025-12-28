# Codex Contract

The Codex Contract is a formal specification for how contributors describe and evaluate work in this repository. It defines a shared format for decisions, artifacts, and review context so that people and tools can communicate consistently across files, services, and environments.

## Schemas

Schemas define the allowed structure of Codex artifacts. They ensure that reports, records, and references use predictable fields, types, and naming so data can be validated, compared, and aggregated without ambiguity.

## Codex Reports

Codex Reports are structured records that capture the output of work or evaluation. They summarize what was produced, the inputs used, and any relevant context for review or auditing. Reports are data artifacts; they are not directives.

## Tier-5: Directive Memory & Traceability (WARN-ONLY)

Tier-5 adds optional traceability metadata to directive artifacts. A `directive_id` is a UUID assigned to a directive at creation time so it can be referenced consistently across reports and payloads.

Chaining is modeled by linking to the immediate predecessor via `previous_directive_id`. A best-effort `chain_position` may be recorded to indicate ordering, but it is informational only and should not be treated as authoritative.

Tier-5 is WARN-ONLY: missing or inconsistent traceability data must not block workflows or change enforcement behavior. These fields are intended for auditing and context, not for validation gates or permission decisions.

## What Codex Does Not Control

Codex does not control execution, approvals, or governance decisions. It does not manage repository permissions, deploy pipelines, or merge behavior. It only defines how information is represented and recorded.
