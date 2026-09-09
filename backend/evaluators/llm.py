from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from backend.models import (
    DimensionScore,
    Evaluation,
    Finding,
    FindingSeverity,
    ProblemSpec,
    Submission,
    new_id,
    now_iso,
)

SYSTEM_PROMPT = """You are a senior engineer giving LLD interview feedback.
Multiple designs can be valid. Never say the submission is simply correct or incorrect.
Ground every comment in what the learner actually wrote. Do not invent classes they did not mention.
Prefer 'this will hurt when X changes' over 'use pattern Y'.
Return ONLY JSON with keys:
narrative (string, 3-6 sentences, interviewer voice),
strengths (string array, max 4),
improvements (string array, max 5),
missing_considerations (string array, max 5),
dimensions (array of {name, score 0-10, comment}).
Dimension names must be exactly:
Requirements coverage, Object modelling, SOLID / patterns, Extensibility, Trade-off awareness.
"""


class LLMEvaluator:
    """Qualitative critique. Uses OpenAI if OPENAI_API_KEY is set; otherwise skipped."""

    name = "llm"

    def __init__(self, timeout_sec: float = 12.0):
        self.timeout_sec = timeout_sec

    def available(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))

    def evaluate(self, problem: ProblemSpec, submission: Submission) -> Evaluation:
        if not self.available():
            return self._failed(submission.id, "skipped", "OPENAI_API_KEY not set")
        payload = {
            "problem": problem.title,
            "statement": problem.statement,
            "requirements": problem.functional_requirements,
            "considerations": problem.considerations,
            "design_notes": submission.design_notes,
            "class_outline": submission.class_outline,
            "code": (submission.code or "")[:6000],
        }
        try:
            data = self._call(payload)
            return self._parse(submission.id, data)
        except Exception as exc:  # noqa: BLE001 — we convert any failure to a status
            return self._failed(submission.id, "failed", str(exc)[:400])

    def _call(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(
            {
                "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload)},
                ],
            }
        ).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
            raw = json.loads(resp.read().decode())
        content = raw["choices"][0]["message"]["content"]
        return json.loads(content)

    def _parse(self, submission_id: str, data: dict[str, Any]) -> Evaluation:
        dims = []
        for d in data.get("dimensions", []):
            try:
                dims.append(
                    DimensionScore(
                        name=str(d["name"]),
                        score=int(max(0, min(10, int(d["score"])))),
                        comment=str(d.get("comment", "")),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        overall = int(round(sum(d.score for d in dims) / max(1, len(dims)) * 10)) if dims else 0
        return Evaluation(
            id=new_id("ev"),
            submission_id=submission_id,
            status="complete",
            overall_score=max(0, min(100, overall)),
            dimensions=dims,
            findings=[],
            strengths=list(data.get("strengths") or [])[:4],
            improvements=list(data.get("improvements") or [])[:5],
            missing_considerations=list(data.get("missing_considerations") or [])[:5],
            narrative=str(data.get("narrative") or ""),
            deterministic_ran=False,
            ai_status="complete",
            ai_error=None,
            evaluator_names=[self.name],
            created_at=now_iso(),
        )

    def _failed(self, submission_id: str, ai_status: str, error: str) -> Evaluation:
        return Evaluation(
            id=new_id("ev"),
            submission_id=submission_id,
            status="failed" if ai_status == "failed" else "complete",
            overall_score=0,
            dimensions=[],
            findings=[
                Finding(
                    "llm",
                    "AI critique",
                    False,
                    FindingSeverity.INFO,
                    "AI critique unavailable — mechanical checks still apply. Retry when a key is configured."
                    if ai_status == "skipped"
                    else f"AI critique failed: {error}",
                )
            ],
            strengths=[],
            improvements=[],
            missing_considerations=[],
            narrative="",
            deterministic_ran=False,
            ai_status=ai_status,
            ai_error=error,
            evaluator_names=[self.name],
            created_at=now_iso(),
        )
