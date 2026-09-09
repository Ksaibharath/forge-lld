from __future__ import annotations

from backend.catalog import get_problem
from backend.evaluators.composite import CompositeEvaluator
from backend.models import Attempt, AttemptStatus, Evaluation, Submission
from backend.store import AttemptRepository


class ForgeService:
    def __init__(self, repo: AttemptRepository, evaluator: CompositeEvaluator | None = None):
        self.repo = repo
        self.evaluator = evaluator or CompositeEvaluator()

    def start_attempt(self, problem_id: str) -> Attempt:
        get_problem(problem_id)  # raises KeyError
        return self.repo.create_attempt(problem_id)

    def submit(self, attempt_id: str, design_notes: str, class_outline: str, code: str) -> Attempt:
        attempt = self.repo.get_attempt(attempt_id)
        if attempt is None:
            raise KeyError("attempt")
        problem = get_problem(attempt.problem_id)
        self.repo.set_status(attempt_id, AttemptStatus.EVALUATING)
        sub = self.repo.add_submission(attempt_id, design_notes, class_outline, code)
        evaluation = self._run(problem, sub)
        self.repo.save_evaluation(evaluation)
        status = (
            AttemptStatus.EVALUATED
            if evaluation.status in {"complete", "partial"}
            else AttemptStatus.EVALUATION_FAILED
        )
        self.repo.set_status(attempt_id, status)
        result = self.repo.get_attempt(attempt_id)
        assert result is not None
        return result

    def retry(self, submission_id: str) -> Attempt:
        sub = self.repo.get_submission(submission_id)
        if sub is None:
            raise KeyError("submission")
        attempt = self.repo.get_attempt(sub.attempt_id)
        if attempt is None:
            raise KeyError("attempt")
        problem = get_problem(attempt.problem_id)
        self.repo.set_status(attempt.id, AttemptStatus.EVALUATING)
        evaluation = self._run(problem, sub)
        self.repo.save_evaluation(evaluation)
        status = (
            AttemptStatus.EVALUATED
            if evaluation.status in {"complete", "partial"}
            else AttemptStatus.EVALUATION_FAILED
        )
        self.repo.set_status(attempt.id, status)
        result = self.repo.get_attempt(attempt.id)
        assert result is not None
        return result

    def _run(self, problem, sub: Submission) -> Evaluation:
        try:
            return self.evaluator.evaluate(problem, sub)
        except Exception as exc:  # noqa: BLE001
            return Evaluation(
                id="ev_failed",
                submission_id=sub.id,
                status="failed",
                overall_score=0,
                dimensions=[],
                findings=[],
                strengths=[],
                improvements=["Evaluation crashed. Retry — this is the boring failure path, not a queue."],
                missing_considerations=[],
                narrative="The evaluator raised an unexpected error. Your submission is saved.",
                deterministic_ran=False,
                ai_status="failed",
                ai_error=str(exc)[:400],
                evaluator_names=["composite"],
                created_at=sub.submitted_at,
            )
