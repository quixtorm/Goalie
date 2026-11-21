"""Automated demo video of the full Goalie scenario (QA tooling only — does not change the app).

Prereqs: backend on http://127.0.0.1:8000 (DEMO_MODE=true) and frontend on http://127.0.0.1:5173 running.
Run:     qa\\.venv\\Scripts\\python.exe qa\\record_demo.py
Output:  qa/video/demo.webm, demo.mp4, frames/*.png, report.md, and qa/demo_video.zip
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
PAUSE_SCALE = 0.58       # all reading pauses x0.58 -> full scenario (11 steps) under 3 minutes
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
    def __init__(self, page: Page):
        self.page = page
        self.t0 = time.monotonic()
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
        self.page.wait_for_timeout(int(sec * PAUSE_SCALE * 1000))

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
        req = urllib.request.Request(API + "/state", headers={"X-Lang": "ru"})
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
                self.click(self.tab(re.compile("Главная|Asosiy")), 0.5)
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
    return "LLM (Claude via API key)" if has_key else "fallback (no API key)"


# ---------------- scenario ----------------
def scenario(r: Recorder):
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
        r.click(r.btn("Зачислить", exact=True))
        r.caption("Сначала аренда, потом цели по приоритету, остаток — на жизнь")
        r.pause(2.5)
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
        r.caption("Goalie — демо завершено")
        r.pause(2.5)

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


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    FRAMES.mkdir(parents=True)
    raw_dir = OUT / "_raw"
    mode = agent_mode()
    print("Agent mode:", mode)
    post("/demo/reset")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=VIEW, device_scale_factor=2, is_mobile=False, has_touch=False,
                                  locale="ru-RU", record_video_dir=str(raw_dir), record_video_size=VIEW)
        ctx.add_init_script(OVERLAY_JS)
        ctx.add_init_script("try { localStorage.setItem('lang', 'ru') } catch (e) {}")  # start in Russian, no reload
        page = ctx.new_page()
        rec = Recorder(page)
        page.goto(APP)
        page.get_by_text("Общий баланс").wait_for(timeout=15000)
        page.mouse.move(195, 420)
        scenario(rec)
        video_path = page.video.path()
        ctx.close()
        browser.close()

    webm = OUT / "demo.webm"
    shutil.move(video_path, webm)
    shutil.rmtree(raw_dir, ignore_errors=True)
    total = rec.steps[-1]["end"] if rec.steps else 0

    ff = ffmpeg_exe()
    mp4_ok = False
    if ff:
        res = subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(webm),
                              "-vf", f"scale={VIEW['width'] * 2}:{VIEW['height'] * 2}:flags=lanczos",
                              "-c:v", "libx264", "-pix_fmt", "yuv420p",
                              "-crf", "22", "-preset", "medium", "-movflags", "+faststart", str(OUT / "demo.mp4")],
                             capture_output=True, text=True)
        mp4_ok = res.returncode == 0
        if not mp4_ok:
            rec.issues.append(f"mp4 conversion failed: {res.stderr[-300:]}")
        src = OUT / "demo.mp4" if mp4_ok else webm
        for i, s in enumerate(rec.steps, 1):
            t = max(0.0, s["end"] - 0.8)  # keyframe near the end of the step: the result is on screen
            subprocess.run([ff, "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1",
                            str(FRAMES / f"step{i:02d}.png")], capture_output=True)
    else:
        rec.issues.append("ffmpeg not available: no mp4 and no keyframes")

    # ---- report ----
    lines = ["# Goalie — demo video report", "",
             f"- Recorded: {time.strftime('%Y-%m-%d %H:%M')}",
             f"- Agent mode: **{mode}**",
             f"- Length: about {fmt(total)} (steps measured from page start; the video starts ~0.5 s earlier)",
             f"- Viewport 390×844 @2x (mp4 upscaled to 780×1688), {SLOW_MO} ms pause per click, "
             f"typing {TYPE_DELAY} ms/char, reading pauses ×{PAUSE_SCALE} (≈1.1–2.6 s)",
             f"- Files: `demo.webm`" + (", `demo.mp4` (H.264, yuv420p)" if mp4_ok else "") + ", `frames/stepNN.png`", "",
             "## Steps", "", "| # | Step | Start | End | Result |", "|---|---|---|---|---|"]
    for i, s in enumerate(rec.steps, 1):
        res = "OK" if s["ok"] else f"FAILED — {s['error']} (screenshot `failures/step{i:02d}.png`)"
        lines.append(f"| {i} | {s['title']} | {fmt(s['start'])} | {fmt(s['end'])} | {res} |")
    lines += ["", "## Problems found", ""]
    probs = [f"- Step failed: {s['title']} — {s['error']}" for s in rec.steps if not s["ok"]]
    probs += [f"- {x}" for x in rec.issues]
    # the wrong-PIN attempt in step 7b is intentional: report it as expected, not as a problem
    expected = [x for x in rec.bad_requests if "401" in x and "/auth/step-up" in x]
    probs += [f"- Console error {x}" for x in rec.console_errors
              if not (expected and "401" in x and "Failed to load resource" in x)]
    probs += [f"- Request {x}" for x in rec.bad_requests if x not in expected]
    if expected:
        lines.append(f"- Expected (not a problem): {len(expected)} × HTTP 401 on /auth/step-up — the deliberate wrong PIN in step 7b")
    lines += probs or ["- None detected automatically (no failed steps, console errors, failed requests or horizontal overflow)."]
    lines += ["", "## Re-record", "", "Start backend and frontend first (see README), then from the project root:", "",
              "```powershell", "qa\\.venv\\Scripts\\python.exe qa\\record_demo.py", "```", "",
              "First-time setup:", "", "```powershell",
              "python -m venv qa\\.venv; qa\\.venv\\Scripts\\python.exe -m pip install -r qa\\requirements.txt; "
              "qa\\.venv\\Scripts\\python.exe -m playwright install chromium", "```"]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---- zip (no node_modules, .env or keys) ----
    zpath = ROOT / "demo_video.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in OUT.rglob("*"):
            if f.is_file() and "node_modules" not in f.parts and not f.name.startswith(".env"):
                z.write(f, Path("video") / f.relative_to(OUT))
    print(f"\nDone: {webm} ({fmt(total)}), mp4={mp4_ok}, report={OUT / 'report.md'}, zip={zpath}")
    print(f"Failed steps: {sum(not s['ok'] for s in rec.steps)} / {len(rec.steps)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
