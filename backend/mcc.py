"""MCC -> category. Decided by code only; user text never changes the category."""
from enum import Enum

from texts import cur


class Category(str, Enum):
    EMERGENCY = "emergency"
    IMPULSE = "impulse"
    OBLIGATION = "obligation"
    UNKNOWN = "unknown"


# mcc -> (category, ru label, uz label)
MCC_TABLE: dict[str, tuple[Category, str, str]] = {
    "5912": (Category.EMERGENCY, "Аптека", "Dorixona"),
    "8062": (Category.EMERGENCY, "Больница", "Shifoxona"),
    "8011": (Category.EMERGENCY, "Врач", "Shifokor"),
    "8021": (Category.EMERGENCY, "Стоматолог", "Stomatolog"),
    "8099": (Category.EMERGENCY, "Медицинские услуги", "Tibbiy xizmatlar"),
    "4119": (Category.EMERGENCY, "Скорая помощь", "Tez yordam"),
    "7832": (Category.IMPULSE, "Кинотеатр", "Kinoteatr"),
    "5812": (Category.IMPULSE, "Ресторан", "Restoran"),
    "5814": (Category.IMPULSE, "Фастфуд", "Fastfud"),
    "5813": (Category.IMPULSE, "Бар", "Bar"),
    "7993": (Category.IMPULSE, "Видеоигры", "Video o'yinlar"),
    "7941": (Category.IMPULSE, "Спортивные события", "Sport tadbirlari"),
    "5311": (Category.IMPULSE, "Универмаг", "Univermag"),
    "5999": (Category.IMPULSE, "Разные товары", "Turli tovarlar"),
    "6513": (Category.OBLIGATION, "Аренда жилья", "Uy ijarasi"),
    "6012": (Category.OBLIGATION, "Платёж по кредиту", "Kredit to'lovi"),
}
UNKNOWN_LABEL = {"ru": "Покупка", "uz": "Xarid", "en": "Purchase"}
EN_LABEL = {"5912": "Pharmacy", "8062": "Hospital", "8011": "Doctor", "8021": "Dentist", "8099": "Medical services",
            "4119": "Ambulance", "7832": "Cinema", "5812": "Restaurant", "5814": "Fast food", "5813": "Bar",
            "7993": "Video games", "7941": "Sports events", "5311": "Department store", "5999": "Other goods",
            "6513": "Rent", "6012": "Loan payment"}


def classify(mcc: str) -> Category:
    """Only the MCC decides. There is deliberately no text parameter."""
    entry = MCC_TABLE.get(mcc)
    return entry[0] if entry else Category.UNKNOWN


def labels(mcc: str) -> dict:
    """Label in every language (for stored messages)."""
    entry = MCC_TABLE.get(mcc)
    return {"ru": entry[1], "uz": entry[2], "en": EN_LABEL[mcc]} if entry else dict(UNKNOWN_LABEL)


def label(mcc: str) -> str:
    return labels(mcc)[cur()]
