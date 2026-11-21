"""Russian text helpers for templates (display only, no math)."""
from datetime import date

from calc import fmt_uzs

MONTHS_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
              "сентября", "октября", "ноября", "декабря"]

LOCK_WARNING = ("Деньги в этой подкарте защищены от импульсных трат. Экстренные расходы (аптека, больница) "
                "проходят без штрафа, остальные — с остановкой, задержкой 24 часа и потерей бонуса за дисциплину.")


def fmt_date(d: date | str) -> str:
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return f"{d.day} {MONTHS_GEN[d.month - 1]} {d.year}"


def plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return one
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return few
    return many


def months(n: int) -> str:
    return f"{n} {plural(n, 'месяц', 'месяца', 'месяцев')}"


def days(n: int) -> str:
    return f"{n} {plural(n, 'день', 'дня', 'дней')}"


__all__ = ["fmt_uzs", "fmt_date", "months", "days", "plural", "LOCK_WARNING"]
