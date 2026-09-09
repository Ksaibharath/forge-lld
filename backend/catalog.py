"""Problem catalog. Adding a problem is data — not a new evaluator."""

from __future__ import annotations

from backend.models import Difficulty, ProblemSpec, RubricSignal

_PARKING_SAMPLE_CODE = '''from abc import ABC, abstractmethod
from enum import Enum

class VehicleType(Enum):
    CAR = "CAR"
    BIKE = "BIKE"

class Vehicle:
    def __init__(self, plate, vehicle_type):
        self.plate = plate
        self.vehicle_type = vehicle_type

class ParkingSpot:
    def __init__(self, spot_id, spot_type):
        self.spot_id = spot_id
        self.spot_type = spot_type
        self.vehicle = None

class ParkingLot:
    def __init__(self, spots):
        self.spots = spots

    def park(self, vehicle):
        for s in self.spots:
            if s.vehicle is None:
                s.vehicle = vehicle
                return s.spot_id
        raise Exception("full")
'''

PARKING_LOT = ProblemSpec(
    id="parking-lot",
    title="Design a Parking Lot",
    difficulty=Difficulty.MEDIUM,
    minutes=45,
    summary="Spots, vehicles, tickets, fees — and occupancy you can query without recounting.",
    statement="""Design a parking lot that can handle mixed vehicles and report how full it is at any moment.

A city garage has multiple spot types (compact, large, motorcycle). Cars, bikes, and trucks arrive at a gate, take a ticket, occupy a compatible spot, and pay on the way out. Pricing should be allowed to change later (hourly, event-day surge) without rewriting the lot.

Interviewers care less about a perfect UML poster and more about: where does occupancy live, who owns a spot, and what you would change to add valet parking tomorrow.""",
    functional_requirements=[
        "Admit a vehicle only if a compatible free spot exists; otherwise reject cleanly.",
        "Issue a ticket on entry that can be used to find the spot and compute a fee on exit.",
        "Track live occupancy by vehicle / spot type without scanning every spot on each query.",
        "Support at least three vehicle kinds and matching spot kinds.",
        "Fee calculation must be replaceable (new policy, not a new if-else in the lot).",
        "Vacate the spot and close the ticket on exit.",
    ],
    constraints=[
        "Single garage, in-memory is fine — no database, no microservices.",
        "Do not model payments, ANPR cameras, or a mobile app.",
        "Spot–vehicle compatibility can be a simple mapping, but call out how you would relax it.",
    ],
    considerations=[
        "Separate Vehicle, ParkingSpot, Ticket, and ParkingLot — the lot should orchestrate, not own every field.",
        "Occupancy counters updated on entry/exit beat O(n) recounting.",
        "Pricing as a Strategy (or equivalent policy object) so rates change independently of allocation.",
        "Custom errors for 'lot full' / 'unknown ticket' instead of returning None everywhere.",
        "What happens if two gates check in concurrently is worth a sentence even if you stay single-threaded.",
        "A truck in a compact spot should be impossible at the type level, not a comment.",
    ],
    expected_entities=["Vehicle", "ParkingSpot", "ParkingLot", "Ticket", "VehicleType", "SpotType"],
    expected_patterns=["Strategy", "Enum"],
    expected_apis=["check_in", "check_out", "park", "occupancy"],
    rubric=[
        RubricSignal(
            id="entities",
            label="Core types exist (Lot, Spot, Vehicle, Ticket)",
            weight=1.4,
            keywords=["ticket", "spot", "vehicle", "parking lot", "parkinglot"],
            class_names=["ParkingLot", "ParkingSpot", "Vehicle", "Ticket"],
            missing_feedback="The lot, the spot, the vehicle, and the ticket are different lifetimes. Collapsing them into one class makes occupancy and billing fight each other.",
            present_feedback="You split the obvious nouns into types — that is the right starting grain.",
        ),
        RubricSignal(
            id="occupancy",
            label="Live occupancy by type",
            weight=1.2,
            keywords=["occupancy", "available", "count", "occupied", "capacity"],
            class_names=[],
            missing_feedback="Interviewers will ask 'how many cars are parked right now?' If the answer is 'loop every spot', say so and mention a counter you would keep in sync on entry/exit.",
            present_feedback="You thought about occupancy as a query, not only as park/leave.",
        ),
        RubricSignal(
            id="pricing",
            label="Replaceable pricing / fee policy",
            weight=1.2,
            keywords=["pricing", "strategy", "fee", "rate", "tariff", "policy"],
            class_names=["PricingStrategy", "FeeCalculator", "PricingPolicy"],
            missing_feedback="Fee logic glued inside check-out will be the first thing that rots. Extract a policy object even if it is a flat hourly rate today.",
            present_feedback="Pricing is an extension point — good, that is a classic Strategy use, not decoration.",
        ),
        RubricSignal(
            id="compatibility",
            label="Vehicle–spot compatibility",
            weight=1.0,
            keywords=["compact", "large", "bike", "truck", "compatible", "spot type", "vehicle type"],
            class_names=["VehicleType", "SpotType"],
            missing_feedback="Without types (or an explicit mapping), a truck can sit in a bike stall and the design cannot explain why not.",
            present_feedback="Compatibility is modelled, not hoped for.",
        ),
        RubricSignal(
            id="errors",
            label="Explicit full / invalid-ticket behaviour",
            weight=0.8,
            keywords=["full", "exception", "error", "reject", "invalid ticket"],
            class_names=["ParkingFullError"],
            missing_feedback="Define what happens when the lot is full or the ticket is unknown. Returning None hides the policy.",
            present_feedback="Failure paths are part of the design, not an afterthought.",
        ),
    ],
    sample_outline="""ParkingLot
  check_in(vehicle) -> Ticket
  check_out(ticket_id) -> Ticket
  occupancy_report()
ParkingSpot
  park(vehicle) / vacate()
Vehicle (type, plate)
Ticket (entry time, spot, fee)
PricingStrategy.calculate_fee(...)
""",
    sample_notes="""Assumptions: one garage, three spot types, one vehicle per spot.
Classes: ParkingLot orchestrates; ParkingSpot holds occupation; Ticket is the receipt; PricingStrategy computes the fee so rates can change.
Occupancy: counters per vehicle type, incremented on check-in.
Gaps I know: no floors yet, no concurrency at the gate.
""",
    sample_code=_PARKING_SAMPLE_CODE,
)


VENDING = ProblemSpec(
    id="vending-machine",
    title="Design a Vending Machine",
    difficulty=Difficulty.MEDIUM,
    minutes=40,
    summary="Inventory, money, and a state machine that refuses illegal actions.",
    statement="""Design a vending machine that sells packaged items from numbered slots.

A customer inserts money, picks a slot, and either receives the item plus change or a clear error (out of stock, not enough money). The machine should not accept a second selection while it is dispensing, and an operator should be able to restock without rewriting the purchase flow.

The interesting part is not the coin math. It is illegal transitions — selecting before paying, paying while dispensing — and where stock actually lives.""",
    functional_requirements=[
        "Slots hold a product and a stock count; selling decrements stock.",
        "Reject out-of-stock and insufficient-funds with explicit errors.",
        "Track inserted money for the current transaction and return change.",
        "Disallow illegal actions depending on state (idle / has-money / dispensing).",
        "Keep a transaction log of successful purchases.",
        "Allow restock without changing purchase code.",
    ],
    constraints=[
        "No card payments, no networking, no UI framework.",
        "A single machine, in-memory inventory.",
        "You may ignore exact coin denomination / change-making algorithms.",
    ],
    considerations=[
        "State pattern (or an equivalent explicit state object) beats a tangle of booleans.",
        "Inventory is a separate object: slot → product, slot → count.",
        "Money already inserted should have a defined fate on failure (keep, refund, stay in HasMoney).",
        "Dispense should be the only place stock decrements — one write path.",
        "Admin restock vs customer select are different actors; do not put both on one god method.",
    ],
    expected_entities=["VendingMachine", "Inventory", "Product", "Transaction"],
    expected_patterns=["State"],
    expected_apis=["insert_coin", "select_product", "dispense", "stock"],
    rubric=[
        RubricSignal(
            id="state",
            label="Explicit purchase states",
            weight=1.5,
            keywords=["state", "idle", "has money", "dispensing", "state pattern"],
            class_names=["VendingMachineState", "IdleState", "HasMoneyState", "DispensingState"],
            missing_feedback="A boolean `has_money` will sprout five friends. Name the states and put illegal actions in the wrong state, not in a 40-line if.",
            present_feedback="States are first-class — that is the heart of this problem.",
        ),
        RubricSignal(
            id="inventory",
            label="Slot-based inventory",
            weight=1.2,
            keywords=["inventory", "slot", "stock", "quantity"],
            class_names=["Inventory", "Product"],
            missing_feedback="Stock needs a home (slot → count). Do not bury an integer inside the machine next to the coin balance.",
            present_feedback="Inventory is its own object with a single decrement path.",
        ),
        RubricSignal(
            id="money",
            label="Inserted amount + change",
            weight=1.0,
            keywords=["inserted", "change", "price", "coin", "refund"],
            class_names=[],
            missing_feedback="Say where inserted money lives and what happens to it when stock is gone.",
            present_feedback="The current transaction's cash is modelled.",
        ),
        RubricSignal(
            id="txlog",
            label="Purchase / transaction history",
            weight=0.8,
            keywords=["transaction", "log", "history", "audit"],
            class_names=["Transaction"],
            missing_feedback="A Transaction record is cheap and is the audit trail interviewers expect if they ask 'what sold today?'",
            present_feedback="Successful purchases are recorded, not only mutated into stock.",
        ),
        RubricSignal(
            id="errors",
            label="Out of stock / insufficient funds",
            weight=0.8,
            keywords=["out of stock", "insufficient", "error", "exception"],
            class_names=["OutOfStockError", "InsufficientFundsError", "InvalidStateError"],
            missing_feedback="Make the two failure modes visible types or documented errors — they are part of the API.",
            present_feedback="Failure modes are explicit.",
        ),
    ],
    sample_outline="""VendingMachine (inserted_amount, state)
  insert_coin(amount)
  select_product(slot_id) -> Transaction
Inventory (slots, stock_levels)
Product, Transaction
IdleState / HasMoneyState / DispensingState
""",
    sample_notes="""State machine: Idle → HasMoney → Dispensing → Idle.
Inventory owns slot maps. Machine owns cash-in-flight and the current state object.
Illegal: select in Idle, insert during Dispensing.
Not doing exact change-making.
""",
    sample_code='''from abc import ABC, abstractmethod

class VendingMachineState(ABC):
    @abstractmethod
    def insert_coin(self, machine, amount): ...
    @abstractmethod
    def select_product(self, machine, slot_id): ...

class IdleState(VendingMachineState):
    def insert_coin(self, machine, amount):
        machine.inserted_amount += amount
        machine.state = "has_money"
    def select_product(self, machine, slot_id):
        raise Exception("insert money first")

class VendingMachine:
    def __init__(self):
        self.inserted_amount = 0
        self.stock = {}
        self.state = "idle"
''',
)


ELEVATOR = ProblemSpec(
    id="elevator",
    title="Design an Elevator System",
    difficulty=Difficulty.HARD,
    minutes=50,
    summary="Cars, hall calls, and a scheduler you can swap when the building grows.",
    statement="""Design the software for a building with one or more elevator cars.

People press up/down in the hallway and pick a destination inside the car. Cars move, open doors, and should not move with the door open. When a second car is added, pickup assignment should not require rewriting the car itself.

This problem is a trap for god objects. If `ElevatorSystem` both moves motors and decides which car should take a hall call, you will feel it when the interviewer adds 'peak hour: prefer the nearest idle car going that direction.'""",
    functional_requirements=[
        "Model cars with a floor, a direction, and a door state.",
        "Accept hall calls (floor + direction) and car destination requests.",
        "A scheduling policy assigns a hall call to a car.",
        "Doors open/close; the car must not travel with the door open.",
        "Support at least two cars without duplicating request logic.",
        "Idle cars and moving cars behave differently when a new request arrives.",
    ],
    constraints=[
        "Ignore hardware, weight sensors, and fire service beyond a one-line mention.",
        "Discrete floors, discrete ticks or events — no real-time OS.",
        "A simple nearest-car or SCAN policy is enough if it is swappable.",
    ],
    considerations=[
        "Separate Elevator (the car) from ElevatorController (orchestration) from SchedulingStrategy.",
        "Direction and DoorState as enums — not magic strings.",
        "Hall request vs cabin request are different types; they have different cancellation rules.",
        "State of a car (idle, moving, boarding) determines what requests it will accept now.",
        "Scheduler as Strategy: nearest-idle today, direction-aware SCAN tomorrow.",
        "Safety invariant: moving ∧ door_open is unreachable.",
    ],
    expected_entities=["Elevator", "ElevatorController", "Request", "SchedulingStrategy"],
    expected_patterns=["Strategy", "State", "Enum"],
    expected_apis=["request", "hall_call", "step", "move", "open_door"],
    rubric=[
        RubricSignal(
            id="split",
            label="Car vs controller vs scheduler",
            weight=1.5,
            keywords=["controller", "scheduler", "strategy", "dispatcher"],
            class_names=["Elevator", "ElevatorController", "SchedulingStrategy", "Dispatcher"],
            missing_feedback="If the car both moves and assigns hall calls, adding a second car copies the wrong code. Pull scheduling out.",
            present_feedback="Orchestration is not stuffed inside the cabin — that will age well.",
        ),
        RubricSignal(
            id="requests",
            label="Hall vs cabin requests",
            weight=1.1,
            keywords=["hall", "destination", "request", "up", "down", "direction"],
            class_names=["Request", "HallCall", "Direction"],
            missing_feedback="A hallway 'up' is not the same object as 'go to floor 12'. Different producers, different cancel rules.",
            present_feedback="Request types are distinguished.",
        ),
        RubricSignal(
            id="safety",
            label="Door / motion safety",
            weight=1.0,
            keywords=["door", "open", "close", "safety", "idle", "moving"],
            class_names=["DoorState", "ElevatorState"],
            missing_feedback="State the invariant: the car does not change floor while the door is open. Encode it in state transitions.",
            present_feedback="Door and motion are not independent booleans.",
        ),
        RubricSignal(
            id="multi",
            label="More than one car",
            weight=1.0,
            keywords=["multiple", "cars", "fleet", "assign", "nearest"],
            class_names=[],
            missing_feedback="Even a one-car MVP should say how a second car would be assigned work.",
            present_feedback="The design does not assume a single cabin.",
        ),
        RubricSignal(
            id="policy",
            label="Swappable scheduling policy",
            weight=0.9,
            keywords=["scan", "nearest", "strategy", "policy", "algorithm"],
            class_names=["SchedulingStrategy"],
            missing_feedback="Hard-coding 'pick elevator 0' is fine only if you name it as a policy you would replace.",
            present_feedback="Scheduling is a policy object.",
        ),
    ],
    sample_outline="""Elevator (floor, direction, door, stops)
ElevatorController (cars, scheduler)
SchedulingStrategy.assign(hall_call, cars) -> Elevator
HallCall / CabinRequest
""",
    sample_notes="""One controller, N cars. Scheduler is a Strategy (nearest idle for now).
Car state: Idle / Moving / Boarding. Cannot move while door open.
HallCall(floor, direction) vs CabinRequest(floor).
""",
    sample_code='''from enum import Enum
from abc import ABC, abstractmethod

class Direction(Enum):
    UP = 1
    DOWN = -1
    IDLE = 0

class Elevator:
    def __init__(self, car_id):
        self.id = car_id
        self.floor = 0
        self.direction = Direction.IDLE
        self.door_open = False
        self.stops = set()

class SchedulingStrategy(ABC):
    @abstractmethod
    def assign(self, call, cars): ...

class ElevatorController:
    def __init__(self, cars, scheduler):
        self.cars = cars
        self.scheduler = scheduler
''',
)


PROBLEMS: dict[str, ProblemSpec] = {
    p.id: p for p in (PARKING_LOT, VENDING, ELEVATOR)
}


def list_problems() -> list[ProblemSpec]:
    return list(PROBLEMS.values())


def get_problem(problem_id: str) -> ProblemSpec:
    if problem_id not in PROBLEMS:
        raise KeyError(problem_id)
    return PROBLEMS[problem_id]


def problem_card(p: ProblemSpec) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "difficulty": p.difficulty.value,
        "minutes": p.minutes,
        "summary": p.summary,
        "expected_patterns": p.expected_patterns,
    }


def problem_public(p: ProblemSpec) -> dict:
    """Statement for the learner — no sample solution, no hidden rubric weights."""
    return {
        **problem_card(p),
        "statement": p.statement,
        "functional_requirements": p.functional_requirements,
        "constraints": p.constraints,
        "considerations_teaser": [
            "Name the core types and who owns what.",
            "Call out one extension point (a policy you would swap later).",
            "Define the failure cases, not only the happy path.",
        ],
    }
