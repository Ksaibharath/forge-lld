"""
Parking Lot - LLD practice problem
Demonstrates: inheritance, Strategy pattern (pricing), Factory-ish spot allocation,
and live occupancy tracking by vehicle type.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class VehicleType(Enum):
    CAR = "CAR"
    BIKE = "BIKE"
    TRUCK = "TRUCK"


class SpotType(Enum):
    COMPACT = "COMPACT"
    LARGE = "LARGE"
    BIKE = "BIKE"


# Which spot type each vehicle type is allowed to use.
VEHICLE_TO_SPOT: dict[VehicleType, SpotType] = {
    VehicleType.CAR: SpotType.COMPACT,
    VehicleType.TRUCK: SpotType.LARGE,
    VehicleType.BIKE: SpotType.BIKE,
}


@dataclass
class Vehicle:
    license_plate: str
    vehicle_type: VehicleType


@dataclass
class ParkingSpot:
    spot_id: str
    spot_type: SpotType
    is_occupied: bool = False
    current_vehicle: Optional[Vehicle] = None

    def park(self, vehicle: Vehicle) -> None:
        if self.is_occupied:
            raise ValueError(f"Spot {self.spot_id} is already occupied")
        self.is_occupied = True
        self.current_vehicle = vehicle

    def vacate(self) -> Vehicle:
        if not self.is_occupied or self.current_vehicle is None:
            raise ValueError(f"Spot {self.spot_id} is already empty")
        vehicle = self.current_vehicle
        self.is_occupied = False
        self.current_vehicle = None
        return vehicle


@dataclass
class Ticket:
    ticket_id: str
    vehicle: Vehicle
    spot: ParkingSpot
    entry_time: datetime
    exit_time: Optional[datetime] = None
    fee: Optional[float] = None


class PricingStrategy(ABC):
    """Strategy pattern: swap pricing logic without touching ParkingLot."""

    @abstractmethod
    def calculate_fee(self, vehicle_type: VehicleType, duration_hours: float) -> float:
        ...


class HourlyFlatRatePricing(PricingStrategy):
    RATES = {
        VehicleType.BIKE: 5.0,
        VehicleType.CAR: 10.0,
        VehicleType.TRUCK: 20.0,
    }

    def calculate_fee(self, vehicle_type: VehicleType, duration_hours: float) -> float:
        rate = self.RATES[vehicle_type]
        # Minimum charge of 1 hour, rounded up.
        billed_hours = max(1, int(duration_hours) + (1 if duration_hours % 1 else 0))
        return round(rate * billed_hours, 2)


class ParkingFullError(Exception):
    pass


class ParkingLot:
    def __init__(self, spots: list[ParkingSpot], pricing_strategy: PricingStrategy):
        self._spots = {spot.spot_id: spot for spot in spots}
        self._pricing_strategy = pricing_strategy
        self._active_tickets: dict[str, Ticket] = {}
        self._ticket_counter = 0

        # Live counters, kept in sync on every entry/exit instead of recomputed.
        self._total_by_type: dict[VehicleType, int] = {vt: 0 for vt in VehicleType}
        self._occupied_by_type: dict[VehicleType, int] = {vt: 0 for vt in VehicleType}
        for spot in spots:
            for vt, st in VEHICLE_TO_SPOT.items():
                if st == spot.spot_type:
                    self._total_by_type[vt] += 1

    def _find_free_spot(self, vehicle_type: VehicleType) -> Optional[ParkingSpot]:
        required_type = VEHICLE_TO_SPOT[vehicle_type]
        for spot in self._spots.values():
            if spot.spot_type == required_type and not spot.is_occupied:
                return spot
        return None

    def check_in(self, vehicle: Vehicle) -> Ticket:
        spot = self._find_free_spot(vehicle.vehicle_type)
        if spot is None:
            raise ParkingFullError(f"No free {vehicle.vehicle_type.value} spot available")

        spot.park(vehicle)
        self._occupied_by_type[vehicle.vehicle_type] += 1

        self._ticket_counter += 1
        ticket = Ticket(
            ticket_id=f"T-{self._ticket_counter}",
            vehicle=vehicle,
            spot=spot,
            entry_time=datetime.now(),
        )
        self._active_tickets[ticket.ticket_id] = ticket
        return ticket

    def check_out(self, ticket_id: str) -> Ticket:
        ticket = self._active_tickets.get(ticket_id)
        if ticket is None:
            raise ValueError(f"No active ticket: {ticket_id}")

        vehicle = ticket.spot.vacate()
        self._occupied_by_type[vehicle.vehicle_type] -= 1

        ticket.exit_time = datetime.now()
        duration_hours = (ticket.exit_time - ticket.entry_time).total_seconds() / 3600
        ticket.fee = self._pricing_strategy.calculate_fee(vehicle.vehicle_type, duration_hours)

        del self._active_tickets[ticket_id]
        return ticket

    def occupancy_report(self) -> dict[str, dict[str, int]]:
        """Exact counts of vehicles currently parked, by type."""
        return {
            vt.value: {
                "occupied": self._occupied_by_type[vt],
                "total": self._total_by_type[vt],
                "available": self._total_by_type[vt] - self._occupied_by_type[vt],
            }
            for vt in VehicleType
        }


if __name__ == "__main__":
    spots = (
        [ParkingSpot(f"C{i}", SpotType.COMPACT) for i in range(1, 4)]
        + [ParkingSpot(f"L{i}", SpotType.LARGE) for i in range(1, 3)]
        + [ParkingSpot(f"B{i}", SpotType.BIKE) for i in range(1, 3)]
    )
    lot = ParkingLot(spots, HourlyFlatRatePricing())

    t1 = lot.check_in(Vehicle("KA-01-1234", VehicleType.CAR))
    t2 = lot.check_in(Vehicle("KA-02-9999", VehicleType.BIKE))
    lot.check_in(Vehicle("KA-03-5555", VehicleType.TRUCK))

    print("Occupancy after check-ins:", lot.occupancy_report())

    closed = lot.check_out(t1.ticket_id)
    print(f"Checked out {closed.vehicle.license_plate}, fee = {closed.fee}")

    print("Occupancy after one check-out:", lot.occupancy_report())
