"""In-memory store + demo clock. One RLock guards every mutation."""
from __future__ import annotations

import copy
import threading
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@dataclass
class Goal:
    id: str
    name: str
    amount: int
    saved: int
    percent: int
    disciplined: bool = True
    planned_months_left: int = 0
    accrued_bonus: int = 0
    status: str = "active"  # active | completed | used | closing | closed
    close_ready_at: datetime | None = None
    priority: int = 0  # 1 = highest; 0 = not active (completed/closed)
    names: dict[str, str] | None = None  # optional per-language display names (seed data)


@dataclass
class Obligation:
    id: str
    name: str
    amount: int
    due_date: date
    reserved: int = 0
    paid: bool = False
    monthly: bool = False
    names: dict[str, str] | None = None


@dataclass
class Stop:
    """A purchase the guardian stopped (or put on cooling-off)."""
    id: str
    source_id: str
    source_kind: str  # goal | obligation
    amount: int
    mcc: str
    merchant: str
    note: str
    category: str
    status: str = "open"  # open | cooling | resolved
    resolution: str | None = None
    ready_at: datetime | None = None
    numbers: dict[str, Any] = field(default_factory=dict)


@dataclass
class Proposal:
    id: str
    kind: str
    title: str
    text: str
    options: list[dict[str, Any]]  # [{key, label, action:{type, params}}]
    condition_key: str
    numbers: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending | confirmed | rejected | resolved
    origin: str = "agent"  # agent | chat
    created_at: datetime | None = None
    result: str | None = None


@dataclass
class State:
    clock: datetime
    income_history: list[int]
    main_balance: int
    next_income_date: date
    goals: dict[str, Goal] = field(default_factory=dict)
    obligations: dict[str, Obligation] = field(default_factory=dict)
    stops: dict[str, Stop] = field(default_factory=dict)
    proposals: dict[str, Proposal] = field(default_factory=dict)
    transactions: list[dict[str, Any]] = field(default_factory=list)
    last_salary: dict[str, Any] | None = None

    @property
    def today(self) -> date:
        return self.clock.date()

    def add_tx(self, title: str | dict, amount: int, source: str = "main", mcc: str | None = None,
               internal: bool = False) -> None:
        self.transactions.insert(0, {
            "id": new_id("tx"), "date": self.today.isoformat(), "title": title,
            "amount": amount, "source": source, "mcc": mcc, "internal": internal,
        })
        del self.transactions[50:]


class Store:
    def __init__(self, seed_factory):
        self._seed_factory = seed_factory
        self.lock = threading.RLock()
        self.state: State = seed_factory()

    def reset(self) -> None:
        with self.lock:
            self.state = self._seed_factory()


def clone(state: State) -> State:
    return copy.deepcopy(state)
