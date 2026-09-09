from __future__ import annotations

from backend.evaluators.deterministic import DeterministicEvaluator
from backend.evaluators.llm import LLMEvaluator
from backend.models import Evaluation, Finding, FindingSeverity, ProblemSpec, Submission, new_id, now_iso


class CompositeEvaluator:
    """Deterministic always. LLM if configured. Merge without losing rule findings."""

    name = "composite"

    def __init__(
        self,
        deterministic: DeterministicEvaluator | None = None,
        llm: LLMEvaluator | None = None,
    ):
        self.deterministic = deterministic or DeterministicEvaluator()
        self.llm = llm or LLMEvaluator()

    def evaluate(self, problem: ProblemSpec, submission: Submission) -> Evaluation:
        det = self.deterministic.evaluate(problem, submission)
        llm_result: Evaluation | None = None
        try:
            llm_result = self.llm.evaluate(problem, submission)
        except Exception as exc:  # noqa: BLE001
            llm_result = self.llm._failed(submission.id, "failed", str(exc)[:400])

        ai_status = llm_result.ai_status if llm_result else "failed"
        names = [self.deterministic.name]
        if llm_result and llm_result.ai_status == "complete":
            names.append(self.llm.name)

        strengths = det.strengths[:]
        improvements = det.improvements[:]
        missing = det.missing_considerations[:]
        narrative = det.narrative
        dimensions = det.dimensions
        overall = det.overall_score
        findings = det.findings[:]

        if llm_result and llm_result.ai_status == "complete":
            strengths = _uniq(llm_result.strengths + strengths)[:5]
            improvements = _uniq(llm_result.improvements + improvements)[:6]
            missing = _uniq(llm_result.missing_considerations + missing)[:6]
            if llm_result.narrative:
                narrative = llm_result.narrative
            if llm_result.dimensions:
                dimensions = llm_result.dimensions
                # Blend 60% rules / 40% LLM so a poetic model cannot hide a missing design.
                overall = int(round(0.6 * det.overall_score + 0.4 * llm_result.overall_score))
            findings.append(
                Finding(
                    "llm",
                    "AI critique",
                    True,
                    FindingSeverity.PASS,
                    "Qualitative critique ran on top of the mechanical rubric.",
                    source="llm",
                )
            )
        else:
            err = (llm_result.ai_error if llm_result else "unknown") or ""
            findings.append(
                Finding(
                    "llm",
                    "AI critique",
                    False,
                    FindingSeverity.INFO,
                    "AI critique skipped (no API key). Rule-based interviewer notes are shown instead."
                    if ai_status == "skipped"
                    else f"AI critique failed ({err}). Showing mechanical feedback. Use Retry.",
                    source="llm",
                )
            )

        status = "complete" if det.deterministic_ran else "failed"
        if not det.deterministic_ran:
            status = "failed"

        return Evaluation(
            id=new_id("ev"),
            submission_id=submission.id,
            status=status if det.deterministic_ran else "failed",
            overall_score=overall,
            dimensions=dimensions,
            findings=findings,
            strengths=strengths,
            improvements=improvements,
            missing_considerations=missing,
            narrative=narrative,
            deterministic_ran=det.deterministic_ran,
            ai_status=ai_status,
            ai_error=None if ai_status == "complete" else (llm_result.ai_error if llm_result else None),
            evaluator_names=names,
            created_at=now_iso(),
        )


def _uniq(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out
