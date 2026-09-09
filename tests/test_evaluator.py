from backend.catalog import get_problem
from backend.evaluators.deterministic import DeterministicEvaluator
from backend.models import Submission, new_id, now_iso
from backend.reference import parking_lot as parking_src
from pathlib import Path


def _sub(**kwargs) -> Submission:
    base = dict(
        id=new_id("sub"),
        attempt_id="att_x",
        design_notes="",
        class_outline="",
        code="",
        submitted_at=now_iso(),
    )
    base.update(kwargs)
    return Submission(**base)


def test_empty_is_low():
    ev = DeterministicEvaluator().evaluate(get_problem("parking-lot"), _sub())
    assert ev.overall_score < 25


def test_reference_parking_scores_high():
    code = Path(parking_src.__file__).read_text()
    notes = (
        "Assumptions: one garage, three spot types. "
        "ParkingLot orchestrates; Ticket is the receipt; PricingStrategy is swappable later "
        "instead of a switch in check_out. Occupancy counters update on entry/exit. "
        "Limitation: no floors, no concurrent gates."
    )
    ev = DeterministicEvaluator().evaluate(
        get_problem("parking-lot"),
        _sub(design_notes=notes, code=code),
    )
    assert ev.overall_score >= 70
    assert ev.deterministic_ran
    passed = {f.rule_id for f in ev.findings if f.passed}
    assert "entities" in passed
    assert "pricing" in passed


def test_vending_notes_without_code_still_grade():
    notes = (
        "State pattern: Idle / HasMoney / Dispensing. Inventory owns slot stock. "
        "Inserted amount lives on the machine. Out of stock and insufficient funds are errors. "
        "I am not doing exact coin change because denominations are out of scope. "
        "Trade-off: extra classes vs a boolean — booleans will rot when we add refund."
    )
    outline = "VendingMachine\nInventory\nProduct\nTransaction\nIdleState\nHasMoneyState"
    ev = DeterministicEvaluator().evaluate(
        get_problem("vending-machine"),
        _sub(design_notes=notes, class_outline=outline),
    )
    assert ev.overall_score >= 55
    assert any(f.rule_id == "state" and f.passed for f in ev.findings)
