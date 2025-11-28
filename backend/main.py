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
