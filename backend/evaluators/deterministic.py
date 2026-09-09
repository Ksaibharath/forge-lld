from __future__ import annotations

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
from backend.signals import CombinedExtractor, DesignSignals


class DeterministicEvaluator:
    """Rule-based checks. Explainable, always available, never 'wrong vs official solution'."""

    name = "deterministic"

    def __init__(self, extractor: CombinedExtractor | None = None):
        self.extractor = extractor or CombinedExtractor()

    def evaluate(self, problem: ProblemSpec, submission: Submission) -> Evaluation:
        signals = self.extractor.extract(submission)
        findings: list[Finding] = []

        notes = (submission.design_notes or "").strip()
        outline = (submission.class_outline or "").strip()
        code = (submission.code or "").strip()

        if not notes:
            findings.append(
                Finding(
                    "notes_present",
                    "Design notes",
                    False,
                    FindingSeverity.FAIL,
                    "Notes are empty. In an interview the talk track is the design — write assumptions, types, and one trade-off.",
                )
            )
        elif len(notes) < 80:
            findings.append(
                Finding(
                    "notes_present",
                    "Design notes",
                    False,
                    FindingSeverity.WARN,
                    "Notes are very short. Spell out assumptions and at least one extension point.",
                )
            )
        else:
            findings.append(
                Finding(
                    "notes_present",
                    "Design notes",
                    True,
                    FindingSeverity.PASS,
                    "There is a written design, not only code.",
                )
            )

        if signals.parse_error:
            findings.append(
                Finding(
                    "code_parses",
                    "Code parses",
                    False,
                    FindingSeverity.WARN,
                    f"Python did not parse ({signals.parse_error}). Outline and notes were still graded.",
                )
            )
        elif code:
            findings.append(
                Finding(
                    "code_parses",
                    "Code parses",
                    True,
                    FindingSeverity.PASS,
                    "Submitted Python parsed — we could inspect types and methods.",
                )
            )
        else:
            findings.append(
                Finding(
                    "code_parses",
                    "Code parses",
                    True,
                    FindingSeverity.INFO,
                    "No code submitted. That is allowed; modelling is graded from notes and outline.",
                )
            )

        # Entity coverage
        entity_hits = [e for e in problem.expected_entities if signals.has_class(e) or signals.mentions([e])]
        entity_miss = [e for e in problem.expected_entities if e not in entity_hits]
        if len(entity_hits) >= max(2, len(problem.expected_entities) - 2):
            findings.append(
                Finding(
                    "entities",
                    "Core entities",
                    True,
                    FindingSeverity.PASS,
                    "Recognised types: " + ", ".join(entity_hits) + ".",
                )
            )
        else:
            findings.append(
                Finding(
                    "entities",
                    "Core entities",
                    False,
                    FindingSeverity.FAIL,
                    "Missing or unnamed types: "
                    + ", ".join(entity_miss)
                    + ". Interviewers look for these nouns even if you name them slightly differently.",
                )
            )

        # Rubric signals
        rubric_hits = 0.0
        rubric_total = 0.0
        missing_considerations: list[str] = []
        strengths: list[str] = []
        for item in problem.rubric:
            rubric_total += item.weight
            hit = signals.mentions(item.keywords) or any(signals.has_class(c) for c in item.class_names)
            if hit:
                rubric_hits += item.weight
                findings.append(
                    Finding(
                        item.id,
                        item.label,
                        True,
                        FindingSeverity.PASS,
                        item.present_feedback or f"Covered: {item.label}.",
                    )
                )
                if item.present_feedback:
                    strengths.append(item.present_feedback)
            else:
                findings.append(
                    Finding(
                        item.id,
                        item.label,
                        False,
                        FindingSeverity.WARN,
                        item.missing_feedback or f"Not seen: {item.label}.",
                    )
                )
                missing_considerations.append(item.missing_feedback or item.label)

        # Patterns / ABC
        if problem.expected_patterns:
            pattern_ok = False
            if "Strategy" in problem.expected_patterns or "State" in problem.expected_patterns:
                pattern_ok = signals.uses_abc or signals.uses_abstract_method or _has_strategy_shape(signals)
                pattern_ok = pattern_ok or signals.mentions(
                    [p.lower() for p in problem.expected_patterns] + ["interface", "abc", "abstract"]
                )
            if "Enum" in problem.expected_patterns:
                pattern_ok = pattern_ok or signals.uses_enum or signals.mentions(["enum"])
            findings.append(
                Finding(
                    "patterns",
                    "Extension points / patterns",
                    pattern_ok,
                    FindingSeverity.PASS if pattern_ok else FindingSeverity.WARN,
                    (
                        "You named or implemented an extension point ("
                        + ", ".join(problem.expected_patterns)
                        + ")."
                    )
                    if pattern_ok
                    else (
                        "This problem usually wants a swappable policy ("
                        + ", ".join(problem.expected_patterns)
                        + "). An ABC, Strategy, or State object is the typical move — only if the behaviour actually varies."
                    ),
                )
            )

        # APIs
        api_hits = [a for a in problem.expected_apis if signals.mentions([a])]
        if problem.expected_apis:
            findings.append(
                Finding(
                    "apis",
                    "Key operations",
                    len(api_hits) >= 1,
                    FindingSeverity.PASS if api_hits else FindingSeverity.WARN,
                    ("Operations mentioned: " + ", ".join(api_hits) + ".")
                    if api_hits
                    else "Name the public operations (entry/exit, insert/select, hall call). Interviewers hang the rest of the talk on those signatures.",
                )
            )

        # God class
        if signals.method_counts:
            total_m = sum(signals.method_counts.values()) or 1
            top_cls, top_n = max(signals.method_counts.items(), key=lambda kv: kv[1])
            if top_n >= 10 and top_n / total_m >= 0.7 and len(signals.method_counts) <= 2:
                findings.append(
                    Finding(
                        "god_class",
                        "Responsibility split",
                        False,
                        FindingSeverity.WARN,
                        f"{top_cls} holds {top_n} methods — that is a god-object smell. Push occupancy, pricing, or inventory out.",
                    )
                )
            elif len(signals.class_names) >= 3:
                findings.append(
                    Finding(
                        "god_class",
                        "Responsibility split",
                        True,
                        FindingSeverity.PASS,
                        "Behaviour is spread across several types, not one manager.",
                    )
                )

        tradeoff = _mentions_tradeoff(notes)
        findings.append(
            Finding(
                "tradeoffs",
                "Trade-off awareness",
                tradeoff,
                FindingSeverity.PASS if tradeoff else FindingSeverity.INFO,
                "You named a limitation or an alternative — that is what interviewers actually grade."
                if tradeoff
                else "Add one sentence of the form 'I did X instead of Y because…' or 'this breaks if…'.",
            )
        )

        dimensions = _dimensions(
            problem, signals, notes, outline, code, entity_hits, rubric_hits, rubric_total, tradeoff, findings
        )
        overall = int(round(sum(d.score for d in dimensions) / max(1, len(dimensions)) * 10))
        overall = max(4, min(96, overall))
        if not notes and not outline and not code:
            overall = min(overall, 8)

        improvements = [f.message for f in findings if not f.passed and f.severity in {FindingSeverity.FAIL, FindingSeverity.WARN}]
        if not strengths:
            if notes:
                strengths.append("You started from the problem, not from a framework.")
            else:
                strengths.append("Empty attempt — nothing to praise yet. Write the types first.")

        narrative = _narrative(problem, overall, strengths, missing_considerations, signals)

        return Evaluation(
            id=new_id("ev"),
            submission_id=submission.id,
            status="complete",
            overall_score=overall,
            dimensions=dimensions,
            findings=findings,
            strengths=strengths[:5],
            improvements=improvements[:6],
            missing_considerations=missing_considerations[:6],
            narrative=narrative,
            deterministic_ran=True,
            ai_status="skipped",
            ai_error=None,
            evaluator_names=[self.name],
            created_at=now_iso(),
        )


def _has_strategy_shape(signals: DesignSignals) -> bool:
    # Multiple subclasses of the same ABC-ish base.
    parents: dict[str, list[str]] = {}
    for child, bases in signals.base_classes.items():
        for b in bases:
            if b in {"object", "Exception", "Enum", ""}:
                continue
            parents.setdefault(b, []).append(child)
    return any(len(children) >= 2 for children in parents.values())


def _mentions_tradeoff(notes: str) -> bool:
    blob = notes.lower()
    needles = [
        "trade",
        "instead of",
        "later",
        "extens",
        "would change",
        "limitation",
        "assumption",
        "alternative",
        "because",
        "swap",
        "without rewriting",
        "not doing",
        "out of scope",
    ]
    return any(n in blob for n in needles)


def _dimensions(
    problem: ProblemSpec,
    signals: DesignSignals,
    notes: str,
    outline: str,
    code: str,
    entity_hits: list[str],
    rubric_hits: float,
    rubric_total: float,
    tradeoff: bool,
    findings: list[Finding],
) -> list[DimensionScore]:
    req_ratio = (rubric_hits / rubric_total) if rubric_total else 0
    req_score = int(round(req_ratio * 10))
    if len(notes) > 200:
        req_score = min(10, req_score + 1)

    model_score = min(10, 2 + 2 * min(4, len(entity_hits)))
    if signals.parsed_code and len(signals.class_names) >= 3:
        model_score = min(10, model_score + 1)
    if not notes and not outline:
        model_score = min(model_score, 3)

    solid = 3
    if signals.uses_abc or signals.uses_abstract_method:
        solid += 3
    if signals.uses_enum:
        solid += 1
    if signals.exception_classes:
        solid += 1
    if _has_strategy_shape(signals):
        solid += 2
    if any(f.rule_id == "god_class" and not f.passed for f in findings):
        solid -= 2
    solid = max(1, min(10, solid))
    if not code and not outline:
        solid = min(solid, 6)
        if any(p.lower() in notes.lower() for p in problem.expected_patterns):
            solid = max(solid, 6)

    ext = int(round(req_ratio * 6)) + (2 if signals.uses_abc or "strategy" in notes.lower() or "state" in notes.lower() else 0)
    ext = max(2, min(10, ext + (1 if "later" in notes.lower() or "swap" in notes.lower() else 0)))

    trade = 8 if tradeoff else 4
    if len(notes) > 400 and tradeoff:
        trade = 9
    if not notes:
        trade = 2

    return [
        DimensionScore("Requirements coverage", req_score, _band(req_score, "requirements")),
        DimensionScore("Object modelling", model_score, _band(model_score, "modelling")),
        DimensionScore("SOLID / patterns", solid, _band(solid, "patterns")),
        DimensionScore("Extensibility", ext, _band(ext, "extensibility")),
        DimensionScore("Trade-off awareness", trade, _band(trade, "trade-offs")),
    ]


def _band(score: int, topic: str) -> str:
    if score >= 8:
        return f"Strong {topic} for an interview pass."
    if score >= 5:
        return f"Adequate {topic}; one more concrete example would lift this."
    return f"Thin {topic} — this is what a follow-up question would probe."


def _narrative(
    problem: ProblemSpec,
    overall: int,
    strengths: list[str],
    missing: list[str],
    signals: DesignSignals,
) -> str:
    opening = {
        True: f"This is a workable first cut of {problem.title.lower().replace('design ', '')}.",
        False: f"This attempt at {problem.title.lower()} still reads as a sketch more than a design.",
    }[overall >= 55]
    mid = strengths[0] if strengths else "The structure is not visible yet."
    gap = missing[0] if missing else "The next iteration should add a failure path and an extension point."
    types = ", ".join(signals.class_names[:6]) if signals.class_names else "no named classes yet"
    return (
        f"{opening} Named types: {types}. {mid} "
        f"I would not call this right or wrong — LLD does not work that way. "
        f"The highest-leverage next move: {gap}"
    )
