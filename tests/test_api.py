from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.store import AttemptRepository
from backend import main as mainmod
from backend.service import ForgeService


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    repo = AttemptRepository(tmp_path / "t.db")
    monkeypatch.setattr(mainmod, "repo", repo)
    monkeypatch.setattr(mainmod, "service", ForgeService(repo))
    return TestClient(app)


def test_list_problems(client: TestClient):
    res = client.get("/api/problems")
    assert res.status_code == 200
    ids = {p["id"] for p in res.json()}
    assert {"parking-lot", "vending-machine", "elevator"} <= ids


def test_submit_flow_and_history(client: TestClient):
    start = client.post("/api/attempts", json={"problem_id": "parking-lot"})
    assert start.status_code == 200
    att = start.json()["id"]
    sub = client.post(
        f"/api/attempts/{att}/submissions",
        json={
            "design_notes": (
                "Vehicle, ParkingSpot, Ticket, ParkingLot. "
                "PricingStrategy so fees can change later instead of a switch. "
                "Occupancy counters. Lot full is an error. Assumption: one floor."
            ),
            "class_outline": "ParkingLot\nParkingSpot\nVehicle\nTicket\nPricingStrategy",
            "code": "class ParkingLot:\n    def check_in(self, vehicle): ...\n",
        },
    )
    assert sub.status_code == 200
    body = sub.json()
    assert body["status"] == "evaluated"
    ev = body["submissions"][-1]["evaluation"]
    assert ev["overall_score"] >= 40
    hist = client.get("/api/history").json()
    assert hist[0]["id"] == att


def test_reject_empty_submit(client: TestClient):
    att = client.post("/api/attempts", json={"problem_id": "elevator"}).json()["id"]
    res = client.post(f"/api/attempts/{att}/submissions", json={})
    assert res.status_code == 400
