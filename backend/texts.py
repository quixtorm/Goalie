"""All user-facing server text in Russian and Uzbek (Latin).

The language of the current request lives in a contextvar (set by main.py from the X-Lang header or the chat body).
Stored things (proposals, transactions) keep a message *key + params* — msg(...) — and are rendered at view time,
so switching language re-renders them.

Param naming does the formatting: *_sum -> money, *_date -> date, *_months / *_days -> plural with unit.
A param that is msg(...) or a {"ru":..,"uz":..} dict is rendered in the current language.
"""
from __future__ import annotations

from contextvars import ContextVar
from datetime import date

LANG: ContextVar[str] = ContextVar("lang", default="ru")


def set_lang(lang: str | None) -> None:
    LANG.set("uz" if lang == "uz" else "ru")


def cur() -> str:
    return LANG.get()


# ---------- formatting ----------
MONTHS_GEN = {
    "ru": ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября",
           "декабря"],
    "uz": ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr",
           "dekabr"],
}


def uzs(amount: int) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}{abs(int(amount)):,}".replace(",", " ") + " so'm"


def fdate(d: date | str, lang: str | None = None) -> str:
    lang = lang or cur()
    if isinstance(d, str):
        d = date.fromisoformat(d)
    m = MONTHS_GEN[lang][d.month - 1]
    return f"{d.day}-{m} {d.year}" if lang == "uz" else f"{d.day} {m} {d.year}"


def _ru_plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return one
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return few
    return many


def fmonths(n: int, lang: str | None = None) -> str:
    return f"{n} oy" if (lang or cur()) == "uz" else f"{n} {_ru_plural(n, 'месяц', 'месяца', 'месяцев')}"


def fdays(n: int, lang: str | None = None) -> str:
    return f"{n} kun" if (lang or cur()) == "uz" else f"{n} {_ru_plural(n, 'день', 'дня', 'дней')}"


# ---------- dictionary: key -> (ru, uz) ----------
T: dict[str, tuple[str, str]] = {
    # errors
    "err_income_needed": ("Укажите ваш ежемесячный доход", "Oylik daromadingizni kiriting"),
    "err_income_positive": ("Доход должен быть больше нуля", "Daromad noldan katta bo'lishi kerak"),
    "err_term": ("Срок должен быть от 1 до {max} месяцев", "Muddat 1 dan {max} oygacha bo'lishi kerak"),
    "err_total_pct": ("Сумма процентов по целям не может быть больше {max}%",
                      "Maqsadlar bo'yicha foizlar yig'indisi {max}% dan oshmasligi kerak"),
    "err_max_goals": ("Можно иметь не больше {max} целей", "{max} tadan ortiq maqsad bo'lishi mumkin emas"),
    "err_goal_amount": ("Сумма цели должна быть больше нуля", "Maqsad summasi noldan katta bo'lishi kerak"),
    "err_min_pct": ("Процент должен быть не меньше {min}%", "Foiz kamida {min}% bo'lishi kerak"),
    "err_credit_amount": ("Сумма кредита должна быть больше нуля", "Kredit summasi noldan katta bo'lishi kerak"),
    "err_rate_negative": ("Ставка не может быть отрицательной", "Foiz stavkasi manfiy bo'lishi mumkin emas"),
    "err_goal_not_found": ("Цель не найдена", "Maqsad topilmadi"),
    "err_goal_not_ready": ("Цель ещё не накоплена", "Maqsad hali yig'ilmagan"),
    "err_goal_cant_close": ("Эту цель нельзя закрыть", "Bu maqsadni yopib bo'lmaydi"),
    "err_reorder": ("Список целей не совпадает с активными целями", "Maqsadlar ro'yxati faol maqsadlarga mos kelmaydi"),
    "err_obl_not_found": ("Обязательство не найдено", "Majburiyat topilmadi"),
    "err_amount_positive": ("Сумма должна быть больше нуля", "Summa noldan katta bo'lishi kerak"),
    "err_date_past": ("Дата платежа уже прошла", "To'lov sanasi o'tib ketgan"),
    "err_topup": ("Пополнять нечего или на основной карте нет денег",
                  "To'ldirish shart emas yoki asosiy kartada pul yo'q"),
    "err_already_paid": ("Уже оплачено", "Allaqachon to'langan"),
    "err_not_enough": ("Не хватает {short_sum} для оплаты", "To'lov uchun {short_sum} yetmaydi"),
    "err_goal_unavailable": ("Эта цель сейчас недоступна", "Bu maqsad hozir mavjud emas"),
    "err_source_not_found": ("Источник не найден", "Manba topilmadi"),
    "err_only_in": ("В «{name}» только {avail_sum}", "«{name}» da faqat {avail_sum}"),
    "err_purchase_not_found": ("Покупка не найдена", "Xarid topilmadi"),
    "err_already_resolved": ("Уже решено", "Allaqachon hal qilingan"),
    "err_main_not_enough": ("На основной карте не хватит денег до зарплаты", "Asosiy kartada maoshgacha pul yetmaydi"),
    "err_option_unavailable": ("Этот вариант сейчас недоступен", "Bu variant hozir mavjud emas"),
    "err_need_confirm_obl": ("Нужно подтверждение: это деньги на обязательный платёж",
                             "Tasdiqlash kerak: bu majburiy to'lov uchun pul"),
    "err_money_insufficient": ("Денег уже недостаточно", "Pul endi yetarli emas"),
    "err_prop_not_found": ("Предложение не найдено", "Taklif topilmadi"),
    "err_prop_done": ("Это предложение уже обработано", "Bu taklif allaqachon ko'rib chiqilgan"),
    "err_no_option": ("Нет такого варианта", "Bunday variant yo'q"),
    "err_unknown_action": ("Неизвестное действие", "Noma'lum amal"),
    "err_salary_positive": ("Сумма зарплаты должна быть больше нуля", "Maosh summasi noldan katta bo'lishi kerak"),
    "err_need_confirm": ("Нужно подтверждение", "Tasdiqlash kerak"),
    "err_check_amount_pct": ("Проверьте сумму и процент", "Summa va foizni tekshiring"),
    "err_check_amount_term": ("Проверьте сумму и срок", "Summa va muddatni tekshiring"),
    "err_not_found": ("Не найдено", "Topilmadi"),
    "err_bad_input": ("Проверьте введённые данные", "Kiritilgan ma'lumotlarni tekshiring"),
    "err_internal": ("Что-то пошло не так. Попробуйте ещё раз.", "Nimadir xato ketdi. Qayta urinib ko'ring."),
    "err_rate_limit": ("Слишком много сообщений. Подождите минуту.", "Xabarlar juda ko'p. Bir daqiqa kuting."),
    "err_bad_calc_data": ("Неверные данные для расчёта", "Hisoblash uchun ma'lumotlar noto'g'ri"),
    "err_unknown_tool": ("Неизвестный инструмент", "Noma'lum vosita"),
    # proposals
    "p_drift_title": ("Цель «{name}» отстаёт", "«{name}» maqsadi orqada qolmoqda"),
    "p_drift_text": ("Доход стал ниже, и цель «{name}» сдвинулась на {shift_months}. "
                     "Если откладывать {new}% вместо {old}%, успеете в срок.",
                     "Daromad kamaydi va «{name}» maqsadi {shift_months}ga surildi. "
                     "{old}% o'rniga {new}% ajratsangiz, muddatga ulgurasiz."),
    "p_drift_text_cap": ("Цель «{name}» сдвинулась на {shift_months}. Максимум, что можно отложить, — {new}%: "
                         "тогда цель займёт {after_months}.",
                         "«{name}» maqsadi {shift_months}ga surildi. Eng ko'pi bilan {new}% ajratish mumkin: "
                         "unda maqsad {after_months} davom etadi."),
    "p_set_pct": ("Поставить {pct}%", "{pct}% qilish"),
    "p_topup_title": ("«{name}»: не хватает денег", "«{name}»: pul yetmayapti"),
    "p_topup_text": ("Платёж «{name}» {when}. Не хватает {short_sum}.", "«{name}» to'lovi {when}. {short_sum} yetmaydi."),
    "p_topup_partial": (" С основной карты можно перевести только {amount_sum}.",
                        " Asosiy kartadan faqat {amount_sum} o'tkazish mumkin."),
    "when_today": ("сегодня", "bugun"),
    "when_in": ("через {n_days}", "{n_days}dan keyin"),
    "p_transfer": ("Перевести {amount_sum}", "{amount_sum} o'tkazish"),
    "p_gap_title": ("До зарплаты может не хватить", "Maoshgacha pul yetmasligi mumkin"),
    "p_gap_text": ("На жизнь до зарплаты нужно около {need_sum}, а свободно {free_sum}. "
                   "Можно временно уменьшить «{name}» с {old}% до {new}%.",
                   "Maoshgacha yashash uchun taxminan {need_sum} kerak, bo'sh pul esa {free_sum}. "
                   "«{name}» ni vaqtincha {old}% dan {new}% gacha kamaytirish mumkin."),
    "p_lower": ("Уменьшить до {pct}%", "{pct}% gacha kamaytirish"),
    "p_cool_title": ("Прошли сутки", "Bir kun o'tdi"),
    "p_cool_text": ("Покупка «{merchant}» на {amount_sum} всё ещё нужна?",
                    "«{merchant}» dagi {amount_sum}lik xarid hali ham kerakmi?"),
    "p_newgoal_title": ("Новая цель «{name}»", "Yangi maqsad: «{name}»"),
    "p_newgoal_text": ("Откладывать {pct}% дохода на «{name}» ({amount_sum}).",
                       "«{name}» uchun daromadning {pct}% ini ajratish ({amount_sum})."),
    "p_create_goal": ("Создать цель", "Maqsad yaratish"),
    "p_newobl_title": ("Новый платёж «{name}»", "Yangi to'lov: «{name}»"),
    "p_newobl_text": ("Добавить обязательный платёж {amount_sum} до {due_date}.",
                      "{due_date} gacha {amount_sum} majburiy to'lov qo'shish."),
    "p_add_obl": ("Добавить платёж", "To'lov qo'shish"),
    "r_set_pct": ("Готово: «{name}» — {pct}% дохода.", "Tayyor: «{name}» — daromadning {pct}%."),
    "r_topup": ("Переведено {amount_sum} в резерв.", "Zaxiraga {amount_sum} o'tkazildi."),
    "r_goal_created": ("Цель «{name}» создана.", "«{name}» maqsadi yaratildi."),
    "r_obl_added": ("Платёж «{name}» добавлен.", "«{name}» to'lovi qo'shildi."),
    # guardian
    "g_cover": ("Оплатить с основной карты", "Asosiy kartadan to'lash"),
    "g_cool": ("Подождать до завтра", "Ertagacha kutish"),
    "g_no_need": ("Уже не нужно", "Endi kerak emas"),
    "g_proceed": ("Всё равно потратить", "Baribir sarflash"),
    "g_decline": ("Отказаться", "Rad etish"),
    "gm_covered": ("Оплачено с основной карты. «{name}» не тронута.", "Asosiy kartadan to'landi. «{name}» ga tegilmadi."),
    "gm_cooling": ("Хорошо, вернёмся к этому завтра. Если желание останется — решим вместе.",
                   "Yaxshi, ertaga qaytamiz. Istak qolsa — birga hal qilamiz."),
    "gm_spent_goal": ("Потрачено из «{name}». Бонус теперь {rate}% годовых.",
                      "«{name}» dan sarflandi. Endi bonus yillik {rate}%."),
    "gm_spent_obl": ("Потрачено из резерва «{name}».", "«{name}» zaxirasidan sarflandi."),
    "gm_declined": ("Покупка отменена. Деньги остались на месте.", "Xarid bekor qilindi. Pul joyida qoldi."),
    # transactions
    "tx_salary": ("Зарплата", "Maosh"),
    "tx_reserve": ("В резерв «{name}»", "«{name}» zaxirasiga"),
    "tx_pay": ("Оплата: {name}", "To'lov: {name}"),
    "tx_purchase": ("{label}: {merchant}", "{label}: {merchant}"),
    "tx_goal_used": ("Цель «{name}» достигнута (с бонусом {bonus_sum})",
                     "«{name}» maqsadiga erishildi ({bonus_sum} bonus bilan)"),
    "tx_goal_closed": ("Цель «{name}» закрыта, деньги вернулись", "«{name}» maqsadi yopildi, pul qaytdi"),
    "tx_groceries": ("{shop} — продукты", "{shop} — oziq-ovqat"),
    "tx_mobile": ("Uzmobile — связь", "Uzmobile — aloqa"),
    "tx_metro": ("Метро", "Metro"),
    "tx_client": ("Перевод от клиента", "Mijozdan o'tkazma"),
    "tx_utilities": ("Коммунальные услуги", "Kommunal xizmatlar"),
    "tx_chaikhana": ("Чайхана", "Choyxona"),
    "tx_taxi": ("Yandex Go", "Yandex Go"),
    # agent (code replies)
    "a_nothing": ("Сейчас нечего подтверждать. Чем помочь?", "Hozir tasdiqlanadigan narsa yo'q. Qanday yordam beray?"),
    "a_several": ("Есть несколько предложений — нажмите «Подтвердить» на нужном.",
                  "Bir nechta taklif bor — keraklisida «Tasdiqlash» ni bosing."),
    # fallback agent
    "lock": ("Деньги в этой подкарте защищены от импульсных трат. Экстренные расходы (аптека, больница) проходят без "
             "штрафа, остальные — с остановкой, задержкой 24 часа и потерей бонуса за дисциплину.",
             "Bu kichik kartadagi pul impulsiv xarajatlardan himoyalangan. Shoshilinch xarajatlar (dorixona, shifoxona) "
             "jarimasiz o'tadi, qolganlari — to'xtatish, 24 soat kechikish va intizom bonusini yo'qotish bilan."),
    "f_help": ("Я помогаю с деньгами: копить на цель, проверить кредит, следить за обязательными платежами и подсказать, "
               "сколько можно потратить. Например: «Хочу накопить 50 млн на машину за 3 года».",
               "Men pul masalalarida yordam beraman: maqsadga yig'ish, kreditni tekshirish, majburiy to'lovlarni kuzatish "
               "va qancha sarflash mumkinligini aytish. Masalan: «Mashina uchun 50 mln 3 yilda yig'moqchiman»."),
    "f_ask_amount": ("Сколько хотите накопить? Например: «50 млн на машину за 3 года».",
                     "Qancha yig'moqchisiz? Masalan: «mashina uchun 50 mln 3 yilda»."),
    "f_ask_term": ("За какой срок хотите накопить {amount_sum}? Например: «за 3 года».",
                   "{amount_sum}ni qancha muddatda yig'moqchisiz? Masalan: «3 yilda»."),
    "f_new_goal": ("Новая цель", "Yangi maqsad"),
    "f_goal_ok": ("Чтобы накопить {amount_sum} на «{name}» за {term_months}, откладывайте {pct}% дохода — "
                  "это {contrib_sum} в месяц.",
                  "«{name}» uchun {amount_sum}ni {term_months}da yig'ish uchun daromadning {pct}% ini ajrating — "
                  "bu oyiga {contrib_sum}."),
    "f_goal_cap": ("За {term_months} не получится: нужно {raw}% дохода, а свободно максимум {cap}% "
                   "(уже {used}% идёт на другие цели). При {pct}% цель займёт {worst_months}.",
                   "{term_months}da ulgurib bo'lmaydi: daromadning {raw}% i kerak, bo'sh esa ko'pi bilan {cap}% "
                   "(boshqa maqsadlarga allaqachon {used}%). {pct}% da maqsad {worst_months} davom etadi."),
    "f_goal_body": ("\n\n• Лучший случай: {best_months}\n• Худший случай: {worst_months}\n• Срок цели: до {expiry_date}"
                    "\n\n{lock}\n\nСоздать цель?",
                    "\n\n• Eng yaxshi holat: {best_months}\n• Eng yomon holat: {worst_months}\n"
                    "• Maqsad muddati: {expiry_date} gacha\n\n{lock}\n\nMaqsad yaratilsinmi?"),
    "w_amount": ("сумму", "summani"),
    "w_term": ("срок", "muddatni"),
    "w_rate": ("процентную ставку", "foiz stavkasini"),
    "f_credit_missing": ("Чтобы посчитать кредит, назовите {missing}. Например: «20 млн на 12 месяцев под 28%».",
                         "Kreditni hisoblash uchun {missing} ayting. Masalan: «20 mln, 12 oy, 28%»."),
    "f_credit_head": ("Платёж — {pay_sum} в месяц, переплата {over_sum}.",
                      "To'lov — oyiga {pay_sum}, ortiqcha to'lov {over_sum}."),
    "f_credit_dti": ("\n• Это {dti}% вашего самого низкого дохода (безопасно — до 40%).",
                     "\n• Bu eng past daromadingizning {dti}% i (xavfsiz — 40% gacha)."),
    "f_credit_cash": ("• ⚠ После обязательных платежей и целей остаётся {free_sum} в месяц — платёж больше этой суммы.",
                      "• ⚠ Majburiy to'lovlar va maqsadlardan keyin oyiga {free_sum} qoladi — to'lov bundan katta."),
    "f_credit_dti_risk": ("• ⚠ Платёж больше 40% дохода — это высокий риск.",
                          "• ⚠ To'lov daromadning 40% idan ko'p — bu yuqori xavf."),
    "f_credit_left": ("• После платежа останется {left_sum} свободных денег в месяц.",
                      "• To'lovdan keyin oyiga {left_sum} bo'sh pul qoladi."),
    "f_credit_never": ("• «{name}»: при таком платеже копить не получится.",
                       "• «{name}»: bunday to'lovda yig'ib bo'lmaydi."),
    "f_credit_delay": ("• «{name}»: {before} → {after} мес. (+{delay_months})",
                       "• «{name}»: {before} → {after} oy (+{delay_months})"),
    "f_credit_options": ("\nВарианты: 1) взять меньшую сумму или на дольше; 2) сначала накопить часть; "
                         "3) отказаться от покупки. Конкретные банки я не советую. Что посчитать дальше?",
                         "\nVariantlar: 1) kichikroq summa yoki uzoqroq muddat; 2) avval bir qismini yig'ish; "
                         "3) xariddan voz kechish. Aniq banklarni tavsiya qilmayman. Yana nimani hisoblay?"),
    "f_obl_none": ("Обязательных платежей пока нет.", "Hozircha majburiy to'lovlar yo'q."),
    "f_obl_head": ("Ваши обязательные платежи:", "Majburiy to'lovlaringiz:"),
    "f_obl_ok": ("✓ хватает", "✓ yetarli"),
    "f_obl_short": ("⚠ не хватает {short_sum}", "⚠ {short_sum} yetmaydi"),
    "f_obl_line": ("• {name}: {amount_sum}, {when} — {mark}", "• {name}: {amount_sum}, {when} — {mark}"),
    "f_obl_prop": ("\nЯ подготовил предложение, как закрыть нехватку.",
                   "\nKamomadni qanday yopish bo'yicha taklif tayyorladim."),
    "f_cash": ("На основной карте {main_sum}. Можно спокойно тратить {free_sum}.\n\n"
               "• До зарплаты {n_days}, на жизнь нужно примерно {need_sum}.",
               "Asosiy kartada {main_sum}. Bemalol {free_sum} sarflash mumkin.\n\n"
               "• Maoshgacha {n_days}, yashash uchun taxminan {need_sum} kerak."),
    "f_cash_gap": ("\n• ⚠ До зарплаты может не хватить — посмотрите предложения во входящих.",
                   "\n• ⚠ Maoshgacha yetmasligi mumkin — maslahatlarni ko'ring."),
}


def msg(key: str, **params) -> dict:
    """A message to render later (in whatever language is current then)."""
    return {"k": key, "p": params}


def both(ru: str, uz: str | None = None) -> dict:
    return {"ru": ru, "uz": uz if uz is not None else ru}


def _val(name: str, v, lang: str):
    if isinstance(v, dict):
        if "k" in v:
            return render(v, lang)
        if "ru" in v or "uz" in v:
            return v.get(lang) or v.get("ru") or ""
    if name.endswith("_sum") and isinstance(v, int):
        return uzs(v)
    if name.endswith("_date") and v:
        return fdate(v, lang)
    if name.endswith("_months") and isinstance(v, int):
        return fmonths(v, lang)
    if name.endswith("_days") and isinstance(v, int):
        return fdays(v, lang)
    return v


def tr(key: str, lang: str | None = None, **params) -> str:
    lang = lang or cur()
    ru, uz = T[key]
    template = uz if lang == "uz" else ru
    return template.format(**{k: _val(k, v, lang) for k, v in params.items()})


def render(m, lang: str | None = None) -> str:
    """Render a msg dict, a {'ru','uz'} dict or a plain string."""
    lang = lang or cur()
    if isinstance(m, dict):
        if "k" in m:
            return tr(m["k"], lang, **m.get("p", {}))
        return m.get(lang) or m.get("ru") or ""
    return m or ""


def disp(obj) -> str:
    """Display name of a goal/obligation in the current language."""
    names = getattr(obj, "names", None)
    return (names or {}).get(cur()) or obj.name


def loc(obj) -> dict:
    """Name of a goal/obligation in both languages (for stored messages)."""
    names = getattr(obj, "names", None) or {}
    return {"ru": names.get("ru") or obj.name, "uz": names.get("uz") or obj.name}
