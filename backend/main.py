"""FastAPI routes. No math here — everything goes through modules/ and calc.py."""
from __future__ import annotations

import logging
import os
import time
from collections import deque
from datetime import date
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import agent  # noqa: E402
import calc  # noqa: E402
import fallback  # noqa: E402
import mcc as mcc_mod  # noqa: E402
from calc import CalcError  # noqa: E402
from mock_data import seed  # noqa: E402
from modules import budget, goals, guardian, obligations, proposals  # noqa: E402
from state import Store  # noqa: E402
from texts import render, set_lang, tr  # noqa: E402

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("api")

STORE = Store(seed)
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

app = FastAPI(title="SmartGoal demo", docs_url="/docs" if DEMO_MODE else None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Lang"],
)


class LangMiddleware:
    """Pure ASGI: sets the request language (X-Lang: ru|uz) before the endpoint and error handlers run."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            raw = dict(scope.get("headers") or []).get(b"x-lang", b"ru").decode("latin-1", "ignore").strip().lower()
            set_lang(raw)
        await self.app(scope, receive, send)


app.add_middleware(LangMiddleware)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.exception_handler(CalcError)
async def calc_error(_: Request, e: CalcError):
    return JSONResponse(status_code=422, content={"detail": str(e)})


@app.exception_handler(KeyError)
async def not_found(_: Request, e: KeyError):
    return JSONResponse(status_code=404, content={"detail": e.args[0] if e.args else tr("err_not_found")})


@app.exception_handler(RequestValidationError)
async def bad_input(_: Request, e: RequestValidationError):
    fields = sorted({str(err["loc"][-1]) for err in e.errors() if err.get("loc")})
    return JSONResponse(status_code=422, content={"detail": tr("err_bad_input"), "fields": fields})


@app.exception_handler(Exception)
async def internal(_: Request, e: Exception):
    log.error("Unhandled error: %s", type(e).__name__)
    return JSONResponse(status_code=500, content={"detail": tr("err_internal")})


# ---- input models (bounded, no unknown fields) ----
Money = Field(gt=0, le=calc.MAX_AMOUNT)
Name = Field(min_length=1, max_length=100)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class GoalIn(Strict):
    name: str = Name
    amount: int = Money
    percent: int = Field(ge=calc.MIN_PERCENT, le=calc.MAX_TOTAL_PERCENT)


class ObligationIn(Strict):
    name: str = Name
    amount: int = Money
    due_date: date
    monthly: bool = False


class ConfirmIn(Strict):
    confirm: bool = False


class SpendIn(Strict):
    source_id: str = Field(min_length=1, max_length=40)
    amount: int = Money
    mcc: str = Field(pattern=r"^\d{4}$")
    merchant: str = Name
    note: str = Field(default="", max_length=100)


class ResolveIn(Strict):
    option: Literal["cover_from_main", "cooling", "proceed", "decline"]
    confirm: bool = False


class ProposalIn(Strict):
    option: str | None = Field(default=None, max_length=40)


class ChatTurn(Strict):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatIn(Strict):
    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    lang: Literal["ru", "uz"] = "ru"


class ReorderIn(Strict):
    ids: list[str] = Field(min_length=1, max_length=calc.MAX_SUBCARDS)


class SalaryIn(Strict):
    amount: int = Money


class TransferIn(Strict):
    amount: int = Money
    source: str = Field(min_length=1, max_length=60)


class SkipIn(Strict):
    hours: int = Field(ge=1, le=720)


# ---- views ----
def state_view() -> dict:
    s = STORE.state
    b = budget.basis(s)
    pend = [p for p in s.proposals.values() if p.status == "pending"]
    today_tx = [t for t in s.transactions if t["date"] == s.today.isoformat() and not t.get("internal")]
    goal_list = sorted((g for g in s.goals.values() if g.status in ("active", "completed", "closing")),
                       key=lambda g: (g.priority or 99, g.id))
    return {
        "today": s.today.isoformat(),
        "clock": s.clock.isoformat(),
        "main": budget.cashflow_view(s),
        "total_balance": s.main_balance + sum(g.saved for g in s.goals.values())
        + sum(o.reserved for o in s.obligations.values() if not o.paid),
        "today_summary": {"spent": -sum(t["amount"] for t in today_tx if t["amount"] < 0),
                          "income": sum(t["amount"] for t in today_tx if t["amount"] > 0),
                          "income_by_type": {ty: sum(t["amount"] for t in today_tx
                                                     if t["amount"] > 0 and t.get("type") == ty)
                                             for ty in calc.INCOME_TYPES},
                          "daily_baseline": calc.DAILY_SPEND_BASELINE},
        "proposals_pending": [proposals.view(p) for p in sorted(pend, key=lambda p: p.created_at, reverse=True)],
        "last_salary": s.last_salary,
        "income": {**fallback.income_view(s), "worst": b.worst, "avg": calc.round_money(b.avg),
                   "salary_history": calc.salary_amounts(s.incomes)[-calc.ANNUAL_WINDOW_MONTHS:],
                   "next_income_date": s.next_income_date.isoformat()},
        "goals": [goals.view(s, g) for g in goal_list],
        "used_percent": budget.used_percent(s),
        "limits": {"max_goals": calc.MAX_SUBCARDS, "max_total_percent": calc.MAX_TOTAL_PERCENT,
                   "discipline_rate": calc.DISCIPLINE_RATE, "base_rate": calc.BASE_RATE,
                   "cooldown_hours": calc.COOLDOWN_HOURS},
        "obligations": sorted([obligations.view(s, o) for o in s.obligations.values() if not o.paid],
                              key=lambda x: x["due_date"]),
        "inbox_count": len(pend),
        "stops": [{"id": st.id, **guardian.stop_view(s, st)}
                  for st in s.stops.values() if st.status in ("open", "cooling")],
        "transactions": [{**t, "title": render(t["title"])} for t in s.transactions[:15]],
        "demo_mode": DEMO_MODE,
    }


# ---- routes ----
@app.get("/state")
def get_state():
    with STORE.lock:
        agent.agent_review(STORE.state)
        return state_view()


@app.get("/mcc")
def mcc_list():
    return [{"mcc": k, "label": mcc_mod.label(k), "category": v[0].value} for k, v in mcc_mod.MCC_TABLE.items()]


@app.get("/calc/preview")
def calc_preview(amount: int, percent: int):
    if not (0 < amount <= calc.MAX_AMOUNT) or not (1 <= percent <= calc.MAX_TOTAL_PERCENT):
        raise CalcError(tr("err_check_amount_pct"))
    with STORE.lock:
        return goals.preview(STORE.state, amount, percent)


@app.get("/calc/suggest")
def calc_suggest(amount: int, months: int):
    if not (0 < amount <= calc.MAX_AMOUNT) or not (1 <= months <= calc.MAX_MONTHS):
        raise CalcError(tr("err_check_amount_term"))
    with STORE.lock:
        return goals.suggest(STORE.state, amount, months)


@app.post("/subcards")
def create_subcard(body: GoalIn):
    with STORE.lock:
        g = goals.create(STORE.state, body.name, body.amount, body.percent)
        agent.agent_review(STORE.state)
        return goals.view(STORE.state, g)


@app.post("/subcards/reorder")
def reorder_subcards(body: ReorderIn):
    with STORE.lock:
        gs = goals.reorder(STORE.state, body.ids)
        return [goals.view(STORE.state, g) for g in gs]


@app.get("/subcards/{goal_id}")
def get_subcard(goal_id: str):
    with STORE.lock:
        return goals.view(STORE.state, goals.get(STORE.state, goal_id))


@app.post("/subcards/{goal_id}/use")
def use_subcard(goal_id: str):
    with STORE.lock:
        return goals.use(STORE.state, goal_id)


@app.post("/subcards/{goal_id}/cancel")
def cancel_subcard(goal_id: str, body: ConfirmIn):
    if not body.confirm:
        raise CalcError(tr("err_need_confirm"))
    with STORE.lock:
        return goals.start_close(STORE.state, goal_id)


@app.get("/obligations")
def list_obligations():
    with STORE.lock:
        return state_view()["obligations"]


@app.post("/obligations")
def create_obligation(body: ObligationIn):
    with STORE.lock:
        o = obligations.create(STORE.state, body.name, body.amount, body.due_date, body.monthly)
        agent.agent_review(STORE.state)
        return obligations.view(STORE.state, o)


@app.post("/obligations/{obl_id}/pay")
def pay_obligation(obl_id: str, body: ConfirmIn):
    if not body.confirm:
        raise CalcError(tr("err_need_confirm"))
    with STORE.lock:
        res = obligations.pay(STORE.state, obl_id)
        agent.agent_review(STORE.state)
        return res


@app.post("/spend")
def spend(body: SpendIn):
    with STORE.lock:
        res = guardian.spend(STORE.state, body.source_id, body.amount, body.mcc, body.merchant, body.note)
        agent.agent_review(STORE.state)
        return res


@app.post("/spend/{stop_id}/resolve")
def resolve_stop(stop_id: str, body: ResolveIn):
    with STORE.lock:
        res = guardian.resolve(STORE.state, stop_id, body.option, body.confirm)
        agent.agent_review(STORE.state)
        return res


# simple in-memory rate limit for the paid LLM endpoint
_chat_hits: deque[float] = deque()
CHAT_LIMIT_PER_MIN = 20


@app.post("/agent/chat")
def agent_chat(body: ChatIn):
    now = time.monotonic()
    while _chat_hits and now - _chat_hits[0] > 60:
        _chat_hits.popleft()
    if len(_chat_hits) >= CHAT_LIMIT_PER_MIN:
        return JSONResponse(status_code=429, content={"detail": tr("err_rate_limit")})
    _chat_hits.append(now)
    with STORE.lock:
        set_lang(body.lang)  # the chat body wins over the header
        return agent.chat(STORE.state, body.message, [t.model_dump() for t in body.history], body.lang)


@app.get("/agent/inbox")
def inbox():
    with STORE.lock:
        agent.agent_review(STORE.state)
        ps = sorted(STORE.state.proposals.values(), key=lambda p: p.created_at, reverse=True)
        return [proposals.view(p) for p in ps][:50]


@app.post("/agent/proposals/{pid}/confirm")
def confirm_proposal(pid: str, body: ProposalIn | None = None):
    with STORE.lock:
        return proposals.apply(STORE.state, pid, body.option if body else None)


@app.post("/agent/proposals/{pid}/reject")
def reject_proposal(pid: str):
    with STORE.lock:
        return proposals.reject(STORE.state, pid)


# ---- demo controls (DEMO_MODE only) ----
def _demo_guard():
    if not DEMO_MODE:
        raise KeyError(tr("err_not_found"))


@app.post("/demo/salary")
def demo_salary(body: SalaryIn):
    _demo_guard()
    with STORE.lock:
        return proposals.salary(STORE.state, body.amount)


@app.post("/demo/transfer-in")
def demo_transfer_in(body: TransferIn):
    """Money from family etc.: credits the main card only. No contributions, no plan change."""
    _demo_guard()
    with STORE.lock:
        return proposals.transfer_in(STORE.state, body.amount, body.source)


@app.post("/demo/skip-time")
def demo_skip(body: SkipIn):
    _demo_guard()
    with STORE.lock:
        proposals.skip_time(STORE.state, body.hours)
        return {"clock": STORE.state.clock.isoformat()}


@app.post("/demo/purchase")
def demo_purchase(body: SpendIn):
    _demo_guard()
    return spend(body)


@app.post("/demo/reset")
def demo_reset():
    _demo_guard()
    STORE.reset()
    return {"ok": True}
