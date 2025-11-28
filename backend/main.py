from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from types import SimpleNamespace
from typing import Optional
import os

from avot_units.convergence import AvotConvergence
from avot_units.fabricator import Fabricator
from avot_units.guardian import Guardian
from avot_units.archivist import Archivist
from avot_units.pr_generator import PRGenerator
from avot_units.indexer import AvotIndexer
from backend.github_api import GitHubAPI
from backend.drift_monitor import DriftMonitor
from backend.heatmap_analyzer import HeatmapAnalyzer
from backend.autonomous import AutonomousEvolution

app = FastAPI()
engine = SimpleNamespace(
    create_task=lambda **kwargs: SimpleNamespace(**kwargs),
    run=lambda name, task: SimpleNamespace(
        output=AvotConvergence().act(SimpleNamespace(payload=task.payload))
    ),
)


class AutoPRRequest(BaseModel):
    title: str
    summary: str
    head: str
    base: str
    repo_owner: str
    repo_name: str
    fabrication_notes: Optional[str] = None
    token: Optional[str] = None


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.post("/avot/fabricator/auto-pr")
def trigger_auto_pr(request: AutoPRRequest):
    token = request.token or os.getenv("GITHUB_TOKEN")
    if not token:
        raise HTTPException(status_code=400, detail="GitHub token is required.")

    fabricator = Fabricator()
    scroll = fabricator.create_scroll(summary=request.summary, notes=request.fabrication_notes)
    fab_output = {"spec": {}}

    guardian = Guardian()
    try:
        guardian_result = guardian.enforce(scroll)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if guardian_result is None:
        guardian_result = SimpleNamespace(output={})

    archivist_result = SimpleNamespace(output={"metadata": {}, "artifact_path": None})
    guardian_score = guardian_result.output.get("coherence_score", 0)

    # 2.5) Convergence (multi-AVOT arbitration)
    convergence_task = engine.create_task(
        name="arbitrate-sovereign-architecture",
        payload={
            "guardian_score": guardian_score,
            "spec": fab_output.get("spec"),
            "metadata": archivist_result.output.get("metadata", {}),
        },
        created_by="api",
    )
    convergence_result = engine.run("AVOT-convergence", convergence_task)
    convergence_output = convergence_result.output

    # Inject convergence_score and approval into metadata
    archivist_result.output["metadata"]["convergence_score"] = convergence_output["convergence_score"]
    archivist_result.output["metadata"]["convergence_approved"] = convergence_output["convergence_approved"]

    archivist = Archivist()
    scroll_path = archivist.archive(scroll, title=request.title, directory="docs")
    archivist_result.output["artifact_path"] = scroll_path
    archivist_result.output["metadata"]["guardian_score"] = guardian_score
    import time
    archivist_result.output["metadata"]["agent_id"] = "AVOT-fabricator"
    archivist_result.output["metadata"]["timestamp"] = str(time.time())
    version = archivist_result.output["metadata"].get("version", "unknown")
    filename = os.path.basename(scroll_path)

    # 3) Master Architecture Index Update
    indexer_task = engine.create_task(
        name="update-master-index",
        payload={
            "version": version,
            "filename": filename,
            "metadata": archivist_result.output["metadata"],
        },
        created_by="api",
    )
    indexer_result = engine.run("AVOT-indexer", indexer_task)

    pr_generator = PRGenerator()
    payload = pr_generator.generate(
        title=request.title,
        summary=request.summary,
        head=request.head,
        base=request.base,
        scroll_path=scroll_path,
        notes=request.fabrication_notes,
    )

    github_api = GitHubAPI(token)
    try:
        pr_response = github_api.create_pull_request(
            owner=request.repo_owner,
            repo=request.repo_name,
            title=payload["title"],
            body=payload["body"],
            head=payload["head"],
            base=payload["base"],
        )
    except Exception as exc:  # pragma: no cover - external API
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "status": "submitted",
        "scroll_path": scroll_path,
        "pull_request": pr_response,
    }


@app.get("/governance/summary")
def get_governance_summary():
    """
    Returns a JSON summary of the latest architecture update as well
    as metadata needed for the governance panel.
    """
    import os, re, json

    index_path = "docs/MASTER-ARCHITECTURE-INDEX.md"
    latest = None

    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            text = f.read()

        # Parse the most recent version block
        blocks = re.split(r"## Version ", text)
        if len(blocks) > 1:
            last = "## Version " + blocks[-1]
            # Extract components
            version = re.search(r"v([0-9.]+)", last)
            filename = re.search(r"Filename:\*\* `([^`]+)`", last)
            guard = re.search(r"Guardian Score:\*\* ([0-9.]+)", last)
            conv = re.search(r"Convergence Score:\*\* ([0-9.]+)", last)
            ts = re.search(r"Timestamp:\*\* ([0-9.]+)", last)

            latest = {
                "version": version.group(1) if version else "unknown",
                "filename": filename.group(1) if filename else "unknown",
                "guardian_score": guard.group(1) if guard else "unknown",
                "convergence_score": conv.group(1) if conv else "unknown",
                "timestamp": ts.group(1) if ts else "unknown",
                "pr_url": f"https://github.com/sovereign-codex/Tyme-open/pull"  # placeholder
            }

    return {
        "latest": latest
    }


@app.get("/governance/evolution.json")
def get_evolution_data():
    """
    Extracts all versions and their scores from the MAI and returns
    a JSON structure suitable for plotting the architecture evolution graph.
    """

    import os, re

    index_path = "docs/MASTER-ARCHITECTURE-INDEX.md"

    versions = []
    guardian_scores = []
    convergence_scores = []

    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            text = f.read()

        blocks = re.split(r"## Version ", text)
        for block in blocks[1:]:
            version_match = re.search(r"v([0-9.]+)", block)
            guardian_match = re.search(r"Guardian Score:\*\* ([0-9.]+)", block)
            convergence_match = re.search(r"Convergence Score:\*\* ([0-9.]+)", block)

            if version_match:
                versions.append(version_match.group(1))
                guardian_scores.append(float(guardian_match.group(1)) if guardian_match else None)
                convergence_scores.append(float(convergence_match.group(1)) if convergence_match else None)

    return {
        "versions": versions,
        "guardian_scores": guardian_scores,
        "convergence_scores": convergence_scores
    }


@app.get("/governance/drift.json")
def get_drift_data():
    """
    Provides temporal coherence smoothing, drift detection,
    stability index, and full score evolution history.
    """
    monitor = DriftMonitor()
    return monitor.analyze()


@app.get("/governance/heatmap.json")
def get_heatmap_data():
    """
    Computes layer-change intensity between versions and returns
    a numeric heatmap for UI visualization.
    """
    analyzer = HeatmapAnalyzer()
    return analyzer.analyze()


@app.post("/autonomous/run")
def autonomous_run():
    """
    Triggers a full predictive evolution cycle.
    """
    ae = AutonomousEvolution()
    return ae.run_cycle()
