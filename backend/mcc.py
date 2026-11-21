"""MCC -> category. Decided by code only; user text never changes the category."""
from enum import Enum


class Category(str, Enum):
    EMERGENCY = "emergency"
    IMPULSE = "impulse"
    OBLIGATION = "obligation"
    UNKNOWN = "unknown"


MCC_TABLE: dict[str, tuple[Category, str]] = {
    "5912": (Category.EMERGENCY, "Аптека"),
    "8062": (Category.EMERGENCY, "Больница"),
    "8011": (Category.EMERGENCY, "Врач"),
    "8021": (Category.EMERGENCY, "Стоматолог"),
    "8099": (Category.EMERGENCY, "Медицинские услуги"),
    "4119": (Category.EMERGENCY, "Скорая помощь"),
    "7832": (Category.IMPULSE, "Кинотеатр"),
    "5812": (Category.IMPULSE, "Ресторан"),
    "5814": (Category.IMPULSE, "Фастфуд"),
    "5813": (Category.IMPULSE, "Бар"),
    "7993": (Category.IMPULSE, "Видеоигры"),
    "7941": (Category.IMPULSE, "Спортивные события"),
    "5311": (Category.IMPULSE, "Универмаг"),
    "5999": (Category.IMPULSE, "Разные товары"),
    "6513": (Category.OBLIGATION, "Аренда жилья"),
    "6012": (Category.OBLIGATION, "Платёж по кредиту"),
}


def classify(mcc: str) -> Category:
    """Only the MCC decides. There is deliberately no text parameter."""
    entry = MCC_TABLE.get(mcc)
    return entry[0] if entry else Category.UNKNOWN


def label(mcc: str) -> str:
    entry = MCC_TABLE.get(mcc)
    return entry[1] if entry else "Покупка"
