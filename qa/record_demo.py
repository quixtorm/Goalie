"""Automated demo videos of Goalie (QA tooling only — does not change the app).

Two recordings:
  short  qa/video/demo_short.mp4  ~80-95 s pitch cut: salary split, Guardian, agent plan + credit advisor, end card
  full   qa/video/demo_full.mp4   the full scenario: goal creation, priorities, salary, family transfer, Guardian,
                                  PIN step-up + cancel, credit advisor, obligations, language toggle

Prereqs: backend on http://127.0.0.1:8000 (DEMO_MODE=true) and frontend on http://127.0.0.1:5173 running.
  en     qa/video/demo_en.mp4     the short cut in English with narration (qa/narration.json, qa/narrate.py)

Run:     qa\\.venv\\Scripts\\python.exe qa\\record_demo.py [short|full|both|en]  (default: both)
Output:  qa/video/demo_short.mp4, demo_full.mp4, frames/*.png, report.md, and qa/demo_video.zip
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request
import zipfile
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
OUT = ROOT / "video"
FRAMES = OUT / "frames"
FAIL_DIR = OUT / "failures"
APP = "http://127.0.0.1:5173"
API = "http://127.0.0.1:8000"
VIEW = {"width": 390, "height": 844}
TYPE_DELAY = 40          # ms per character
SLOW_MO = 150            # ms pause per visible user action (click). Applied in Recorder.click instead of
                         # Playwright's slow_mo, which would add it to every internal call (~10 per click).
PAUSE_SCALE = {"short": 1.0,   # short cut: 1.5-2 s on each key screen, as written
               "en": 1.0,      # English cut: each scene also lasts at least its narration + 0.5 s
               "full": 0.58}   # full scenario: reading pauses x0.58 -> 11 steps in about 3 minutes
MAX_MB = 50              # each mp4 must stay under this
sys.stdout.reconfigure(encoding="utf-8")

# ---------- overlay: fake cursor + caption bar (injected into every page) ----------
OVERLAY_JS = r"""
(() => {
  if (window.__qaOverlay) return; window.__qaOverlay = true;
  const css = `
    #qa-cursor{position:fixed;left:0;top:0;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;
      background:rgba(255,255,255,.85);border:2px solid #2E7BD6;box-shadow:0 0 0 4px rgba(46,123,214,.25),0 4px 12px rgba(0,0,0,.5);
      z-index:2147483647;pointer-events:none;transition:transform .12s ease,left .05s linear,top .05s linear}
    #qa-cursor.down{transform:scale(.7);background:#5AA2F0}
    .qa-pulse{position:fixed;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;border:3px solid #5AA2F0;
      z-index:2147483646;pointer-events:none;animation:qa-p .6s ease-out forwards}
    @keyframes qa-p{from{transform:scale(1);opacity:1}to{transform:scale(3.2);opacity:0}}
    #qa-caption{position:fixed;left:10px;right:10px;bottom:96px;z-index:2147483645;pointer-events:none;
      background:rgba(8,10,16,.82);color:#fff;font:600 17px/1.35 Inter,system-ui,sans-serif;padding:12px 14px;
      border-radius:14px;border:1px solid rgba(255,255,255,.15);box-shadow:0 8px 24px rgba(0,0,0,.45);
      opacity:0;transform:translateY(8px);transition:opacity .25s,transform .25s}
    #qa-caption.on{opacity:1;transform:none}
    #qa-caption.top{bottom:auto;top:14px}
    #qa-caption small{display:block;font-weight:500;font-size:13px;color:#9fc3ff;margin-bottom:2px}`;
  const add = () => {
    const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    const c = document.createElement('div'); c.id = 'qa-cursor'; document.body.appendChild(c);
    const cap = document.createElement('div'); cap.id = 'qa-caption'; document.body.appendChild(cap);
    addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', e => { c.classList.add('down'); const p = document.createElement('div');
      p.className = 'qa-pulse'; p.style.left = e.clientX + 'px'; p.style.top = e.clientY + 'px';
      document.body.appendChild(p); setTimeout(() => p.remove(), 700); }, true);
    addEventListener('mouseup', () => c.classList.remove('down'), true);
    // bottom sheets open from the bottom: move the caption to the top while one is open, so it never covers them
    setInterval(() => cap.classList.toggle('top', !!document.querySelector('[role=dialog]')), 150);
    window.__caption = (step, text) => { cap.innerHTML = ''; const s = document.createElement('small');
      s.textContent = step; cap.appendChild(s); cap.appendChild(document.createTextNode(text));
      cap.classList.toggle('on', !!text); };
  };
  if (document.body) add(); else addEventListener('DOMContentLoaded', add);
})();
"""


class Recorder:
    def __init__(self, page: Page, pause_scale: float = 1.0, lang: str = "ru", t0: float | None = None):
        self.page = page
        self.pause_scale = pause_scale
        self.lang = lang
        self.scene_starts: dict[str, float] = {}  # scene id -> seconds from the start of the video
        self.t0 = t0 if t0 is not None else time.monotonic()  # = video start (page creation)
        self.steps: list[dict] = []
        self.console_errors: list[str] = []
        self.bad_requests: list[str] = []
        self.issues: list[str] = []
        self.cur = None
        page.on("console", lambda m: m.type == "error" and self.console_errors.append(f"[{self.ts()}] {m.text[:200]}"))
        page.on("requestfailed", lambda r: self.bad_requests.append(f"[{self.ts()}] FAILED {r.method} {r.url}"))
        page.on("response", lambda r: r.status >= 400 and self.bad_requests.append(
            f"[{self.ts()}] HTTP {r.status} {r.request.method} {r.url}"))

    def ts(self) -> str:
        s = time.monotonic() - self.t0
        return f"{int(s // 60)}:{s % 60:04.1f}"

    # ---- presentation helpers ----
    def caption(self, text: str):
        self.page.evaluate("([s, t]) => window.__caption && window.__caption(s, t)",
                           [self.cur["title"] if self.cur else "", text])

    def pause(self, sec: float = 2.0):
        self.page.wait_for_timeout(int(sec * self.pause_scale * 1000))

    def show(self, loc):
        loc.first.evaluate("e => e.scrollIntoView({block: 'center', behavior: 'smooth'})")
        self.page.wait_for_timeout(500)

    def click(self, loc, settle: float = 0.6):
        el = loc.first
        el.wait_for(state="visible", timeout=15000)
        # center it: fixed bars (tab bar, sticky button, caption) must not cover the target
        el.evaluate("e => e.scrollIntoView({block: 'center', behavior: 'instant'})")
        self.page.wait_for_timeout(250)
        # the point we click must really hit this element (not a fixed bar / caption-free overlay)
        for nudge in (0, -160, 160, -320):
            if nudge:
                self.page.mouse.wheel(0, -nudge)
                self.page.wait_for_timeout(250)
            box = el.bounding_box()
            x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            if el.evaluate("(e, [x, y]) => { const h = document.elementFromPoint(x, y); return !!h && (e === h || e.contains(h)); }",
                           [x, y]):
                break
        else:
            raise AssertionError("click target is covered by another element")
        self.page.mouse.move(x, y, steps=18)
        self.page.wait_for_timeout(SLOW_MO)
        box = el.bounding_box()  # re-read: layout may have shifted while the cursor moved
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        self.page.mouse.move(x, y, steps=4)
        self.page.mouse.click(x, y)
        self.page.wait_for_timeout(int(settle * 1000))

    def type(self, loc, text: str):
        self.click(loc, 0.2)
        loc.first.fill("")
        loc.first.press_sequentially(text, delay=TYPE_DELAY)

    def expect(self, ok: bool, what: str):
        """Turn a silent miss (click landed on the wrong element) into a reported step failure."""
        if not ok:
            raise AssertionError(what)

    def goal(self, name: str) -> dict:
        req = urllib.request.Request(API + "/state", headers={"X-Lang": self.lang})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return next((g for g in json.loads(resp.read())["goals"] if g["name"] == name), {})

    def btn(self, name, exact=False):
        return self.page.get_by_role("button", name=name, exact=exact)

    def tab(self, name):
        return self.page.locator("nav").get_by_role("button", name=name)

    def close_sheets(self):
        for _ in range(3):
            if self.page.locator("[role=dialog]").count() == 0:
                return
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(350)

    def scene(self, sid: str, title: str, fn, audio_sec: float):
        """A narrated scene: runs like a step, then holds until the narration (+0.5 s) has finished."""
        start = time.monotonic() - self.t0
        self.scene_starts[sid] = start

        def run():
            try:
                fn()
            finally:
                left = start + audio_sec + 0.5 - (time.monotonic() - self.t0)
                if left > 0:
                    self.page.wait_for_timeout(int(left * 1000))
        self.step(title, run)
        self.steps[-1]["scene"] = sid

    # ---- step runner: a failed step is logged + screenshotted, the recording continues ----
    def step(self, title: str, fn):
        self.cur = {"title": title, "start": time.monotonic() - self.t0, "ok": True, "error": None}
        print(f"[{self.ts()}] ▶ {title}")
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            self.cur["ok"] = False
            self.cur["error"] = f"{type(e).__name__}: {str(e).splitlines()[0][:300]}"
            FAIL_DIR.mkdir(parents=True, exist_ok=True)
            shot = FAIL_DIR / f"step{len(self.steps) + 1:02d}.png"
            try:
                self.page.screenshot(path=str(shot))
            except Exception:  # noqa: BLE001
                pass
            print(f"   ✗ {self.cur['error']}")
            traceback.print_exc(limit=1)
            self.close_sheets()
            try:
                self.click(self.tab(re.compile("Главная|Asosiy|^Home$")), 0.5)
            except Exception:  # noqa: BLE001
                pass
        try:
            if self.page.evaluate("document.documentElement.scrollWidth > innerWidth + 1"):
                self.issues.append(f"{title}: horizontal overflow (page wider than the screen)")
        except Exception:  # noqa: BLE001
            pass
        self.cur["end"] = time.monotonic() - self.t0
        self.steps.append(self.cur)
        self.cur = None


def post(path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(API + path, data=json.dumps(body or {}).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read() or b"{}")


def agent_mode() -> str:
    env = PROJECT / "backend" / ".env"
    has_key = False
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.lstrip("﻿")  # .env may start with a BOM
            if line.startswith("ANTHROPIC_API_KEY=") and line.split("=", 1)[1].strip():
                has_key = True
    return "LLM (via API key)" if has_key else "fallback (no API key)"


def call(method: str, path: str, body: dict | None = None, lang: str = "ru") -> dict:
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None,
                                 method=method, headers={"Content-Type": "application/json", "X-Lang": lang})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read() or b"{}")


END_CARD_JS = r"""
(text) => {
  const d = document.createElement('div');
  d.style.cssText = 'position:fixed;inset:0;z-index:2147483640;display:grid;place-items:center;padding:32px;' +
    'background:radial-gradient(120% 80% at 50% 20%,#1f5fae 0%,#0b1220 70%);color:#fff;text-align:center;' +
    'font:800 30px/1.25 Inter,system-ui,sans-serif;opacity:0;transition:opacity .6s';
  const box = document.createElement('div');
  const logo = document.createElement('div');
  logo.style.cssText = 'width:76px;height:76px;margin:0 auto 22px;border-radius:22px;background:#fff;' +
    'color:#1f5fae;display:grid;place-items:center;font-size:44px';
  logo.textContent = 'G';
  const t = document.createElement('div'); t.textContent = text;
  box.appendChild(logo); box.appendChild(t); d.appendChild(box);
  document.body.appendChild(d);
  const cap = document.getElementById('qa-caption'); if (cap) cap.classList.remove('on');
  requestAnimationFrame(() => { d.style.opacity = 1; });
}
"""


# ---------------- seeds (through the public demo API, before the recording starts) ----------------
def seed_full():
    post("/demo/reset")


def seed_short():
    """«Машина» #1 (21%, some progress) and «Телефон» #2, rent due in 6 days with a partial reserve."""
    post("/demo/reset")
    car = call("POST", "/subcards", {"name": "Машина", "goal_amount": 50_000_000, "term_months": 36})
    call("POST", "/subcards/reorder", {"ids": [car["id"], "goal_phone"]})
    # progress for «Машина»: a family transfer, and the agent's optional "set part aside" accepted
    call("POST", "/demo/transfer-in", {"amount": 10_000_000, "source": "Семья"})
    for prop in call("GET", "/agent/inbox"):
        if prop["kind"] == "transfer_save" and prop["status"] == "pending":
            call("POST", f"/agent/proposals/{prop['id']}/confirm", {})
    st = call("GET", "/state")
    names = [(g["name"], g["priority"]) for g in st["goals"] if g["status"] == "active"]
    assert names == [("Машина", 1), ("Телефон", 2)], names
    assert next(g for g in st["goals"] if g["name"] == "Машина")["saved"] > 0
    assert any(o["due_in_days"] <= 7 and not o.get("paid") for o in st["obligations"])


# ---------------- short scenario (~90 s) ----------------
def short_scenario(r: Recorder):
    p = r.page

    def home():
        r.caption("Главная: основная карта и подкарты-цели — «Машина» #1 и «Телефон» #2")
        r.pause(2)
        r.click(p.get_by_text(re.compile("Показать подкарты")))
        r.caption("Подкарты выезжают из-под основной карты, у каждой — прогресс и приоритет")
        r.pause(2)
        r.click(p.get_by_text(re.compile("Скрыть подкарты")))
        r.pause(0.6)

    def salary():
        r.click(r.tab("Ещё"))
        r.show(p.get_by_text("Управление демо"))
        r.caption("Демо: приходит зарплата")
        r.click(r.btn(re.compile("^Обычная")))
        before = r.goal("Машина").get("saved", 0)
        r.click(r.btn("Зачислить", exact=True), 0.2)
        sheet = p.get_by_role("dialog", name="Goalie разложил зарплату")
        sheet.wait_for(timeout=10000)
        r.caption("Зарплата пришла: Goalie сам разложил")
        p.wait_for_timeout(2600)  # all lines in, amounts landed in the cards
        labels = [x.strip() for x in sheet.locator("li .font-semibold.truncate").all_inner_texts()]
        r.expect(labels == ["Аренда квартиры", "Машина", "Телефон", "Основная карта"],
                 f"waterfall order should be rent -> #1 -> #2 -> main card, got {labels}")
        sheet.wait_for(state="detached", timeout=8000)  # auto-close after 3 s
        r.expect(r.goal("Машина").get("saved", 0) > before, "«Машина» should grow after the salary")
        r.click(p.get_by_text(re.compile("Показать подкарты")))
        r.caption("Прогресс подкарт вырос — без единого действия пользователя")
        r.pause(2)
        r.click(p.get_by_text(re.compile("Скрыть подкарты")))

    def guardian():
        r.click(r.tab("Ещё"))
        r.show(p.get_by_text(re.compile("Покупка из цели")))
        r.caption("Покупка в кино (MCC 7832) из денег на «Машину»")
        r.expect("Машина" in p.locator('select[aria-label="source"] option:checked').inner_text(),
                 "source should be «Машина»")
        p.locator('select[aria-label="MCC"]').select_option("7832")
        r.type(p.locator('input[aria-label="amount"]'), "150000")
        r.click(r.btn("Оплатить картой"))
        p.get_by_text(re.compile("Подождите")).wait_for(timeout=10000)
        r.caption("Стоп-карта: на сколько дней отложится цель и сколько бонуса сгорит")
        r.pause(3)
        r.click(r.btn(re.compile("Подождать до завтра")))
        r.caption("Пауза 24 часа вместо импульсной покупки")
        r.pause(1.5)
        r.click(r.btn("Хорошо"))
        p.locator('select[aria-label="MCC"]').select_option("5912")
        r.type(p.locator('input[aria-label="amount"]'), "300000")
        r.caption("Аптека (MCC 5912) — экстренная покупка")
        r.click(r.btn("Оплатить картой"))
        p.get_by_text("Оплачено без штрафа").wait_for(timeout=10000)
        r.caption("Срыв остановили, экстренное не тронули")
        r.pause(2)
        r.click(r.btn("Хорошо"))

    def agent():
        r.click(r.tab("Главная"))
        r.click(r.btn("Поиск или спросите AI"))
        box = p.get_by_role("textbox", name="Напишите вопрос…")
        r.type(box, "Хочу накопить 50 млн на машину за 3 года")
        r.click(r.btn("Отправить", exact=True), 0.3)
        r.caption("Агент считает по худшей зарплате и ничего не делает без подтверждения")
        p.get_by_text("Думаю…").wait_for(state="detached", timeout=60000)
        dlg = p.get_by_role("dialog")
        r.expect(dlg.get_by_text(re.compile(r"21\s?%")).count() > 0, "the plan should show 21%")
        r.pause(2.5)
        r.type(box, "Посоветуй лучший кредит с низким процентом на компьютер 15 млн")
        r.click(r.btn("Отправить", exact=True), 0.3)
        header = p.get_by_text("Предложения банка", exact=True).first
        header.wait_for(timeout=60000)
        r.show(header)
        r.caption("Три предложения из демо-каталога: ★ лучший по стоимости и как сдвинутся цели")
        r.expect(dlg.get_by_role("button", name="Оформить заявку (демо)").count() == 3, "3 offer cards")
        r.expect(dlg.get_by_text(re.compile("★ Лучший по стоимости")).count() >= 1, "best badge")
        r.expect(dlg.get_by_text(re.compile(r"Машина \+\d+ мес")).count() >= 1, "goal delay chips")
        r.pause(2.5)
        r.show(dlg.get_by_text(re.compile("Накопить самому")))
        r.caption("Сравнение: накопить самому — без переплаты. Заявку не оформляем")
        r.pause(2)
        r.expect(not call("GET", "/state").get("credit_applications"), "no credit application must be created")
        r.close_sheets()

    def end():
        p.evaluate(END_CARD_JS, "Goalie — числа считает код, решает человек")
        r.pause(3.5)

    for title, fn in [
        ("1. Главная и стопка подкарт", home),
        ("2. Зарплата: Goalie сам разложил", salary),
        ("3. Guardian: кино остановлено, аптека прошла", guardian),
        ("4. Агент: план цели и кредитный советник", agent),
        ("5. Финальная карточка", end),
    ]:
        r.step(title, fn)


# ---------------- full scenario ----------------
def full_scenario(r: Recorder):
    p = r.page

    def home():
        r.caption("Главный экран: основная карта, общий баланс и стопка подкарт-целей")
        r.pause(2.5)
        r.expect(p.get_by_text(re.compile("^Подкарта$")).count() == 0, "no '+' ghost card in the collapsed stack")
        r.click(p.get_by_text(re.compile("Показать подкарты")))
        r.caption("Подкарты выезжают из-под основной карты, как в кошельке; «+» — в конце списка")
        r.pause(2.5)
        r.expect(p.get_by_text(re.compile("Скрыть подкарты")).count() == 1, "bar should say 'Скрыть' when expanded")
        r.click(p.get_by_text(re.compile("Скрыть подкарты")))
        r.pause(1.2)
        r.expect(p.get_by_text(re.compile("Показать подкарты")).count() == 1, "bar should say 'Показать' when collapsed")

    def create():
        r.click(r.btn("Новая цель").first)
        r.caption("Новая цель: пользователь вводит только название и сумму — процент выбирает агент")
        r.pause(1.5)
        r.type(p.locator("#gname"), "Машина")
        r.type(p.locator("#gamount"), "50000000")
        r.expect(p.get_by_text("Спросить агента").count() == 0, "no 'Спросить агента' link on Create Goal")
        r.caption("Агент считает процент по худшему месяцу зарплаты (переводы не учитываются)…")
        p.get_by_text("Подобрано агентом").wait_for(timeout=15000)
        r.pause(1.5)
        r.caption("Срок «3 года» — агент пересчитывает процент сам")
        r.click(p.get_by_role("radio", name="3 года"))
        p.get_by_text("21% зарплаты").first.wait_for(timeout=15000)
        r.show(p.get_by_text("Подобрано агентом"))
        r.caption("План агента: 21% зарплаты, взнос в худший месяц, срок и лучший случай — только для чтения")
        r.pause(3)
        p.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        r.caption("Карта-превью обновляется вживую: название, срок, процент")
        r.pause(2)

    def issue():
        r.click(r.btn("Создать цель", exact=True))
        r.caption("Подтверждение: деньги в подкарте защищены от импульсных трат")
        r.pause(2.5)
        r.click(r.btn("Понятно, создать"))
        r.caption("Карта выпущена!")
        r.page.wait_for_timeout(300)
        r.expect(r.goal("Машина").get("percent") == 21, "goal should be created at 21% (3-year term)")
        r.pause(2.5)
        r.caption("Детали подкарты: приоритет #2, срок до 1 декабря 2029")
        r.pause(2)
        r.click(r.tab("Главная"))
        r.click(p.get_by_text(re.compile("Показать подкарты")))
        r.caption("Новая подкарта «Машина» в стопке — с приоритетом и датой окончания")
        r.pause(2.5)
        r.click(p.get_by_text(re.compile("Скрыть подкарты")))

    def priority():
        r.click(r.tab("Цели"))
        r.caption("Приоритеты: если денег не хватит, сначала пополняется цель выше")
        r.pause(2)
        r.click(p.get_by_role("button", name="Поднять приоритет: Машина"))
        r.caption("«Машина» теперь #1, «Телефон» — #2")
        r.pause(2.5)
        r.expect(r.goal("Машина").get("priority") == 1, "«Машина» should be priority #1")

    def salary():
        r.close_sheets()
        r.click(r.tab("Ещё"))
        r.show(p.get_by_text("Управление демо"))
        r.caption("Демо: зарплата на 15% ниже обычной (6 375 000)")
        r.click(r.btn(re.compile("^−15%")))
        r.click(r.btn("Зачислить", exact=True), 0.2)
        sheet = p.get_by_role("dialog", name="Goalie разложил зарплату")
        sheet.wait_for(timeout=10000)
        r.caption("Goalie разложил зарплату: аренда, потом цели по приоритету, остаток — на жизнь")
        sheet.wait_for(state="detached", timeout=10000)
        r.click(p.get_by_role("button", name=re.compile("^Советы для вас")))
        r.caption("Агент: «Машина» отстаёт на 2 месяца — предлагает 22% вместо 21%")
        r.pause(3)
        r.click(r.btn("Поставить 22%"))
        r.caption("Подтверждено: срок снова 35 месяцев")
        r.pause(2)
        r.click(r.btn("Закрыть"))

    def transfer():
        r.close_sheets()
        r.click(r.tab("Ещё"))
        r.show(p.get_by_text(re.compile("Симулировать перевод")))
        r.caption("Перевод от близких 2 000 000: план и сроки НЕ меняются — считаем только зарплату")
        r.pause(2)
        r.click(r.btn("Зачислить перевод"))
        r.pause(2.5)
        r.click(p.get_by_role("button", name=re.compile("^Советы для вас")))
        r.caption("Агент предлагает по желанию отложить 22% перевода на цель #1")
        r.pause(3)
        r.click(r.btn(re.compile("^Отложить")))
        r.caption("Подтверждено: 440 000 ушли в «Машину», прогресс вырос, срок прежний")
        r.pause(2)
        r.click(r.btn("Закрыть"))

    def guardian():
        r.close_sheets()
        r.click(r.tab("Ещё"))
        r.show(p.get_by_text(re.compile("Покупка из цели")))
        r.caption("Guardian: покупка в кино (MCC 7832) из денег на «Машину»")
        r.pause(1.5)
        r.click(r.btn("Оплатить картой"))
        p.get_by_text(re.compile("Подождите")).wait_for(timeout=10000)
        r.caption("Стоп: цель отложится на 3 дня, потеря бонуса за ближайший год — 1 045 500 so'm")
        r.pause(3.5)
        r.click(r.btn(re.compile("Подождать до завтра")))
        r.caption("Пауза 24 часа: если желание останется — решим завтра")
        r.pause(2)
        r.click(r.btn("Хорошо"))
        r.click(r.btn("Перемотать на 24 часа"))
        r.click(p.get_by_role("button", name=re.compile("^Советы для вас")))
        r.caption("Прошли сутки — агент спрашивает ещё раз")
        r.pause(2.5)
        r.click(r.btn("Уже не нужно"))
        r.pause(1.5)
        r.click(r.btn("Закрыть"))
        r.caption("Аптека (MCC 5912) — экстренная покупка")
        p.locator('select[aria-label="MCC"]').select_option("5912")
        r.type(p.locator('input[aria-label="amount"]'), "300000")
        r.click(r.btn("Оплатить картой"))
        p.get_by_text("Оплачено без штрафа").wait_for(timeout=10000)
        r.caption("Проходит без штрафа: бонус 22% сохранён, срок не изменился")
        r.pause(3)
        r.click(r.btn("Хорошо"))

    def pin_release():
        r.close_sheets()
        r.click(r.tab("Ещё"))
        r.show(p.get_by_text(re.compile("Покупка из цели")))
        p.locator('select[aria-label="MCC"]').select_option("5812")
        r.type(p.locator('input[aria-label="amount"]'), "100000")
        r.caption("Ресторан из денег на «Машину»: пользователь хочет «Всё равно потратить»")
        r.click(r.btn("Оплатить картой"))
        r.click(r.btn("Всё равно потратить"))
        pin = p.get_by_role("dialog", name="Подтвердите PIN-кодом")
        pin.wait_for(timeout=10000)
        r.caption("Снятие защищённых денег — только с PIN. Без него сервер отклоняет запрос (401)")
        r.pause(2)
        for d in "0000":
            r.click(pin.get_by_role("button", name=d, exact=True), 0.15)
        pin.get_by_text(re.compile("Неверный PIN")).wait_for(timeout=5000)
        r.caption("Неверный PIN — отклонено, осталось 2 попытки (после 3 — блокировка на 60 сек)")
        r.pause(2.5)
        for d in "1234":
            r.click(pin.get_by_role("button", name=d, exact=True), 0.15)
        p.get_by_text(re.compile("Потрачено из")).wait_for(timeout=8000)
        r.caption("PIN верный — снятие выполнено")
        r.pause(1.8)
        r.click(r.btn("Хорошо"))
        r.click(p.get_by_role("button", name=re.compile("^Советы для вас")))
        r.caption("Уведомление: «Вы подтвердили снятие… Это были не вы? Отменить» — 24 часа")
        r.pause(3)
        r.click(r.btn("Отменить", exact=True))
        r.caption("Отменено: деньги вернулись в цель, бонус за дисциплину восстановлен")
        r.pause(2.2)
        r.expect(r.goal("Машина").get("disciplined") is True, "cancel should restore the discipline bonus")
        r.click(r.btn("Закрыть"))

    def credit():
        r.click(r.tab("Главная"))
        r.click(r.btn("Кредит подобрать"))
        r.caption("Кредитный советник: вопрос уже подставлен в чат")
        r.pause(2)
        r.click(r.btn("Отправить"))
        r.caption("Агент ранжирует демо-предложения банка кодом и объясняет результат…")
        # exact match = the cards header only (the AI's own reply text may contain the same words)
        header = p.get_by_text("Предложения банка", exact=True).first
        header.wait_for(timeout=60000)
        dlg = p.get_by_role("dialog")
        r.show(header)
        r.caption("Три карточки: лучший по стоимости, меньший платёж — и как сдвинутся цели")
        r.pause(3.5)
        r.click(dlg.get_by_role("button", name="Подробнее").first)
        r.caption("Подробнее: проценты, комиссия, полная стоимость")
        r.pause(2.5)
        r.show(dlg.get_by_text(re.compile("Накопить самому")))
        r.caption("Сравнение: накопить самому — без переплаты")
        r.pause(2.5)
        r.click(dlg.get_by_role("button", name="Оформить заявку (демо)").first)
        r.caption("Заявка только после подтверждения — деньги не перечисляются")
        r.pause(3)
        r.click(r.btn("Подтверждаю, отправить"))
        r.pause(2)
        r.close_sheets()

    def obligations():
        r.click(r.tab("Платежи"))
        r.caption("Обязательства: аренда уже отложена из зарплаты")
        r.pause(2)
        r.click(r.btn(re.compile("Добавить платёж")))
        r.type(p.locator("#oname"), "Долг брату")
        r.type(p.locator("#oamount"), "1500000")
        r.type(p.locator("#odate"), "05122026")  # localized field: shows 05.12.2026
        r.expect(p.locator("#odate").input_value() == "05.12.2026", "date field should show dd.mm.yyyy")
        r.click(r.btn("Добавить", exact=True))
        r.caption("Новый долг через 3 дня — резерва не хватает 1 500 000")
        r.pause(2.5)
        r.click(p.get_by_role("button", name=re.compile("^Советы для вас")))
        r.caption("Агент предлагает пополнить резерв с основной карты")
        r.pause(2.5)
        r.click(r.btn(re.compile("^Перевести")))
        r.pause(1.5)
        r.click(r.btn("Закрыть"))
        rent = p.locator("section", has_text="Аренда квартиры")
        r.show(rent)
        r.click(rent.get_by_role("button", name="Оплатить"))
        r.caption("Оплата аренды — только с подтверждением")
        r.pause(2.5)
        r.click(r.btn("Да, оплатить"))
        r.pause(2)

    def language():
        r.click(r.tab("Ещё"))
        r.caption("Язык: русский / узбекский — все тексты, включая ответы сервера")
        r.pause(1.5)
        r.click(p.get_by_role("radio", name="O'zbekcha"))
        r.pause(1.5)
        r.click(r.tab("Asosiy"))
        r.caption("Interfeys o'zbek tilida — Asosiy ekran")
        r.pause(3)
        p.evaluate(END_CARD_JS, "Goalie — числа считает код, решает человек")
        r.pause(3)

    for title, fn in [
        ("1. Главный экран и стопка подкарт", home),
        ("2. Создание цели: агент считает процент", create),
        ("3. Выпуск карты и новая подкарта", issue),
        ("4. Смена приоритетов", priority),
        ("5. Зарплата ниже обычной: пересчёт", salary),
        ("6. Перевод от близких: план не меняется", transfer),
        ("7. Guardian: кино и аптека", guardian),
        ("7b. PIN: снятие из цели и отмена", pin_release),
        ("8. Кредитный советник", credit),
        ("9. Обязательства", obligations),
        ("10. Переключение языка", language),
    ]:
        r.step(title, fn)


# ---------------- English narrated video (scenes timed to the narration audio) ----------------
AUDIO = ROOT / "audio"
NARRATION = ROOT / "narration.json"


def seed_en():
    """Same story as seed_short, created in English: «Car» #1 (some progress), «Phone» #2, rent due in 6 days."""
    post("/demo/reset")
    car = call("POST", "/subcards", {"name": "Car", "goal_amount": 50_000_000, "term_months": 36}, lang="en")
    call("POST", "/subcards/reorder", {"ids": [car["id"], "goal_phone"]}, lang="en")
    call("POST", "/demo/transfer-in", {"amount": 10_000_000, "source": "Family"}, lang="en")
    for prop in call("GET", "/agent/inbox", lang="en"):
        if prop["kind"] == "transfer_save" and prop["status"] == "pending":
            call("POST", f"/agent/proposals/{prop['id']}/confirm", {}, lang="en")
    st = call("GET", "/state", lang="en")
    names = [(g["name"], g["priority"]) for g in st["goals"] if g["status"] == "active"]
    assert names == [("Car", 1), ("Phone", 2)], names
    assert any(o["due_in_days"] <= 7 and not o.get("paid") for o in st["obligations"])


def en_scenario(r: Recorder):
    p = r.page
    durs = json.loads((AUDIO / "durations.json").read_text(encoding="utf-8"))

    def home():
        r.caption("Home: the main card and goal subcards, «Car» #1 and «Phone» #2")
        r.pause(2)
        r.click(p.get_by_text(re.compile("Show subcards")))
        r.caption("Subcards slide out from under the main card, each with progress and priority")
        r.pause(2)
        r.click(p.get_by_text(re.compile("Hide subcards")))

    def salary():
        r.click(r.tab("More"))
        r.show(p.get_by_text("Demo controls"))
        r.caption("Demo: a salary arrives")
        r.click(r.btn(re.compile("^Usual")))
        before = r.goal("Car").get("saved", 0)
        r.click(r.btn("Credit it", exact=True), 0.2)
        sheet = p.get_by_role("dialog", name="Goalie split your salary")
        sheet.wait_for(timeout=10000)
        r.caption("Salary arrived: Goalie split it for you")
        p.wait_for_timeout(2600)
        labels = [x.strip() for x in sheet.locator("li .font-semibold.truncate").all_inner_texts()]
        r.expect(labels == ["Apartment rent", "Car", "Phone", "Main card"],
                 f"waterfall order should be rent -> #1 -> #2 -> main card, got {labels}")
        sheet.wait_for(state="detached", timeout=8000)
        r.expect(r.goal("Car").get("saved", 0) > before, "«Car» should grow after the salary")
        r.click(p.get_by_text(re.compile("Show subcards")))
        r.caption("Subcard progress grew, with no action from the user")
        r.pause(1.5)
        r.click(p.get_by_text(re.compile("Hide subcards")))

    def guardian():
        r.click(r.tab("More"))
        r.show(p.get_by_text(re.compile("Purchase from a goal")))
        r.caption("A cinema purchase (MCC 7832) from the «Car» money")
        r.expect("Car" in p.locator('select[aria-label="source"] option:checked').inner_text(), "source should be «Car»")
        p.locator('select[aria-label="MCC"]').select_option("7832")
        r.type(p.locator('input[aria-label="amount"]'), "150000")
        r.click(r.btn("Pay by card"))
        p.get_by_text(re.compile("Wait: this is money")).wait_for(timeout=10000)
        r.caption("Stop card: the cost in days and in bonus")
        r.pause(2.5)
        r.click(r.btn(re.compile("Wait until tomorrow")))
        r.pause(1)
        r.click(r.btn("OK", exact=True))
        p.locator('select[aria-label="MCC"]').select_option("5912")
        r.type(p.locator('input[aria-label="amount"]'), "300000")
        r.caption("Pharmacy (MCC 5912): an emergency purchase")
        r.click(r.btn("Pay by card"))
        p.get_by_text("Paid with no penalty").wait_for(timeout=10000)
        r.caption("Impulse stopped, emergency untouched")
        r.pause(2)
        r.click(r.btn("OK", exact=True))

    box = p.get_by_role("textbox", name="Type a question…")

    def plan():
        r.click(r.tab("Home"))
        r.click(r.btn("Search or ask AI"))
        r.type(box, "I want to save 50 million for a car in 3 years")
        r.click(r.btn("Send", exact=True), 0.3)
        r.caption("The agent plans on the worst salary and does nothing without confirmation")
        p.get_by_text("Thinking…").wait_for(state="detached", timeout=60000)
        # a confirmation card, nothing created (the percent itself depends on the goals that already exist)
        r.expect(p.get_by_role("dialog").get_by_role("button", name="Create goal").count() >= 1, "a goal proposal card")
        r.expect(p.get_by_role("dialog").get_by_text(re.compile("[А-Яа-яЁё]")).count() == 0, "the reply must be English")
        r.pause(1.5)

    def credit():
        dlg = p.get_by_role("dialog")
        r.type(box, "Recommend the best low-interest loan for a computer, 15 million")
        r.click(r.btn("Send", exact=True), 0.3)
        header = p.get_by_text("Bank offers", exact=True).first
        header.wait_for(timeout=60000)
        r.show(header)
        r.caption("Three demo offers: ★ best by cost, and how each one moves your goals")
        r.expect(dlg.get_by_role("button", name="Apply (demo)").count() == 3, "3 offer cards")
        r.expect(dlg.get_by_text(re.compile("★ Best by cost")).count() >= 1, "best badge")
        r.expect(dlg.get_by_text(re.compile(r"Car \+\d+ mo")).count() >= 1, "goal delay chips")
        r.pause(2.5)
        r.show(dlg.get_by_text(re.compile("Save it yourself")))
        r.caption("Compared with saving it yourself: no overpayment. No application is sent")
        r.pause(2)
        r.expect(not call("GET", "/state").get("credit_applications"), "no credit application must be created")

    def end():
        r.close_sheets()
        p.evaluate(END_CARD_JS, "Goalie: code calculates, AI explains, you decide.")

    for sid, title, fn in [
        ("home", "1. Home and subcard stack", home),
        ("salary", "2. Salary: Goalie splits it", salary),
        ("guardian", "3. Guardian: cinema stopped, pharmacy passes", guardian),
        ("plan", "4. Agent: goal plan", plan),
        ("credit", "5. Agent: credit advisor", credit),
        ("end", "6. End card", end),
    ]:
        r.scene(sid, title, fn, durs[sid])


def mux_narration(info: dict) -> None:
    """One audio track: each scene's mp3 delayed to the scene's start time in the video, then H.264 + AAC."""
    rec, ff = info["rec"], ffmpeg_exe()
    silent = OUT / "_en_silent.mp4"
    shutil.move(info["mp4"], silent)
    inputs, chains, labels = [], [], []
    for i, (sid, start) in enumerate(rec.scene_starts.items(), 1):
        inputs += ["-i", str(AUDIO / "en" / f"{sid}.mp3")]
        ms = max(0, int(round(start * 1000)))
        chains.append(f"[{i}:a]aresample=48000,adelay={ms}|{ms}[a{i}]")
        labels.append(f"[a{i}]")
    graph = ";".join(chains) + f";{''.join(labels)}amix=inputs={len(labels)}:normalize=0,apad[aout]"
    res = subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(silent), *inputs, "-filter_complex", graph,
                          "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                          "-shortest", "-movflags", "+faststart", str(info["mp4"])], capture_output=True, text=True)
    if res.returncode != 0:
        rec.issues.append(f"audio mux failed: {res.stderr[-300:]}")
        shutil.move(silent, info["mp4"])
        return
    silent.unlink()
    info["size_mb"] = info["mp4"].stat().st_size / 2**20
    info["muxed"] = True


def narration_section(info: dict) -> list[str]:
    c = json.loads(NARRATION.read_text(encoding="utf-8"))
    src_path = AUDIO / "en" / "sources.json"
    src = json.loads(src_path.read_text(encoding="utf-8")) if src_path.exists() else {}
    durs = json.loads((AUDIO / "durations.json").read_text(encoding="utf-8"))
    rec = info["rec"]
    out = ["## English narration", "",
           f"- Voice used: **`{c['voice']}`** — {c['voice_options'].get(c['voice'], '')}",
           "- Alternatives (samples in `qa/audio/samples/`, see its README):"]
    out += [f"  - `{k}` — {v}" for k, v in c["voice_options"].items() if k != c["voice"]]
    out += ["- Audio track: " + ("AAC (mono), each scene's clip placed at the scene's start time" if info.get("muxed")
                                 else "**not muxed** (see problems)"), "",
            "| Scene | Engine | Audio | Starts at | Scene length | Text |", "|---|---|---|---|---|---|"]
    by_id = {s["id"]: s["text_en"] for s in c["scenes"]}
    for st in rec.steps:
        sid = st.get("scene")
        if not sid:
            continue
        s = src.get(sid, {})
        eng = "Speko" if s.get("engine") == "speko" else f"edge-tts (fallback: {s.get('reason')})" if s.get("fallback") \
            else s.get("engine", "?")
        out.append(f"| {sid} | {eng} | {durs[sid]:.1f} s | {fmt(st['start'])} | {st['end'] - st['start']:.1f} s | "
                   f"{by_id[sid]} |")
    fb = [k for k, v in src.items() if v.get("fallback")]
    out += ["", f"- Speko scenes: {sum(1 for v in src.values() if v.get('engine') == 'speko')} of {len(c['scenes'])}; "
            f"fallback (edge-tts): {', '.join(fb) if fb else 'none'}.", ""]
    out += ["### Regenerate with another voice", "",
            "1. Set `\"voice\"` in `qa/narration.json` to one of the `voice_options` keys.",
            "2. Make the scene audio:",
            "   - edge-tts voice (fully scripted, no key):", "",
            "     ```powershell", "     qa\\.venv\\Scripts\\python.exe qa\\narrate.py build", "     ```", "",
            "   - Speko voice: Speko is reached through its MCP connector (no Speko key is stored in this "
            "repo). Call audio.synthesize once per scene with the voice in qa/narration.json and import each saved result with "
            "`qa\\.venv\\Scripts\\python.exe qa\\narrate.py import <scene> <result.json>`, then runs `narrate.py build` "
            "(any scene without Speko audio falls back to edge-tts and is marked as such).",
            "3. Re-record and mux (backend and frontend running):", "",
            "   ```powershell", "   qa\\.venv\\Scripts\\python.exe qa\\record_demo.py en", "   ```", ""]
    return out


# ---------------- post-processing ----------------
def ffmpeg_exe() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return None


def fmt(sec: float) -> str:
    return f"{int(sec // 60)}:{sec % 60:04.1f}"


VIDEOS = {
    "short": {"title": "Короткое видео (питч)", "seed": seed_short, "scenario": short_scenario,
              "file": "demo_short.mp4", "target": (80, 95)},
    "full": {"title": "Полное видео (все функции)", "seed": seed_full, "scenario": full_scenario,
             "file": "demo_full.mp4", "target": None},
    "en": {"title": "English narrated video", "seed": seed_en, "scenario": en_scenario,
           "file": "demo_en.mp4", "target": (80, 95), "lang": "en"},
}
READY_TEXT = {"ru": "Общий баланс", "en": "Total balance"}


def record(name: str, mode: str) -> dict:
    """Record one scenario into qa/video/<file>; returns its steps, problems and output info."""
    cfg = VIDEOS[name]
    raw_dir = OUT / f"_raw_{name}"
    cfg["seed"]()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        lang = cfg.get("lang", "ru")
        ctx = browser.new_context(viewport=VIEW, device_scale_factor=2, is_mobile=False, has_touch=False,
                                  locale="en-US" if lang == "en" else "ru-RU", record_video_dir=str(raw_dir),
                                  record_video_size=VIEW)
        ctx.add_init_script(OVERLAY_JS)
        ctx.add_init_script(f"try {{ localStorage.setItem('lang', '{lang}') }} catch (e) {{}}")  # UI language, no reload
        t0 = time.monotonic()  # the video starts when the page is created
        page = ctx.new_page()
        rec = Recorder(page, PAUSE_SCALE[name], lang, t0)
        page.goto(APP)
        page.get_by_text(READY_TEXT[lang]).wait_for(timeout=15000)
        page.mouse.move(195, 420)
        cfg["scenario"](rec)
        video_path = page.video.path()
        ctx.close()
        browser.close()

    webm = OUT / f"_{name}.webm"
    shutil.move(video_path, webm)
    shutil.rmtree(raw_dir, ignore_errors=True)
    total = rec.steps[-1]["end"] if rec.steps else 0
    mp4 = OUT / cfg["file"]
    info = {"name": name, "cfg": cfg, "rec": rec, "total": total, "mp4": None, "size_mb": None}

    ff = ffmpeg_exe()
    if not ff:
        rec.issues.append("ffmpeg not available: no mp4 and no keyframes (raw video kept as webm)")
        shutil.move(webm, OUT / f"demo_{name}.webm")
        return info
    # H.264 / yuv420p, upscaled 2x (the page renders at deviceScaleFactor 2); raise CRF until it fits MAX_MB
    for crf in (22, 26, 30, 34):
        res = subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(webm),
                              "-vf", f"scale={VIEW['width'] * 2}:{VIEW['height'] * 2}:flags=lanczos",
                              "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(crf), "-preset", "medium",
                              "-movflags", "+faststart", "-an", str(mp4)], capture_output=True, text=True)
        if res.returncode != 0:
            rec.issues.append(f"mp4 conversion failed: {res.stderr[-300:]}")
            shutil.move(webm, OUT / f"demo_{name}.webm")
            return info
        size = mp4.stat().st_size / 2**20
        if size < MAX_MB:
            break
    info.update(mp4=mp4, size_mb=size, crf=crf)
    if size >= MAX_MB:
        rec.issues.append(f"{mp4.name} is {size:.1f} MB (limit {MAX_MB} MB) even at CRF {crf}")
    webm.unlink()
    if name == "en":
        mux_narration(info)
    for i, s in enumerate(rec.steps, 1):
        t = max(0.0, s["end"] - 0.8)  # keyframe near the end of the step: the result is on screen
        if name in ("short", "en") and i == 2:
            t = s["start"] + (s["end"] - s["start"]) * 0.45  # salary: the split sheet itself, not the stack after it
        subprocess.run([ff, "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(mp4), "-frames:v", "1",
                        str(FRAMES / (f"en_{s['scene']}.png" if s.get("scene") else f"{name}_step{i:02d}.png"))],
                       capture_output=True)
    return info


def report_section(info: dict) -> list[str]:
    rec, cfg = info["rec"], info["cfg"]
    tgt = cfg["target"]
    length = fmt(info["total"])
    if tgt:
        inside = tgt[0] <= info["total"] <= tgt[1]
        length += f" (target {tgt[0]}–{tgt[1]} s: {'OK' if inside else 'OUT OF RANGE'})"
        if not inside:
            rec.issues.append(f"length {info['total']:.0f} s is outside the {tgt[0]}–{tgt[1]} s target")
    out = [f"## {cfg['title']} — `{cfg['file']}`", "",
           f"- Length: about {length} (steps measured from page start; the video starts ~0.5 s earlier)",
           f"- File: " + (f"`{info['mp4'].name}` — H.264" + (" + AAC" if info.get("muxed") else "")
                          + f", yuv420p, 780×1688, CRF {info['crf']}, {info['size_mb']:.1f} MB"
                          if info["mp4"] else "no mp4 (see problems)"),
           f"- Reading pauses ×{PAUSE_SCALE[info['name']]}", "",
           "| # | Step | Start | End | Keyframe | Result |", "|---|---|---|---|---|---|"]
    for i, s in enumerate(rec.steps, 1):
        res = "OK" if s["ok"] else f"FAILED — {s['error']} (screenshot `failures/{info['name']}_step{i:02d}.png`)"
        frame = f"en_{s['scene']}.png" if s.get("scene") else f"{info['name']}_step{i:02d}.png"
        out.append(f"| {i} | {s['title']} | {fmt(s['start'])} | {fmt(s['end'])} | `frames/{frame}` | {res} |")
    out += ["", "**Problems found**", ""]
    probs = [f"- Step failed: {s['title']} — {s['error']}" for s in rec.steps if not s["ok"]]
    probs += [f"- {x}" for x in rec.issues]
    # the wrong-PIN attempt in the full video is intentional: report it as expected, not as a problem
    expected = [x for x in rec.bad_requests if "401" in x and "/auth/step-up" in x]
    probs += [f"- Console error {x}" for x in rec.console_errors
              if not (expected and "401" in x and "Failed to load resource" in x)]
    probs += [f"- Request {x}" for x in rec.bad_requests if x not in expected]
    if expected:
        out.append(f"- Expected (not a problem): {len(expected)} × HTTP 401 on /auth/step-up — the deliberate wrong PIN")
    out += probs or ["- None detected automatically (no failed steps, console errors, failed requests or horizontal overflow)."]
    return out + [""]


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    names = ["short", "full"] if which == "both" else [which]
    if which not in ("short", "full", "both", "en"):
        print("usage: record_demo.py [short|full|both|en]")
        return 2
    FRAMES.mkdir(parents=True, exist_ok=True)
    for name in names:  # replace only this run's outputs; other videos (and their report sections) stay
        for f in [OUT / VIDEOS[name]["file"], OUT / f"report_{name}.md", *FRAMES.glob(f"{name}_*.png"),
                  *(OUT / "failures").glob(f"{name}_*.png")]:
            f.unlink(missing_ok=True)
    if "en" in names:
        if not (ROOT / "audio" / "durations.json").exists():
            print("Run qa\\narrate.py build first (qa/audio/durations.json is missing).")
            return 2
    mode = agent_mode()
    print("Agent mode:", mode)

    global FAIL_DIR
    results = []
    for name in names:
        print(f"\n===== {name} =====")
        FAIL_DIR = OUT / "failures"
        results.append(record(name, mode))
        # failure screenshots are numbered per run: prefix them with the video name
        for f in (FAIL_DIR.glob("step*.png") if FAIL_DIR.exists() else []):
            f.rename(FAIL_DIR / f"{name}_{f.name}")
        sec = report_section(results[-1]) + (narration_section(results[-1]) if name == "en" else [])
        (OUT / f"report_{name}.md").write_text("\n".join(sec) + "\n", encoding="utf-8")
    post("/demo/reset")  # leave the app clean for a live demo

    lines = ["# Goalie — demo video report", "",
             f"- Recorded: {time.strftime('%Y-%m-%d %H:%M')}",
             f"- Agent mode: **{mode}**",
             f"- Viewport 390×844 @ deviceScaleFactor 2 (mp4 is 780×1688), fake cursor, Russian caption bar "
             f"(moves to the top while a bottom sheet is open), {SLOW_MO} ms pause per click, typing {TYPE_DELAY} ms/char",
             "- Keyframes: one per scenario step in `frames/` (`short_stepNN.png`, `full_stepNN.png`)", ""]
    for name in ("short", "full", "en"):
        part = OUT / f"report_{name}.md"
        if part.exists():
            lines += part.read_text(encoding="utf-8").splitlines()
    lines += ["## Re-record", "", "Start backend and frontend first (see README), then from the project root:", "",
              "```powershell", "qa\\.venv\\Scripts\\python.exe qa\\record_demo.py          # both videos",
              "qa\\.venv\\Scripts\\python.exe qa\\record_demo.py short    # only demo_short.mp4",
              "qa\\.venv\\Scripts\\python.exe qa\\record_demo.py en       # demo_en.mp4 with narration "
              "(run qa\\narrate.py build first)", "```", "",
              "First-time setup:", "", "```powershell",
              "python -m venv qa\\.venv; qa\\.venv\\Scripts\\python.exe -m pip install -r qa\\requirements.txt; "
              "qa\\.venv\\Scripts\\python.exe -m playwright install chromium", "```"]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---- zip (no node_modules, .env, keys or signed links) ----
    def safe(f: Path) -> bool:
        return f.is_file() and "node_modules" not in f.parts and not f.name.startswith(".env") \
            and not f.name.startswith("_")
    zpath = ROOT / ("demo_video_en.zip" if which == "en" else "demo_video.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in OUT.rglob("*"):
            if safe(f):
                z.write(f, Path("video") / f.relative_to(OUT))
        if which == "en":
            for f in (ROOT / "audio" / "samples").rglob("*"):
                if safe(f):
                    z.write(f, Path("audio") / "samples" / f.relative_to(ROOT / "audio" / "samples"))
    for info in results:
        bad = sum(not s["ok"] for s in info["rec"].steps)
        print(f"{info['name']}: {fmt(info['total'])}, mp4={info['mp4']}, {info['size_mb'] or 0:.1f} MB, "
              f"failed steps {bad}/{len(info['rec'].steps)}")
    print(f"report={OUT / 'report.md'}, zip={zpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
