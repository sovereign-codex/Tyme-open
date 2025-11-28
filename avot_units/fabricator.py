from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional

from avot_core.protocols import BaseAVOT
from avot_core.models import AvotTask
from avot_core.registry import register_avot
from backend.drift_monitor import DriftMonitor


@dataclass
class Fabrication:
    summary: str
    notes: Optional[str]
    created_at: datetime


@register_avot("AVOT-fabricator")
class Fabricator(BaseAVOT):
    """Generates Sovereign Architecture scroll content."""

    description = "Creates Sovereign Architecture specs and scrolls."

    def create_scroll(
        self,
        summary: str,
        notes: Optional[str] = None,
        spec: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        timestamp = datetime.utcnow().isoformat() + "Z"
        header = ["# Sovereign Architecture Scroll", f"Generated at: {timestamp}"]

        spec = spec or {}
        metadata = metadata or {}

        body = ["## Summary", summary.strip() or "No summary provided."]

        if spec:
            body.append("\n## Layers")
            layers: List[Dict[str, Any]] = spec.get("layers", [])
            if layers:
                for layer in layers:
                    name = layer.get("name", "layer")
                    components = ", ".join(layer.get("components", [])) or "unspecified"
                    body.append(f"- **{name}**: {components}")
            else:
                body.append("- No layers defined.")

            lifecycle = spec.get("lifecycle", {})
            if lifecycle:
                rhythm = lifecycle.get("governance_rhythm", "unspecified rhythm")
                body.append("\n## Lifecycle & Governance")
                body.append(f"- governance_rhythm: {rhythm}")

        if metadata:
            body.append("\n## Metadata")
            for key, value in metadata.items():
                body.append(f"- {key}: {value}")

        if notes:
            body.append("\n## Fabricator Notes")
            body.append(notes.strip())

        footer = ["\n---", "Prepared by the AVOT Fabricator."]
        return "\n\n".join(header + body + footer)

    def act(self, task: AvotTask) -> Dict[str, Any]:
        payload = task.payload or {}

        # Baseline architecture spec
        spec: Dict[str, Any] = payload.get("spec") or {
            "description": payload.get(
                "description",
                "Sovereign Intelligence base architecture synthesized by AVOT-fabricator.",
            ),
            "root_node": "sovereign_intelligence",
            "layers": payload.get(
                "layers",
                [
                    {"name": "layer_1", "components": ["core", "governance", "flow"]},
                    {"name": "layer_2", "components": ["core", "governance", "flow"]},
                    {"name": "layer_3", "components": ["core", "governance", "flow"]},
                ],
            ),
            "lifecycle": payload.get(
                "lifecycle",
                {
                    "governance_rhythm": "periodic review + convergence arbitration",
                },
            ),
        }

        metadata: Dict[str, Any] = dict(payload.get("metadata", {}))
        metadata["timestamp"] = metadata.get("timestamp") or datetime.utcnow().timestamp()

        # Drift analysis to embed temporal signals
        metadata["drift_analysis"] = DriftMonitor().analyze()

        # If predictive mode is requested
        if payload.get("predict", False):
            predictor_task = AvotTask(
                name="predict-next-architecture",
                payload={"layers": spec.get("layers", [])},
                created_by=task.created_by
            )
            predictor_output = self.engine.run("AVOT-predictor", predictor_task).output

            predicted_spec = predictor_output.get("predicted_spec", {})
            signals = predictor_output.get("signals", {})

            spec = predicted_spec  # override with predicted structure
            metadata["prediction_signals"] = signals

        summary_text = payload.get("summary") or spec.get("description", "")
        notes = payload.get("fabrication_notes") or payload.get("notes")

        markdown = self.create_scroll(
            summary=summary_text,
            notes=notes,
            spec=spec,
            metadata=metadata,
        )

        return {
            "spec": spec,
            "markdown": markdown,
            "metadata": metadata,
        }
