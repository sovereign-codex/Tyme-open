# Tyme Frontier — Governance Policy Spec (v0.1)

Purpose
-------
This document defines the policy engine schema, default rules, and operational practices that govern agentic activity in Tyme Frontier.
Policies are enforced by the Policy Engine, consulted by the Orchestrator, and recorded by the EpochRecorder.

Key Principles
--------------
* Default Deny: All effectful operations (files, shell, network, deployments, node activation) are denied by default.
* Least Privilege: Agents get the smallest scope needed; secrets are ephemeral.
* Human-in-loop: Any action classified "dangerous" requires explicit approval(s).
* Audit First: All agent intent, rationale, result, and approvals are logged immutably.

Policy Schema (YAML)
--------------------
# Example policy document format (policy name: "default")
# Top-level keys: allowlists, actions, approvals, node_rules, special_rules
name: default
version: 1
description: Default governance policy for Tyme-Open (Phase 0).

allowlists:
  # directories the agent may edit without explicit approval (low risk)
  writable_dirs:
    - "docs/"
    - "examples/"
    - "scripts/safe_tests/"
  # directories requiring explicit allowance (high risk)
  sensitive_dirs:
    - "infra/"
    - "deploy/"
    - "nodes/"
  # commands not allowed unless explicitly elevated
  forbidden_commands:
    - "curl"
    - "wget"
    - "ssh"
    - "nc"
    - "scp"
    - "rm -rf"
    - "sudo"

actions:
  # action classes and default gating
  apply_patch:
    description: "Apply a code patch to repo"
    gate: "human_review"    # human_review | auto | guardian_approval
    test_requirements:
      - "unit_tests"
      - "sast_scan"
      - "dependency_scan"
      - "secret_scan"
  run_shell:
    description: "Run arbitrary shell / command"
    gate: "sandbox_only"
    sandbox_policy: "no_network"
  deploy_node:
    description: "Deploy to Dot Node or field hardware"
    gate: "human_approval_multi"
    approvals_required: 2
    sim_required: true

approvals:
  human_approval_multi:
    min_signatures: 2
    required_roles:
      - "engineer"
      - "safety_officer"
  human_review:
    min_signatures: 1
    required_roles:
      - "engineer"
  guardian_approval:
    min_signatures: 1
    required_roles:
      - "guardian"

node_rules:
  # Dot Node rules (example)
  nodes:
    Luminara-01:
      allowed_actions: ["simulate", "stage_deploy"]
      deploy_requires: "human_approval_multi"
    Aetherwell-Test:
      allowed_actions: ["simulate"]
      deploy_requires: "human_approval_multi"

special_rules:
  prevent_secret_exfiltration: true
  log_all_responses: true
  ephemeral_secrets: true

Notes:
* Policies are loaded at Tyme start and can be modified via an approved PR.
* Policy engine returns structured decisions: {decision: allow|deny|require_approval, reason, rule_id}
