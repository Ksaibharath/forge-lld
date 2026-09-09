from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class AttemptStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    EVALUATING = "evaluating"
    EVALUATED = "evaluated"
    EVALUATION_FAILED = "evaluation_failed"


class FindingSeverity(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    INFO = "info"


@dataclass
class RubricSignal:
    """One checkable consideration for a problem."""

    id: str
    label: str
    weight: float
    keywords: list[str]
    class_names: list[str] = field(default_factory=list)
    missing_feedback: str = ""
    present_feedback: str = ""


@dataclass
class ProblemSpec:
    id: str
    title: str
    difficulty: Difficulty
    minutes: int
    summary: str
    statement: str
    functional_requirements: list[str]
    constraints: list[str]
    considerations: list[str]
    expected_entities: list[str]
    expected_patterns: list[str]
    expected_apis: list[str]
    rubric: list[RubricSignal]
    sample_outline: str
    sample_notes: str
    sample_code: str


@dataclass
class Finding:
    rule_id: str
    label: str
    passed: bool
    severity: FindingSeverity
    message: str
    source: str = "deterministic"


@dataclass
class DimensionScore:
    name: str
    score: int  # 0-10
    comment: str


@dataclass
class Evaluation:
    id: str
    submission_id: str
    status: str  # complete | partial | failed
    overall_score: int
    dimensions: list[DimensionScore]
    findings: list[Finding]
    strengths: list[str]
    improvements: list[str]
    missing_considerations: list[str]
    narrative: str
    deterministic_ran: bool
    ai_status: str  # complete | skipped | failed
    ai_error: Optional[str]
    evaluator_names: list[str]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "submission_id": self.submission_id,
            "status": self.status,
            "overall_score": self.overall_score,
            "dimensions": [d.__dict__ for d in self.dimensions],
            "findings": [
                {**f.__dict__, "severity": f.severity.value} for f in self.findings
            ],
            "strengths": self.strengths,
            "improvements": self.improvements,
            "missing_considerations": self.missing_considerations,
            "narrative": self.narrative,
            "deterministic_ran": self.deterministic_ran,
            "ai_status": self.ai_status,
            "ai_error": self.ai_error,
            "evaluator_names": self.evaluator_names,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Evaluation":
        dims = [DimensionScore(**d) for d in data.get("dimensions", [])]
        findings = []
        for f in data.get("findings", []):
            findings.append(
                Finding(
                    rule_id=f["rule_id"],
                    label=f["label"],
                    passed=f["passed"],
                    severity=FindingSeverity(f["severity"]),
                    message=f["message"],
                    source=f.get("source", "deterministic"),
                )
            )
        return Evaluation(
            id=data["id"],
            submission_id=data["submission_id"],
            status=data["status"],
            overall_score=data["overall_score"],
            dimensions=dims,
            findings=findings,
            strengths=data.get("strengths", []),
            improvements=data.get("improvements", []),
            missing_considerations=data.get("missing_considerations", []),
            narrative=data.get("narrative", ""),
            deterministic_ran=data.get("deterministic_ran", True),
            ai_status=data.get("ai_status", "skipped"),
            ai_error=data.get("ai_error"),
            evaluator_names=data.get("evaluator_names", []),
            created_at=data["created_at"],
        )


@dataclass
class Submission:
    id: str
    attempt_id: str
    design_notes: str
    class_outline: str
    code: str
    submitted_at: str
    evaluation: Optional[Evaluation] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "attempt_id": self.attempt_id,
            "design_notes": self.design_notes,
            "class_outline": self.class_outline,
            "code": self.code,
            "submitted_at": self.submitted_at,
            "evaluation": self.evaluation.to_dict() if self.evaluation else None,
        }


@dataclass
class Attempt:
    id: str
    problem_id: str
    status: AttemptStatus
    created_at: str
    updated_at: str
    submissions: list[Submission] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "problem_id": self.problem_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "submissions": [s.to_dict() for s in self.submissions],
        }
