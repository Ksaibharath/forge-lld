from __future__ import annotations

from typing import Protocol

from backend.models import Evaluation, ProblemSpec, Submission


class Evaluator(Protocol):
    name: str

    def evaluate(self, problem: ProblemSpec, submission: Submission) -> Evaluation: ...
