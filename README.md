# SmartGoal вЂ” AI Financial Agent (hackathon demo)

Banking-app feature for Uzbekistan: **goal sub-cards** ("РњРµС‡С‚Р°"), an **obligations card** ("Р©РёС‚") and an
**AI Financial Agent** that runs *observe в†’ calculate в†’ propose в†’ act only after confirmation*.
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
Open http://127.0.0.1:5173, preferably in phone view (F12 в†’ device toolbar).

Tests (97 tests, ~8 s, no API key needed; `test_i18n.py` runs the whole demo in Uzbek and fails on any Russian text):
```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q
```

## 3-minute demo script

Before starting: tab В«Р•С‰С‘В» в†’ В«рџЋ¬ РЈРїСЂР°РІР»РµРЅРёРµ РґРµРјРѕВ» в†’ В«РЎР±СЂРѕСЃРёС‚СЊ РґРµРјРѕВ». Language toggle (Р СѓСЃСЃРєРёР№ / O'zbekcha) is also in В«Р•С‰С‘В».
The AI agent opens from the header on every screen: the search field В«РџРѕРёСЃРє РёР»Рё СЃРїСЂРѕСЃРёС‚Рµ AIВ» (вњ¦) or the рџ”” bell (opens on the tips inbox).

| # | Action | What the audience sees (exact numbers) |
|---|---|---|
| 1 | Header search вњ¦ в†’ chip В«РҐРѕС‡Сѓ РЅР°РєРѕРїРёС‚СЊ 50 РјР»РЅ РЅР° РјР°С€РёРЅСѓ Р·Р° 3 РіРѕРґР°В» в†’ В«РЎРѕР·РґР°С‚СЊ С†РµР»СЊВ» (or type В«РґР°В») | Agent sheet slides up: 21% of income (в‰€1 428 000 so'm/month), best 32 months, worst 36, deadline 1 РґРµРєР°Р±СЂСЏ 2029, lock warning. Home: В«РџРѕРєР°Р·Р°С‚СЊ РїРѕРґРєР°СЂС‚С‹ (2/3)В». |
| 1b | Tab В«Р¦РµР»РёВ» в†’ в–І on В«РњР°С€РёРЅР°В» | В«РњР°С€РёРЅР°В» becomes #1, В«РўРµР»РµС„РѕРЅВ» #2. If a salary is too small, #1 is funded first and the shortfall is shown. |
| 2 | В«Р•С‰С‘В» в†’ demo panel в†’ preset В«в€’15%В» (6 375 000) в†’ В«Р—Р°С‡РёСЃР»РёС‚СЊВ» | Rent first, then goals by priority (РњР°С€РёРЅР°, then РўРµР»РµС„РѕРЅ), rest to the main card: 14 898 750. рџ”” 1 в†’ В«Р¦РµР»СЊ В«РњР°С€РёРЅР°В» РѕС‚СЃС‚Р°С‘С‚В» в†’ В«РџРѕСЃС‚Р°РІРёС‚СЊ 22%В» в†’ back to 35 months. |
| 3 | Same panel: purchase В«#1 РњР°С€РёРЅР°В», РљРёРЅРѕС‚РµР°С‚СЂ (7832), 150 000 в†’ В«РћРїР»Р°С‚РёС‚СЊ РєР°СЂС‚РѕР№В» | вњ‹ Guardian sheet: goal delayed **3 days**, bonus lower by **7 750 042 so'm** (22% в†’ 12%). В«РџРѕРґРѕР¶РґР°С‚СЊ РґРѕ Р·Р°РІС‚СЂР°В». Then В«РџРµСЂРµРјРѕС‚Р°С‚СЊ РЅР° 24 С‡Р°СЃР°В» в†’ рџ”” В«РџСЂРѕС€Р»Рё СЃСѓС‚РєРёвЂ¦В» в†’ В«РЈР¶Рµ РЅРµ РЅСѓР¶РЅРѕВ». |
| 4 | Same panel: РђРїС‚РµРєР° (5912), 300 000 в†’ В«РћРїР»Р°С‚РёС‚СЊ РєР°СЂС‚РѕР№В» | рџ’љ Paid with no penalty, 22% bonus kept, deadline unchanged. |
| 5 | Home в†’ quick action В«Р Р°СЃС‡С‘С‚ РєСЂРµРґРёС‚Р°В» (or the chip) | 1 930 120 so'm/month, overpayment 3 161 437, 30% of income, вљ  payment is bigger than free money (1 835 000), В«РњР°С€РёРЅР°В» 35 в†’ 51 months. No bank recommendations. |
| 6 | Tab В«РџР»Р°С‚РµР¶РёВ» в†’ В«пј‹ Р”РѕР±Р°РІРёС‚СЊ РїР»Р°С‚С‘Р¶В»: В«Р”РѕР»Рі Р±СЂР°С‚СѓВ», 1 500 000, 5 РґРµРєР°Р±СЂСЏ 2026 | рџ”” / Home В«AI-СЃРѕРІРµС‚РЅРёРєВ»: В«РќРµ С…РІР°С‚Р°РµС‚ 1 500 000В» в†’ В«РџРµСЂРµРІРµСЃС‚Рё 1 500 000 so'mВ» в†’ status В«вњ“ РҐРІР°С‚Р°РµС‚В». |
| 7 | В«Р•С‰С‘В» в†’ В«РЎРёРјСѓР»РёСЂРѕРІР°С‚СЊ РїРµСЂРµРІРѕРґ РѕС‚ Р±Р»РёР·РєРёС…В»: 2 000 000, В«РЎРµРјСЊСЏВ» | Main card +2 000 000, chip В«РџРµСЂРµРІРѕРґВ». В«РњР°С€РёРЅР°В»: percent, deadline and months **unchanged** (plan = salary only). рџ”” В«РџСЂРёС€Р»Рѕ 2 000 000 so'm РѕС‚: РЎРµРјСЊСЏвЂ¦ РџСЂРµРґР»Р°РіР°СЋ 22% вЂ” 440 000 so'mВ» в†’ В«РћС‚Р»РѕР¶РёС‚СЊ 440 000 so'mВ» в†’ saved +440 000, deadline still the same. Ask the agent В«РџРѕС‡РµРјСѓ РїРµСЂРµРІРѕРґС‹ РЅРµ СѓС‡РёС‚С‹РІР°СЋС‚СЃСЏ?В» в†’ it answers from `list_income_by_type`. |

| 8 | Home → «Кредит подобрать» (or chat): «Посоветуй лучший кредит с низким процентом на компьютер 15 млн» | 3 offer cards (демо-данные): **★ Лучший по стоимости** «Потребительский Стандарт» 12 мес — 1 432 952/мес, переплата 2 345 425, 22% зарплаты, chips «Машина +10 мес», «Телефон +2 мес»; «Меньше платёж» «Выгодный (долгий срок)» 48 мес — 472 591/мес but 7 984 376 overpayment; row «Накопить самому: 30 месяцев, без переплаты». Nothing is applied until «Оформить заявку (демо)» → confirm. |

**Credit advisor.** Ranking is code (`calc.rank_credits`) over a fictional demo catalog (`backend/loan_products.py`):
eligibility (amount, term, salary history) → for each product/term: payment, interest + origination fee, share of the
worst monthly salary, risk (> 40%), cash gap, goal delays → best = lowest total cost among safe options, plus
lowest-payment and fastest alternatives and a "save it yourself" comparison. The agent may only explain what the tool
returns; applying is a mock (`POST /credits/apply`) that needs explicit confirmation and moves no money.

**Income types.** Every inflow is SALARY, TRANSFER (family, friends) or OTHER. Only SALARY feeds the plan
(worst/avg monthly salary over the last 6 salaries; worst annual = worst month Г— 12). Transfers credit the main card
and only trigger an optional "set part aside?" proposal вЂ” nothing moves without confirmation.

These numbers are asserted in `backend/tests/test_demo_scenario.py`. If that test passes, the demo will show exactly these values.

## How it works

```
backend/
  calc.py          all formulas & constants (pure functions, exact math)
  mcc.py           purchase type by MCC code (code decides, never the AI or user text)
  state.py         in-memory store + demo clock (one lock around all changes)
  mock_data.py     seed user
  modules/         budget, goals, obligations, guardian (anti-impulse), proposals (agent_review + salary waterfall)
  agent.py         chat router: typed В«РґР°В» в†’ code; API key в†’ llm.py; otherwise в†’ fallback.py
  llm.py           Anthropic SDK tool loop (read-only tools + propose_* tools)
  fallback.py      deterministic Russian agent (regex intents + templates)
  main.py          FastAPI routes, input validation, security headers
frontend/src/      React + Tailwind, dark theme, 4 tabs: Р“Р»Р°РІРЅР°СЏ В· РџР»Р°С‚РµР¶Рё В· Р¦РµР»Рё В· Р•С‰С‘
                   AI agent = bottom sheet (components/AgentSheet.jsx), guardian = GuardianSheet.jsx, i18n.js (ru/uz)
```

Salary order: **obligations first в†’ goals by % of income в†’ the rest to the main card.**
Spending from a goal: **pharmacy/hospital в†’ released with no penalty**; **anything else в†’ stop card** (cost of breaking the goal, a 24-hour pause, or paying from the main card instead). Proceeding anyway is always possible, but the bonus drops from 22% to 12%.

## Security

Built into the demo:
- API key only in `backend/.env` (gitignored), never sent to the browser or logged; `.env.example` has a placeholder.
- Servers bind to 127.0.0.1; CORS allows only the Vite origin; the browser talks to one origin through the Vite proxy.
- Every request body is a strict pydantic model: amounts between 1 and 10В№ВІ so'm, percent 1вЂ“40, MCC exactly 4 digits, text up to 100 characters (chat up to 1000), unknown fields rejected.
- Errors return a short Russian message; there are no stack traces or internal paths in responses.
- Prompt-injection defence: the AI has only read-only tools plus `propose_*`. Every change needs a human click, and a typed В«РґР°В» is handled by code. User text and state are sent as delimited data. Tool inputs are re-validated before running.
- Idempotent actions: a proposal, stop card or payment can't be applied twice.
- `/agent/chat` is rate-limited (20 requests/min); `/demo/*` only works with `DEMO_MODE=true`.
- Response headers: `nosniff`, `X-Frame-Options: DENY`, `no-referrer`, `no-store`. The frontend has a CSP and never uses `dangerouslySetInnerHTML`.
- Tests: `tests/test_security.py`, `tests/test_llm.py` (injection, bad input, double confirm, refusal в†’ fallback).

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
- UI and all server texts (tips, guardian, errors, purchase types, transactions, fallback agent) are Russian and
  Uzbek; the app sends `X-Lang` with every request. Names the user types (e.g. a new goal) stay as typed.
- Goal priority uses в–І/в–ј buttons instead of drag-and-drop (works with touch, keyboard and screen readers).

## Demo video (QA)

Automated recording of the full scenario (Playwright, 390x844 phone view, fake cursor and captions). Start backend and frontend first, then:

```powershell
qa\.venv\Scripts\python.exe qa\record_demo.py
```

Outputs `qa/video/demo.mp4`, `demo.webm`, `frames/`, `report.md` and `qa/demo_video.zip`. Setup: see `qa/video/report.md`.

