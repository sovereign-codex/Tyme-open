from __future__ import annotations

import time
from typing import Dict, Any

from avot_core.engine import AvotEngine
from avot_core.models import AvotTask

from backend.github_api import GitHubAPI as GitHubClient
from backend.drift_monitor import DriftMonitor
from backend.rhythm import RhythmEngine
from backend.epochs import EpochEngine


class AutonomousEvolution:
    """
    AutonomousEvolution v0.1

    This module performs the FULL predictive->fabricate->validate->archive->PR->merge cycle.

    Triggered by:
        - manual endpoint: /autonomous/run
        - timed loop (optional)
    """

    def run_cycle(self) -> Dict[str, Any]:
        engine = AvotEngine()

        # ------------------------------------------------------------
        # 1. Multi-agent prediction
        # ------------------------------------------------------------
        # Load epoch parameters
        epoch_params = EpochEngine().get_epoch()
        weights = epoch_params["parameters"]["predictor_weights"]
        agents = [
            ("AVOT-predictor-minimal", weights.get("minimal", 0)),
            ("AVOT-predictor-deep", weights.get("deep", 0)),
            ("AVOT-predictor-semantic", weights.get("semantic", 0)),
        ]

        candidates = []
        for agent, weight in agents:
            if weight <= 0:
                continue
            # repeat predictor roughly proportional to weight
            repeat = max(1, int(weight * 3))
            for _ in range(repeat):
                pred_task = engine.create_task(
                    name="predict-next-architecture",
                    payload={"base_spec": {}},
                    created_by="autonomous",
                )
                output = engine.run(agent, pred_task).output
                candidates.append(output)

        # Run selector
        selector_task = engine.create_task(
            name="select-best-prediction",
            payload={"candidates": candidates},
            created_by="autonomous",
        )
        selected = engine.run("AVOT-selector", selector_task).output
        predicted_spec = selected.get("selected_spec") or {}

        # ------------------------------------------------------------
        # 2. Fabricate (predictive mode)
        # ------------------------------------------------------------
        fab_task = engine.create_task(
            name="generate-sovereign-architecture",
            payload={
                "predict": True,
                "semantic_expand": True,
                "spec_override": predicted_spec
            },
            created_by="autonomous"
        )
        fabricated = engine.run("AVOT-fabricator", fab_task).output

        version = fabricated.get("version")
        filename = fabricated.get("filename")
        markdown = fabricated.get("markdown")
        spec = fabricated.get("spec")

        # ------------------------------------------------------------
        # 3. Guardian
        # ------------------------------------------------------------
        guardian_task = engine.create_task(
            name="validate-sovereign-architecture",
            payload={"version": version, "spec": spec, "markdown": markdown},
            created_by="autonomous"
        )
        guardian = engine.run("AVOT-guardian", guardian_task).output
        guardian_score = guardian.get("coherence_score", 0)

        # ------------------------------------------------------------
        # 4. Convergence
        # ------------------------------------------------------------
        convergence_task = engine.create_task(
            name="arbitrate-sovereign-architecture",
            payload={"guardian_score": guardian_score, "spec": spec, "metadata": {}},
            created_by="autonomous"
        )
        convergence = engine.run("AVOT-convergence", convergence_task).output

        convergence_score = convergence.get("convergence_score", 0)
        convergence_approved = convergence.get("convergence_approved")

        # Abort early if Convergence rejects
        if not convergence_approved:
            return {
                "status": "rejected",
                "reason": "Convergence did not approve predictive evolution.",
                "guardian_score": guardian_score,
                "convergence_score": convergence_score,
            }

        # ------------------------------------------------------------
        # 5. Archivist
        # ------------------------------------------------------------
        archivist_task = engine.create_task(
            name="archive-sovereign-architecture",
            payload={"version": version, "markdown": markdown, "filename": filename},
            created_by="autonomous"
        )
        archived = engine.run("AVOT-archivist", archivist_task).output

        archived_path = archived.get("path")
        metadata = archived.get("metadata", {})

        metadata["guardian_score"] = guardian_score
        metadata["convergence_score"] = convergence_score
        metadata["agent_id"] = "autonomous-cycle"
        metadata["timestamp"] = time.time()

        # ------------------------------------------------------------
        # 6. Indexer
        # ------------------------------------------------------------
        indexer_task = engine.create_task(
            name="update-master-index",
            payload={"version": version, "filename": filename, "metadata": metadata},
            created_by="autonomous"
        )
        engine.run("AVOT-indexer", indexer_task)

        # ------------------------------------------------------------
        # 7. PR Generator
        # ------------------------------------------------------------
        pr_task = engine.create_task(
            name="generate-architecture-pr",
            payload={"version": version, "filename": filename, "path": archived_path, "metadata": metadata},
            created_by="autonomous"
        )
        pr_data = engine.run("AVOT-pr-generator", pr_task).output

        # ------------------------------------------------------------
        # 8. Create branch + commit + open PR
        # ------------------------------------------------------------
        gh = GitHubClient()

        branch = pr_data["branch"]
        gh.create_branch(branch)
        gh.commit_file(
            branch=branch,
            file_path=f"docs/{filename}",
            content=markdown,
            message=pr_data["commit_message"],
        )
        pr_info = gh.open_pr(
            branch=branch,
            title=pr_data["pr"]["title"],
            body=pr_data["pr"]["body"],
        )

        return {
            "status": "submitted",
            "version": version,
            "pr_url": pr_info.get("html_url"),
            "guardian_score": guardian_score,
            "convergence_score": convergence_score,
        }

    def run_timed(self, duration_seconds: int = 3600):
        """
        Runs autonomous evolution cycles over a time window,
        using the RhythmEngine to determine pacing.
        """
        rhythm = RhythmEngine()

        end = time.time() + duration_seconds

        cycles = []

        while time.time() < end:
            pulse = rhythm.get_rhythm()

            cycles.append({
                "mode": pulse["mode"],
                "interval_seconds": pulse["interval_seconds"],
            })

            # Execute one evolution cycle
            result = self.run_cycle()
            cycles[-1]["result"] = result

            # Wait until next cycle
            time.sleep(pulse["interval_seconds"])

        return {"cycles": cycles}
