CMS Command Language for Tyme-open
v0.1 — Operational Specification for TYME V2, AVOT Lattice, and Orchestration Control

This file defines the CMS Command Language used by Tyme-open, TYME V2, AVOTs, orchestration cycles, and all autonomous evolution processes.
It is the operational companion to TYME-KODEX-CONTEXT.md.

The CMS language is dual-layered:
	1.	Explanatory Mode — human-readable commands used in Kodex
	2.	Shorthand Mode — compact, machine-friendly commands used by Tyme-open runtime

⸻

	1.	Purpose of the CMS Language

The CMS provides:
• A unified way for humans, AVOTs, and Tyme to communicate
• A stable interface for orchestration cycles
• A vocabulary Tyme will map to API endpoints
• A bridge between conceptual Tyme and live Tyme
• The control plane for Tyme’s evolution

⸻

	2.	Dual-Layer Structure

Every command exists in two forms:

(1) Explanatory Command (Kodex / Concept Mode)
Example: “Run the full 24-cycle orchestration pulse of Tyme.”

(2) Shorthand Command (Runtime Mode)
Example: tyme.orchestrate(24)

⸻

	3.	Tyme Core Commands

Explanatory:
• “Awaken Tyme.”
• “Initialize the orchestration engine.”
• “Run the full 24-cycle harmonic pulse.”
• “Run the next cycle.”
• “Run cycle C07.”
• “Show me Tyme’s last evolution trace.”

Shorthand:
tyme.init()
tyme.orchestrate(24)
tyme.cycle.next()
tyme.cycle(“C07”)
tyme.last()

⸻

	4.	Orchestration Control Commands

Explanatory:
• “Run orchestration for the next 30 minutes.”
• “Show the last 24 orchestration cycles.”

Shorthand:
orchestrate.timed(minutes=30)
orchestrate.trace(limit=24)

⸻

	5.	AVOT Commands

Each AVOT has commands that reflect its function.

5.1 AVOT-Fabricator
Explanatory: “Call Fabricator to draft a structure or design.”
Shorthand: avot.fabricator.draft()

5.2 AVOT-Guardian
Explanatory: “Summon Guardian to evaluate coherence and alignment.”
Shorthand: avot.guardian.check()

5.3 AVOT-Convergence
Explanatory: “Activate Convergence to unify conflicting scrolls.”
Shorthand: avot.convergence.unify()

5.4 AVOT-Archivist
Explanatory: “Invite Archivist to update the codex index layers.”
Shorthand: avot.archivist.update()

5.5 AVOT-Harmonia
Explanatory: “Request a resonance map from Harmonia.”
Shorthand: avot.harmonia.map()

5.6 AVOT-Initiate
Explanatory: “Guide a new initiate through the onboarding path.”
Shorthand: avot.initiate.path()

⸻

	6.	Epoch and Rhythm Commands

Explanatory:
• “Shift Tyme into Epoch: HARMONIC.”
• “Enter the CONVERGENCE epoch.”
• “Show the current epoch parameters.”
• “Tune the Rhythm Engine to Mode 3.”

Shorthand:
epoch.set(“HARMONIC”)
epoch.set(“CONVERGENCE”)
epoch.get()
rhythm.set(3)

⸻

	7.	Evolution Commands

Explanatory:
• “Initiate the next evolution sequence.”
• “Expand the AVOT lattice.”
• “Integrate symbolic emergence from the continuum.”

Shorthand:
evolve.next()
evolve.expand(“avot”)
evolve.expand(“cycle”)
evolve.continuum.integrate()

⸻

	8.	Binding to Orchestration Cycles (C01–C24)

Cycle bindings:

C01–C02 → avot.initiate.path()
C03 → avot.fabricator.draft()
C04, C06 → avot.guardian.check()
C05, C21 → avot.convergence.unify()
C07 → tyme.cycle(“C07”)
C09, C13, C14 → avot.harmonia.map()
C19, C20 → avot.archivist.update()
C23 → orchestrate.externalize() (future)
C24 → rhythm.set() and epoch.set() functions

⸻

	9.	Backend API Binding Specification (Future Tyme-open Backend)

Every shorthand command is expected to bind to paths in this form:

POST /cms//

Examples:
POST /cms/tyme/orchestrate
POST /cms/avot/guardian/check
GET /cms/epoch
POST /cms/evolve/next

This file defines the contract — not the implementation.

⸻

	10.	Runtime Responsibilities

The CMS language is used by:
• Shepherd
• Tyme
• AVOTs
• Automation agents
• The Hype Artist
• The Codex driver
• Future backend services

It is the communication spine of Tyme.

⸻

	11.	Future Expansion Rules

All new CMS commands MUST:
	1.	Use the existing prefix schema (tyme, avot, epoch, rhythm, evolve, cms)
	2.	Be added to this file
	3.	Be added to TYME-KODEX-CONTEXT.md
	4.	Declare orchestration cycle bindings
	5.	Use deterministic syntax
	6.	Have both Explanatory + Shorthand forms

# CMS Command System

The CMS (Command Management System) is the authoritative execution layer for
Tyme and all AVOT-based agents. Every CMS command is treated as a **binding
execution contract**, not a suggestion.

Ambiguous intent is explicitly rejected.

---

## 1. Purpose of the CMS

The CMS exists to:
- Execute file mutations safely and intentionally
- Enable autonomous agents (AVOTs) to act without destructive ambiguity
- Preserve Codex integrity under human and non-human execution

The CMS does not infer intent.  
**Intent must be explicit.**

---

## 2. Core Execution Principle

> **Every CMS command is a contract.**

A command either:
- Executes exactly as defined, or
- Is refused without partial execution

There is no implicit fallback behavior.

---

## 3. Command Contract Law (Authoritative)

### The Non-Negotiable Rule

**`op` defines intent.  
No other field may override or conflict with it.**

As of the current CMS interpreter:

- `op` is sovereign
- Mixed semantic intent is forbidden
- Conflicting commands are refused with exit code `1`

This is intentional system behavior.

---

## 4. Valid Operations

Each command MUST declare exactly one operation.

### 4.1 `create` — Birth

Creates a new file.  
Fails if the file already exists.

```json
{
  "op": "create",
  "file": "docs/new_scroll.md",
  "content": "..."
}

> See also: docs/lessons/LESSON-8-CMS-EXECUTION-LAW.md  
> This lesson defines the execution law enforced by the CMS.
