from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.catalog import get_problem, list_problems, problem_card, problem_public
from backend.service import ForgeService
from backend.store import AttemptRepository

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

repo = AttemptRepository(DATA / "forge.db")
service = ForgeService(repo)

app = FastAPI(title="Forge", description="LLD practice bench", version="1.0.0")


class StartAttemptBody(BaseModel):
    problem_id: str


class SubmitBody(BaseModel):
    design_notes: str = Field(default="", max_length=20000)
    class_outline: str = Field(default="", max_length=8000)
    code: str = Field(default="", max_length=80000)


@app.get("/api/health")
def health():
    return {"ok": True, "product": "forge"}


@app.get("/api/problems")
def problems():
    return [problem_card(p) for p in list_problems()]


@app.get("/api/problems/{problem_id}")
def problem_detail(problem_id: str):
    try:
        p = get_problem(problem_id)
    except KeyError:
        raise HTTPException(404, "Unknown problem")
    return problem_public(p)


@app.get("/api/problems/{problem_id}/sample")
def problem_sample(problem_id: str):
    """Starter text to try the evaluator — not a gold solution."""
    try:
        p = get_problem(problem_id)
    except KeyError:
        raise HTTPException(404, "Unknown problem")
    return {
        "design_notes": p.sample_notes,
        "class_outline": p.sample_outline,
        "code": p.sample_code,
    }


@app.post("/api/attempts")
def start_attempt(body: StartAttemptBody):
    try:
        attempt = service.start_attempt(body.problem_id)
    except KeyError:
        raise HTTPException(404, "Unknown problem")
    return attempt.to_dict()


@app.get("/api/attempts/{attempt_id}")
def get_attempt(attempt_id: str):
    attempt = repo.get_attempt(attempt_id)
    if not attempt:
        raise HTTPException(404, "Unknown attempt")
    return attempt.to_dict()


@app.post("/api/attempts/{attempt_id}/submissions")
def submit(attempt_id: str, body: SubmitBody):
    if not repo.get_attempt(attempt_id):
        raise HTTPException(404, "Unknown attempt")
    if not (body.design_notes.strip() or body.class_outline.strip() or body.code.strip()):
        raise HTTPException(400, "Write notes, an outline, or code before submitting.")
    attempt = service.submit(
        attempt_id,
        body.design_notes.strip(),
        body.class_outline.strip(),
        body.code,
    )
    return attempt.to_dict()


@app.post("/api/submissions/{submission_id}/retry")
def retry(submission_id: str):
    try:
        attempt = service.retry(submission_id)
    except KeyError:
        raise HTTPException(404, "Unknown submission")
    return attempt.to_dict()


@app.get("/api/history")
def history():
    rows = repo.history()
    titles = {p.id: p.title for p in list_problems()}
    for row in rows:
        row["problem_title"] = titles.get(row["problem_id"], row["problem_id"])
    return rows


if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND / "index.html")
