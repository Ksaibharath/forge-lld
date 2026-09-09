from backend.reference.parking_lot import (
    HourlyFlatRatePricing,
    ParkingFullError,
    ParkingLot,
    ParkingSpot,
    SpotType,
    Vehicle,
    VehicleType,
)


def _lot(compact=2, large=1, bike=1) -> ParkingLot:
    spots = (
        [ParkingSpot(f"C{i}", SpotType.COMPACT) for i in range(compact)]
        + [ParkingSpot(f"L{i}", SpotType.LARGE) for i in range(large)]
        + [ParkingSpot(f"B{i}", SpotType.BIKE) for i in range(bike)]
    )
    return ParkingLot(spots, HourlyFlatRatePricing())


def test_occupancy_tracks_without_recount():
    lot = _lot()
    t = lot.check_in(Vehicle("KA-1", VehicleType.CAR))
    report = lot.occupancy_report()
    assert report["CAR"]["occupied"] == 1
    assert report["CAR"]["available"] == 1
    lot.check_out(t.ticket_id)
    assert lot.occupancy_report()["CAR"]["occupied"] == 0


def test_full_lot_rejects():
    lot = _lot(compact=1, large=0, bike=0)
    lot.check_in(Vehicle("KA-1", VehicleType.CAR))
    try:
        lot.check_in(Vehicle("KA-2", VehicleType.CAR))
        assert False, "should be full"
    except ParkingFullError:
        pass


def test_checkout_sets_fee():
    lot = _lot()
    t = lot.check_in(Vehicle("KA-1", VehicleType.BIKE))
    closed = lot.check_out(t.ticket_id)
    assert closed.fee == 5.0
    assert closed.exit_time is not None


def test_unknown_ticket():
    lot = _lot()
    try:
        lot.check_out("nope")
        assert False
    except ValueError:
        pass
