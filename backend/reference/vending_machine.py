"""
Vending Machine - LLD practice problem
Demonstrates: State pattern (Idle -> HasMoney -> Dispensing -> Idle)
and slot-based inventory tracking.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Product:
    product_id: str
    name: str
    price: float


class OutOfStockError(Exception):
    pass


class InsufficientFundsError(Exception):
    pass


class InvalidStateError(Exception):
    pass


@dataclass
class Inventory:
    slots: dict[str, Product] = field(default_factory=dict)
    stock_levels: dict[str, int] = field(default_factory=dict)

    def add_stock(self, slot_id: str, product: Product, quantity: int) -> None:
        self.slots[slot_id] = product
        self.stock_levels[slot_id] = self.stock_levels.get(slot_id, 0) + quantity

    def is_in_stock(self, slot_id: str) -> bool:
        return self.stock_levels.get(slot_id, 0) > 0

    def decrement(self, slot_id: str) -> None:
        self.stock_levels[slot_id] -= 1


@dataclass
class Transaction:
    slot_id: str
    product_name: str
    amount_paid: float
    change_returned: float
    timestamp: datetime = field(default_factory=datetime.now)


# ---- State pattern ----

class VendingMachineState(ABC):
    """Each state decides which actions are legal from here."""

    @abstractmethod
    def insert_coin(self, machine: "VendingMachine", amount: float) -> None:
        ...

    @abstractmethod
    def select_product(self, machine: "VendingMachine", slot_id: str) -> Transaction:
        ...


class IdleState(VendingMachineState):
    def insert_coin(self, machine: "VendingMachine", amount: float) -> None:
        machine.inserted_amount += amount
        machine.set_state(HasMoneyState())

    def select_product(self, machine: "VendingMachine", slot_id: str) -> Transaction:
        raise InvalidStateError("Insert money before selecting a product")


class HasMoneyState(VendingMachineState):
    def insert_coin(self, machine: "VendingMachine", amount: float) -> None:
        machine.inserted_amount += amount

    def select_product(self, machine: "VendingMachine", slot_id: str) -> Transaction:
        machine.set_state(DispensingState())
        return machine.dispense(slot_id)


class DispensingState(VendingMachineState):
    def insert_coin(self, machine: "VendingMachine", amount: float) -> None:
        raise InvalidStateError("Cannot insert coins while dispensing")

    def select_product(self, machine: "VendingMachine", slot_id: str) -> Transaction:
        raise InvalidStateError("Already dispensing an item")


class VendingMachine:
    def __init__(self, inventory: Inventory):
        self.inventory = inventory
        self.inserted_amount: float = 0.0
        self._state: VendingMachineState = IdleState()
        self.transaction_log: list[Transaction] = []

    def set_state(self, state: VendingMachineState) -> None:
        self._state = state

    def insert_coin(self, amount: float) -> None:
        self._state.insert_coin(self, amount)

    def select_product(self, slot_id: str) -> Transaction:
        return self._state.select_product(self, slot_id)

    def dispense(self, slot_id: str) -> Transaction:
        """Called by HasMoneyState. Validates stock and funds, then resets to Idle."""
        if not self.inventory.is_in_stock(slot_id):
            self.set_state(IdleState())
            raise OutOfStockError(f"Slot {slot_id} is out of stock")

        product = self.inventory.slots[slot_id]
        if self.inserted_amount < product.price:
            self.set_state(IdleState())
            raise InsufficientFundsError(
                f"Need {product.price}, only {self.inserted_amount} inserted"
            )

        self.inventory.decrement(slot_id)
        change = round(self.inserted_amount - product.price, 2)

        transaction = Transaction(
            slot_id=slot_id,
            product_name=product.name,
            amount_paid=self.inserted_amount,
            change_returned=change,
        )
        self.transaction_log.append(transaction)

        self.inserted_amount = 0.0
        self.set_state(IdleState())
        return transaction

    def stock_report(self) -> dict[str, int]:
        """Exact remaining stock per slot."""
        return dict(self.inventory.stock_levels)


if __name__ == "__main__":
    inv = Inventory()
    inv.add_stock("A1", Product("P1", "Coke", 25.0), quantity=3)
    inv.add_stock("A2", Product("P2", "Chips", 20.0), quantity=1)

    vm = VendingMachine(inv)

    vm.insert_coin(30.0)
    tx = vm.select_product("A1")
    print(f"Dispensed {tx.product_name}, change = {tx.change_returned}")
    print("Stock after purchase:", vm.stock_report())

    vm.insert_coin(20.0)
    tx2 = vm.select_product("A2")
    print(f"Dispensed {tx2.product_name}, change = {tx2.change_returned}")

    try:
        vm.insert_coin(20.0)
        vm.select_product("A2")  # now out of stock
    except OutOfStockError as e:
        print("Expected error:", e)

    print("Final stock:", vm.stock_report())
