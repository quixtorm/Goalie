# Мечта и Щит — AI Financial Agent (hackathon demo)

Banking-app feature for Uzbekistan: **goal sub-cards** ("Мечта"), an **obligations card** ("Щит") and an
**AI Financial Agent** that runs *observe → calculate → propose → act only after confirmation*.
Mock data only: no real bank, no auth, no database.

- **Every number is computed by code** (`backend/calc.py`, exact fractions, no floats). The AI only writes the wording.
- **The AI can't move money.** It can only create proposal cards; a person confirms them.
- **The demo works without an API key**: a deterministic fallback agent gives the same numbers.

## Run it (Windows / PowerShell)

Backend (Python 3.11+):
```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```
Put your key in `backend/.env` (`ANTHROPIC_API_KEY=...`). Leave it empty to use the fallback agent.

Frontend (Node 20+), in a second terminal:
```powershell
cd frontend
npm install
npm run dev
```
Open http://127.0.0.1:5173, preferably in phone view (F12 → device toolbar).

Tests (54 tests, ~8 s, no API key needed):
```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q
```

## 3-minute demo script

Before starting: Главная → «🎬 Управление демо» → «Сбросить демо».

| # | Action | What the audience sees (exact numbers) |
|---|---|---|
| 1 | Помощник → chip «Хочу накопить 50 млн на машину за 3 года» → «Создать цель» (or type «да») | 21% of income (≈1 428 000 so'm/month), best 32 months, worst 36, deadline 1 декабря 2029, lock warning. Goal «Машина» appears. |
| 2 | Главная → Управление демо → preset «−15%» (6 375 000) → «Зачислить» | Rent is set aside first, then the goals, then the rest: main card 14 898 750. 🔔 1 tip: «Машина» slipped 2 months → «Поставить 22%» → deadline back to 35 months. |
| 3 | Управление демо → purchase: 🎯 Машина, Кинотеатр (7832), 150 000 → «Оплатить картой» | ✋ Stop card: goal delayed **3 days**, bonus lower by **7 750 042 so'm** (22% → 12%). Choose «Подождать до завтра». Then «Перемотать на 24 часа» → 🔔 «Прошли сутки…» → «Уже не нужно». |
| 4 | Same panel: Аптека (5912), 300 000 → «Оплатить картой» | 💚 Paid with no penalty, 22% bonus kept, deadline unchanged. |
| 5 | Помощник → chip «Хочу телефон в кредит за 20 млн на 12 месяцев под 28%» | 1 930 120 so'm/month, overpayment 3 161 437, 30% of income, ⚠ payment is bigger than free money (1 835 000), «Машина» 35 → 51 months. No bank recommendations. |
| 6 | Платежи → «＋ Добавить платёж»: «Долг брату», 1 500 000, 5 декабря 2026 | 🔔 «Не хватает 1 500 000» → «Перевести 1 500 000 so'm» → status «✓ Хватает». |

These numbers are asserted in `backend/tests/test_demo_scenario.py`. If that test passes, the demo will show exactly these values.

## How it works

```
backend/
  calc.py          all formulas & constants (pure functions, exact math)
  mcc.py           purchase type by MCC code (code decides, never the AI or user text)
  state.py         in-memory store + demo clock (one lock around all changes)
  mock_data.py     seed user
  modules/         budget, goals, obligations, guardian (anti-impulse), proposals (agent_review + salary waterfall)
  agent.py         chat router: typed «да» → code; API key → llm.py; otherwise → fallback.py
  llm.py           Anthropic SDK tool loop (read-only tools + propose_* tools)
  fallback.py      deterministic Russian agent (regex intents + templates)
  main.py          FastAPI routes, input validation, security headers
frontend/src/      React + Tailwind, 3 tabs: Главная · Платежи · Помощник
```

Salary order: **obligations first → goals by % of income → the rest to the main card.**
Spending from a goal: **pharmacy/hospital → released with no penalty**; **anything else → stop card** (cost of breaking the goal, a 24-hour pause, or paying from the main card instead). Proceeding anyway is always possible, but the bonus drops from 22% to 12%.

## Security

Built into the demo:
- API key only in `backend/.env` (gitignored), never sent to the browser or logged; `.env.example` has a placeholder.
- Servers bind to 127.0.0.1; CORS allows only the Vite origin; the browser talks to one origin through the Vite proxy.
- Every request body is a strict pydantic model: amounts between 1 and 10¹² so'm, percent 1–40, MCC exactly 4 digits, text up to 100 characters (chat up to 1000), unknown fields rejected.
- Errors return a short Russian message; there are no stack traces or internal paths in responses.
- Prompt-injection defence: the AI has only read-only tools plus `propose_*`. Every change needs a human click, and a typed «да» is handled by code. User text and state are sent as delimited data. Tool inputs are re-validated before running.
- Idempotent actions: a proposal, stop card or payment can't be applied twice.
- `/agent/chat` is rate-limited (20 requests/min); `/demo/*` only works with `DEMO_MODE=true`.
- Response headers: `nosniff`, `X-Frame-Options: DENY`, `no-referrer`, `no-store`. The frontend has a CSP and never uses `dangerouslySetInnerHTML`.
- Tests: `tests/test_security.py`, `tests/test_llm.py` (injection, bad input, double confirm, refusal → fallback).

Dependency audit (21 Nov 2026):
- `pip-audit`: no known vulnerabilities.
- `npm audit`: one moderate advisory (GHSA-67mh-4wv8-2f99, esbuild inside the **Vite dev server only**). The fix needs Vite 8, a breaking upgrade. Mitigation: the dev server binds to 127.0.0.1 only, and the production build (`npm run build`) is static files that don't include esbuild.

In production this would also need (not built): real authentication with 2FA, encryption at rest, an audit log of every money movement, PCI DSS for card data, data localisation under Uzbekistan's personal-data law (ZRU-547), fraud monitoring, and a server-side session per user.

## What is real vs mocked

| Real | Mocked |
|---|---|
| All calculations, guardian rules, proposals, waterfall, validation | Bank, cards, payments (in-memory numbers) |
| AI chat via the Anthropic API (when a key is set) | One demo user, no login |
| Deterministic fallback agent | Clock (`/demo/skip-time`), salary (`/demo/salary`) |

## Known limitations
- State resets when the backend restarts (in memory by design).
- A salary event counts as "one month" for goals and bonus but does not move the clock.
- The fallback agent understands a fixed set of phrasings (goal, credit, payments, balance).
- Bonus rates 22% / 12% are demo values; who funds them is a business decision.
- UI is Russian only.
