from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from types import SimpleNamespace
from typing import Optional
import os

from avot_units.fabricator import Fabricator
from avot_units.guardian import Guardian
from avot_units.archivist import Archivist
from avot_units.pr_generator import PRGenerator
from backend.github_api import GitHubAPI

app = FastAPI()


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

    guardian = Guardian()
    try:
        guardian_result = guardian.enforce(scroll)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if guardian_result is None:
        guardian_result = SimpleNamespace(output={})

    archivist = Archivist()
    archivist_result = SimpleNamespace(output={"metadata": {}, "artifact_path": None})
    scroll_path = archivist.archive(scroll, title=request.title, directory="docs")
    archivist_result.output["artifact_path"] = scroll_path
    guardian_score = guardian_result.output.get("coherence_score", 0)
    archivist_result.output["metadata"]["guardian_score"] = guardian_score
    import time
    archivist_result.output["metadata"]["agent_id"] = "AVOT-fabricator"
    archivist_result.output["metadata"]["timestamp"] = str(time.time())

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
