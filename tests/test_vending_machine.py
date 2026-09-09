from backend.reference.vending_machine import (
    InsufficientFundsError,
    InvalidStateError,
    Inventory,
    OutOfStockError,
    Product,
    VendingMachine,
)


def _vm(qty_a2=1) -> VendingMachine:
    inv = Inventory()
    inv.add_stock("A1", Product("P1", "Coke", 25.0), 3)
    inv.add_stock("A2", Product("P2", "Chips", 20.0), qty_a2)
    return VendingMachine(inv)


def test_happy_path_decrements_stock_and_logs():
    vm = _vm()
    vm.insert_coin(30)
    tx = vm.select_product("A1")
    assert tx.change_returned == 5.0
    assert vm.stock_report()["A1"] == 2
    assert len(vm.transaction_log) == 1


def test_select_before_pay_is_illegal():
    vm = _vm()
    try:
        vm.select_product("A1")
        assert False
    except InvalidStateError:
        pass


def test_out_of_stock():
    vm = _vm(qty_a2=0)
    vm.insert_coin(20)
    try:
        vm.select_product("A2")
        assert False
    except OutOfStockError:
        pass


def test_insufficient_funds():
    vm = _vm()
    vm.insert_coin(5)
    try:
        vm.select_product("A1")
        assert False
    except InsufficientFundsError:
        pass
