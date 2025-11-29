from __future__ import annotations

import time
from typing import Dict, Any

from avot_core.engine import AvotEngine
from avot_core.models import AvotTask

from avot_units.convergence_predictive import AvotConvergencePredictive  # noqa: F401
from backend.epoch import EpochRecorder
from backend.github_api import GitHubAPI as GitHubClient
from backend.drift_monitor import DriftMonitor
from backend.rhythm import RhythmEngine
from backend.epochs import EpochEngine
from backend.diagram_generator import DiagramGenerator
from backend.topology import TopologyExtractor
from backend.delta_engine import DeltaEngine
from backend.steering import SteeringEngine


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
        output: Dict[str, Any] = {}
        payload: Dict[str, Any] = {}

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
                candidate_output = engine.run(agent, pred_task).output
                candidates.append(candidate_output)

        # Run selector
        selector_task = engine.create_task(
            name="select-best-prediction",
            payload={"candidates": candidates},
            created_by="autonomous",
        )
        selected = engine.run("AVOT-selector", selector_task).output
        predicted_spec = selected.get("selected_spec") or {}

        # -------------------------------------------
        # C23: Generate predictive topology for v(next)
        # -------------------------------------------
        from backend.topology import TopologyExtractor

        drift_entries = DriftMonitor().load_entries()
        latest_version = drift_entries[-1]["version"] if drift_entries else "0"
        predictive_version = f"{float(latest_version) + 1}"
        topo = TopologyExtractor()

        # -------------------------------------------
        # C24: Predictive Steering
        # -------------------------------------------
        # Compute predictive delta vs current version
        try:
            current_version = str(float(latest_version))
            from backend.delta_engine import DeltaEngine
            de = DeltaEngine()
            predictive_delta = de.compute_delta(predictive_version, current_version)
        except:  # pragma: no cover - defensive
            predictive_delta = {}

        # Load epoch params (already computed earlier)
        epoch_parameters = epoch_params["parameters"]

        # Apply steering
        steering = SteeringEngine().steer(predicted_spec, predictive_delta, epoch_parameters)
        predicted_spec = steering["steered_spec"]
        steering_score = steering["steering_score"]
        output["steering_score"] = steering_score
        output["steering_actions"] = steering.get("actions", [])

        predicted_topology_path = topo.extract(predictive_version, predicted_spec)

        output["predictive_topology"] = predicted_topology_path

        # -------------------------------------------
        # C25: Self-Stabilizing Predictive Convergence Gate
        # -------------------------------------------

        # Compute predictive delta vs current version if possible
        try:
            # 'current_version' may be tracked upstream; if not available,
            # fall back to "0"
            current_version = str(payload.get("current_version", "0"))
        except Exception:
            current_version = "0"

        try:
            delta_engine = DeltaEngine()
            predictive_delta = delta_engine.compute_delta(
                v_new="predicted",   # synthetic ID for predicted spec
                v_old=current_version
            )
        except Exception:
            predictive_delta = {}

        # Epoch params were fetched earlier in the cycle (C16)
        # Ensure 'epoch_params' variable is available; if not, get it:
        try:
            epoch_state = epoch_params
        except NameError:
            epoch_state = EpochEngine().get_epoch()

        # Run AVOT-convergence-predictive
        pred_conv_task = engine.create_task(
            name="predictive-convergence-gate",
            payload={
                "predicted_spec": predicted_spec,
                "epoch": epoch_state,
                "steering_score": steering_score,
                "delta": predictive_delta,
            },
            created_by="autonomous",
        )
        pred_conv = engine.run("AVOT-convergence-predictive", pred_conv_task).output

        predictive_approved = pred_conv.get("predictive_approved", True)
        predictive_action = pred_conv.get("recommended_action", "proceed")

        # If predictive gate says 'hold', abort evolution early
        if not predictive_approved or predictive_action == "hold":
            return {
                "status": "blocked_by_predictive_convergence",
                "predictive_convergence": pred_conv,
            }

        # If recommended_action == 'proceed_softened', we can optionally
        # add a softening hint into metadata for later use.
        # (No structural change required here, but signal is preserved.)

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
            # --------------------------------------------------------
            #  SELF-HEALING PHASE (C17)
            # --------------------------------------------------------
            healer_task = engine.create_task(
                name="heal-rejected-architecture",
                payload={
                    "spec": spec,
                    "guardian_score": guardian_score,
                    "convergence_score": convergence_score,
                },
                created_by="autonomous",
            )
            healed = engine.run("AVOT-healer", healer_task).output
            healed_spec = healed.get("healed_spec", spec)

            # Retry Convergence with healed spec
            retry_guardian_task = engine.create_task(
                name="validate-sovereign-architecture",
                payload={"version": version, "spec": healed_spec, "markdown": ""},
                created_by="autonomous",
            )
            retry_guardian = engine.run("AVOT-guardian", retry_guardian_task).output
            g2 = retry_guardian.get("coherence_score", guardian_score)

            retry_conv_task = engine.create_task(
                name="arbitrate-sovereign-architecture",
                payload={"guardian_score": g2, "spec": healed_spec, "metadata": {}},
                created_by="autonomous",
            )
            retry_conv = engine.run("AVOT-convergence", retry_conv_task).output
            c2 = retry_conv.get("convergence_score", convergence_score)

            if not retry_conv.get("convergence_approved"):
                return {
                    "status": "rejected_after_healing",
                    "guardian_score": g2,
                    "convergence_score": c2,
                    "steering_score": steering_score,
                    "steering_actions": steering.get("actions", []),
                    "predictive_convergence": pred_conv,
                }

            # Success after healing — replace original spec
            spec = healed_spec
            output["healed"] = True

        # -------------------------------------------
        # C18: Generate architecture diagrams
        # -------------------------------------------
        diagram = DiagramGenerator()
        art_paths = diagram.generate(version, spec)
        output["visuals"] = art_paths

        # -------------------------------------------
        # C19: Extract Lattice Topology
        # -------------------------------------------
        topo = TopologyExtractor()
        topo_path = topo.extract(version, spec)
        output["topology"] = topo_path

        # ------------------------------------------------------------
        # 5. Archivist
        # ------------------------------------------------------------
        archivist_task = engine.create_task(
            name="archive-sovereign-architecture",
            payload={
                "version": version,
                "markdown": markdown,
                "filename": filename,
                "visuals": art_paths,
                "topology": topo_path,
                "steering_score": steering_score,
                "steering_actions": steering.get("actions", []),
                "predictive_convergence": pred_conv,
            },
            created_by="autonomous"
        )
        archived = engine.run("AVOT-archivist", archivist_task).output

        archived_path = archived.get("path")
        metadata = archived.get("metadata", {})

        metadata["guardian_score"] = guardian_score
        metadata["convergence_score"] = convergence_score
        metadata["agent_id"] = "autonomous-cycle"
        metadata["timestamp"] = time.time()
        metadata["predictive_convergence"] = pred_conv

        # ------------------------------------------------------------
        # 6. Indexer
        # ------------------------------------------------------------
        indexer_task = engine.create_task(
            name="update-master-index",
            payload={"version": version, "filename": filename, "metadata": metadata},
            created_by="autonomous"
        )
        engine.run("AVOT-indexer", indexer_task)

        # -------------------------------------------
        # C20: Epoch Chronicle Recording
        # -------------------------------------------
        arch_path = archived_path
        drift_data = DriftMonitor().analyze()
        drift_count = len(drift_data.get("drift_flags", []))

        # C21: compute delta vs previous version
        prev_version = str(float(version) - 1)  # naive step
        try:
            delta_engine = DeltaEngine()
            delta = delta_engine.compute_delta(version, prev_version)
            drift_count = delta.get("drift_count", drift_count)
        except:  # pragma: no cover - defensive
            delta = {}

        recorder = EpochRecorder()

        # Build a Tyme-style narrative summary
        summary_text = (
            f"Version {version} emerged from a coherence score of "
            f"{guardian_score} with convergence at {convergence_score}. "
            f"{'Healing was applied to restore structural clarity. ' if output.get('healed') else ''}"
            f"The lattice expanded its harmonic definition and "
            f"strengthened its sovereign alignment."
        )

        recorder.write_epoch({
            "version": version,
            "guardian_score": guardian_score,
            "convergence_score": convergence_score,
            "drift_count": drift_count,
            "healed": output.get("healed", False),
            "summary": summary_text,
            "architecture_path": arch_path,
            "visuals": output.get("visuals", {}),
            "topology": output.get("topology"),
            "delta": delta,
            "steering_score": steering_score,
            "steering_actions": steering.get("actions", []),
            "predictive_convergence": pred_conv,
        })

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

        output.update(
            {
                "status": "submitted",
                "version": version,
                "pr_url": pr_info.get("html_url"),
                "guardian_score": guardian_score,
                "convergence_score": convergence_score,
                "steering_score": steering_score,
                "steering_actions": steering.get("actions", []),
                "predictive_convergence": pred_conv,
            }
        )

        return output

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
