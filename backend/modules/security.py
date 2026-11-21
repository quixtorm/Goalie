"""Minimal security layer (demo).

Step-up PIN: required ONLY for actions that release protected money or commit the user:
  use a goal, early goal close, "proceed anyway" after the Guardian, credit application.
- POST /auth/step-up {pin} -> short-lived token (5 min). 3 wrong PINs -> 60 s lock.
- The server rejects protected actions without a valid token (401).
- Every protected action records a security event and a bell notification with "Отменить" for 24 h (demo clock).

Demo only: the PIN is a fixed demo value (env DEMO_STEP_UP_PIN, default 1234). In production this would be the
user's real PIN/biometrics verified by the bank's auth service, tokens bound to the session/device.
"""
from __future__ import annotations

import hmac
import os
import secrets
import time
from datetime import timedelta

import calc
from calc import CalcError
from modules import budget, credits, goals, guardian
from state import State, new_id
from texts import disp, loc, msg, tr

PIN = os.getenv("DEMO_STEP_UP_PIN", "1234")
MAX_ATTEMPTS = 3
LOCK_SECONDS = 60
TOKEN_TTL_SECONDS = 5 * 60
HOLD_HOURS = 24


class StepUpRequired(Exception):
    """Protected action without a valid step-up token -> 401."""


class StepUpLocked(Exception):
    def __init__(self, retry_after: int):
        super().__init__(retry_after)
        self.retry_after = retry_after


class WrongPin(Exception):
    def __init__(self, attempts_left: int):
        super().__init__(attempts_left)
        self.attempts_left = attempts_left


def _su(s: State) -> dict:
    return s.step_up


def step_up(s: State, pin: str) -> dict:
    su = _su(s)
    now = time.monotonic()
    if su["locked_until"] > now:
        raise StepUpLocked(int(su["locked_until"] - now) + 1)
    if not hmac.compare_digest(str(pin), PIN):
        su["fails"] += 1
        if su["fails"] >= MAX_ATTEMPTS:
            su["fails"] = 0
            su["locked_until"] = now + LOCK_SECONDS
            raise StepUpLocked(LOCK_SECONDS)
        raise WrongPin(MAX_ATTEMPTS - su["fails"])
    su["fails"] = 0
    token = secrets.token_urlsafe(24)
    su["tokens"] = {t: exp for t, exp in su["tokens"].items() if exp > now}  # drop expired
    su["tokens"][token] = now + TOKEN_TTL_SECONDS
    return {"token": token, "expires_in": TOKEN_TTL_SECONDS}


def require(s: State, token: str | None) -> None:
    exp = _su(s)["tokens"].get(token or "")
    if not exp or exp <= time.monotonic():
        raise StepUpRequired()


# ---------- protected actions (each records an undoable security event) ----------
def _record(s: State, kind: str, amount: int, name, data: dict) -> dict:
    ev = {"id": new_id("sec"), "kind": kind, "amount": amount, "name": name, "data": data,
          "created_at": s.clock, "status": "active"}
    s.security_events.append(ev)
    return ev


def use_goal(s: State, goal_id: str) -> dict:
    g = goals.get(s, goal_id)
    before = {"saved": g.saved, "bonus": g.accrued_bonus, "status": g.status, "priority": g.priority}
    res = goals.use(s, goal_id)
    _record(s, "use", res["payout"], loc(g), {"goal_id": goal_id, **before, "payout": res["payout"]})
    return res


def close_goal(s: State, goal_id: str) -> dict:
    g = goals.get(s, goal_id)
    res = goals.start_close(s, goal_id)
    _record(s, "close", g.saved, loc(g), {"goal_id": goal_id})
    return res


def proceed(s: State, stop_id: str) -> dict:
    stop = s.stops.get(stop_id)
    if not stop:
        raise KeyError(tr("err_purchase_not_found"))
    src = s.goals.get(stop.source_id) or s.obligations.get(stop.source_id)
    before = {"disciplined": getattr(src, "disciplined", None)}
    res = guardian.resolve(s, stop_id, "proceed", confirm=True)
    _record(s, "proceed", stop.amount, loc(src), {"stop_id": stop_id, "source_id": stop.source_id,
                                                  "source_kind": stop.source_kind, **before})
    return res


def apply_credit(s: State, product_id: str, amount: int, months: int, confirm: bool) -> dict:
    res = credits.apply(s, product_id, amount, months, confirm)
    _record(s, "credit", amount, res["name"], {"app_id": res["id"]})
    return res


# ---------- notifications + 24 h cancel ----------
def active_events(s: State) -> list[dict]:
    limit = timedelta(hours=HOLD_HOURS)
    return [e for e in s.security_events if e["status"] == "active" and s.clock < e["created_at"] + limit]


def notice_text(e: dict) -> dict:
    return msg(f"sec_{e['kind']}", amount_sum=e["amount"], name=e["name"])


def undo(s: State, event_id: str) -> dict:
    e = next((x for x in s.security_events if x["id"] == event_id), None)
    if not e or e not in active_events(s):
        raise CalcError(tr("err_sec_expired"))
    d = e["data"]
    if e["kind"] == "use":
        g = goals.get(s, d["goal_id"])
        if s.main_balance < d["payout"]:
            raise CalcError(tr("err_money_insufficient"))
        s.main_balance -= d["payout"]
        g.saved, g.accrued_bonus, g.status = d["saved"], d["bonus"], d["status"]
        budget.renumber(s)
        if d["priority"]:
            g.priority = d["priority"]
            budget.renumber(s)
        s.add_tx(msg("tx_undo", name=e["name"]), -d["payout"], internal=True)
    elif e["kind"] == "close":
        g = goals.get(s, d["goal_id"])
        if g.status == "closing":
            g.status, g.close_ready_at = "active", None
            g.priority = len(budget.active_goals(s)) + 1
            budget.renumber(s)
    elif e["kind"] == "proceed":
        if d["source_kind"] == "goal":
            g = s.goals[d["source_id"]]
            g.saved += e["amount"]
            if d["disciplined"] is not None:
                g.disciplined = d["disciplined"]
        else:
            s.obligations[d["source_id"]].reserved += e["amount"]
        s.add_tx(msg("tx_undo", name=e["name"]), e["amount"], source=d["source_id"])
    elif e["kind"] == "credit":
        for a in s.credit_applications:
            if a["id"] == d["app_id"]:
                a["status"] = "cancelled"
    e["status"] = "cancelled"
    return {"status": "cancelled", "message": tr(f"sec_undone_{e['kind']}", amount_sum=e["amount"], name=e["name"])}


def acknowledge(s: State, event_id: str) -> None:
    for e in s.security_events:
        if e["id"] == event_id and e["status"] == "active":
            e["status"] = "acknowledged"
