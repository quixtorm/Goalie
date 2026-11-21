"""The whole demo in Uzbek: no Cyrillic may leak into any server response."""
import json
import re

import pytest
from fastapi.testclient import TestClient

import main

CYR = re.compile(r"[А-Яа-яЁё]")
UZ = {"X-Lang": "uz"}


def no_cyrillic(resp):
    text = json.dumps(resp.json(), ensure_ascii=False)
    found = CYR.findall(text)
    assert not found, f"Cyrillic leaked: {text[:400]}"
    return resp.json()


@pytest.fixture
def c():
    client = TestClient(main.app)
    client.post("/demo/reset")
    return client


def test_full_demo_in_uzbek_has_no_russian(c):
    st = no_cyrillic(c.get("/state", headers=UZ))
    assert [g["name"] for g in st["goals"]] == ["Telefon"]
    assert st["obligations"][0]["name"] == "Kvartira ijarasi"
    assert any("oziq-ovqat" in t["title"] for t in st["transactions"])
    no_cyrillic(c.get("/mcc", headers=UZ))

    r = no_cyrillic(c.post("/agent/chat", json={"message": "Mashina uchun 50 mln 3 yilda yig'moqchiman", "lang": "uz"}))
    assert r["data"]["percent"] == 21 and "Maqsad yaratilsinmi?" in r["reply"]
    no_cyrillic(c.post("/agent/chat", json={"message": "ha", "lang": "uz"}))
    car = next(g for g in c.get("/state", headers=UZ).json()["goals"] if g["name"] == "Mashina")

    no_cyrillic(c.post("/demo/salary", json={"amount": 6_375_000}, headers=UZ))
    inbox = no_cyrillic(c.get("/agent/inbox", headers=UZ))
    drift = next(p for p in inbox if p["kind"] == "goal_percent" and p["status"] == "pending")
    assert "orqada qolmoqda" in drift["title"] and drift["options"][0]["label"] == "22% qilish"
    no_cyrillic(c.post(f"/agent/proposals/{drift['id']}/confirm", headers=UZ))

    stop = no_cyrillic(c.post("/spend", json={"source_id": car["id"], "amount": 150_000, "mcc": "7832",
                                              "merchant": "Magic Cinema"}, headers=UZ))
    assert stop["label"] == "Kinoteatr"
    no_cyrillic(c.post(f"/spend/{stop['stop_id']}/resolve", json={"option": "cooling"}, headers=UZ))
    c.post("/demo/skip-time", json={"hours": 24}, headers=UZ)
    cool = next(p for p in no_cyrillic(c.get("/agent/inbox", headers=UZ)) if p["kind"] == "cooling_ready")
    assert cool["title"] == "Bir kun o'tdi"
    no_cyrillic(c.post(f"/agent/proposals/{cool['id']}/confirm", json={"option": "decline"}, headers=UZ))

    no_cyrillic(c.post("/spend", json={"source_id": car["id"], "amount": 300_000, "mcc": "5912",
                                       "merchant": "Dori-Darmon"}, headers=UZ))
    r = no_cyrillic(c.post("/agent/chat", json={"message": "Telefon kredit 20 mln 12 oyga 28%", "lang": "uz"}))
    assert r["data"]["payment"] == 1_930_120
    no_cyrillic(c.post("/agent/chat", json={"message": "Qarzlarim", "lang": "uz"}))
    no_cyrillic(c.post("/agent/chat", json={"message": "Qancha sarflay olaman?", "lang": "uz"}))

    no_cyrillic(c.post("/obligations", json={"name": "Akamga qarz", "amount": 1_500_000, "due_date": "2026-12-05"},
                       headers=UZ))
    top = next(p for p in no_cyrillic(c.get("/agent/inbox", headers=UZ)) if p["kind"] == "obligation_topup")
    assert "3 kundan keyin" in top["text"]
    no_cyrillic(c.post(f"/agent/proposals/{top['id']}/confirm", headers=UZ))
    no_cyrillic(c.get("/state", headers=UZ))


def test_errors_in_uzbek(c):
    r = c.post("/subcards", json={"name": "A", "amount": 1_000_000, "percent": 35}, headers=UZ)
    assert r.status_code == 422 and "40%" in r.json()["detail"]
    no_cyrillic(r)
    no_cyrillic(c.get("/subcards/nope", headers=UZ))
    no_cyrillic(c.post("/demo/salary", json={"amount": -1}, headers=UZ))


def test_switching_language_rerenders_stored_items(c):
    c.post("/demo/salary", json={"amount": 6_375_000})
    ru = c.get("/state").json()["transactions"][0]["title"]
    uz = c.get("/state", headers=UZ).json()["transactions"][0]["title"]
    assert (ru, uz) == ("Зарплата", "Maosh")
