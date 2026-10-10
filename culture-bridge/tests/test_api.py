"""Testy warstwy HTTP — pełna ścieżka: żądanie → planer → odpowiedź."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_zglasza_tryb_demo_bez_klucza(monkeypatch):
    monkeypatch.delenv("QLOO_API_KEY", raising=False)
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert data["qloo_connected"] is False
    assert data["data_source"] == "demo"


def test_health_zglasza_qloo_gdy_jest_klucz(monkeypatch):
    monkeypatch.setenv("QLOO_API_KEY", "abc123")
    data = client.get("/api/health").json()
    assert data["qloo_connected"] is True
    assert data["data_source"] == "qloo"


def test_domains_zwraca_liste_dla_frontendu():
    ids = {d["id"] for d in client.get("/api/domains").json()["domains"]}
    assert "urn:entity:movie" in ids
    assert "urn:entity:place" in ids


def test_plan_odpowiada_na_pelne_zadanie():
    response = client.post(
        "/api/plan",
        json={
            "origin": "Ukraina (Lwów)",
            "destination": "Poznań",
            "anchors": [{"name": "Okean Elzy", "kind": "artist"}, {"name": "Amélie", "kind": "movie"}],
            "domains": ["urn:entity:movie", "urn:entity:artist", "urn:entity:place"],
        },
    )
    assert response.status_code == 200
    plan = response.json()
    assert plan["origin"] == "Ukraina (Lwów)"
    assert plan["destination"] == "Poznań"
    assert plan["data_source"] == "demo"
    assert plan["sections"], "brak sekcji w odpowiedzi"
    assert any(s["items"] for s in plan["sections"]), "żadna sekcja nie ma pozycji"
    assert plan["weeks"], "brak podziału na tygodnie"


def test_plan_wymaga_kotwicy():
    response = client.post(
        "/api/plan",
        json={"origin": "Ukraina", "destination": "Poznań", "anchors": []},
    )
    assert response.status_code == 422
    assert "kotwicę" in response.json()["detail"]


def test_plan_odrzuca_puste_pole_pochodzenia():
    response = client.post(
        "/api/plan",
        json={"origin": "", "destination": "Poznań", "anchors": [{"name": "Sting"}]},
    )
    assert response.status_code == 422


def test_pozycja_ma_wyjasnienie_w_odpowiedzi_api():
    plan = client.post(
        "/api/plan",
        json={
            "origin": "Ukraina",
            "destination": "Poznań",
            "anchors": [{"name": "Okean Elzy", "kind": "artist"}],
            "domains": ["urn:entity:artist"],
        },
    ).json()
    item = plan["sections"][0]["items"][0]
    assert item["why"]
    assert item["drivers"]
    assert 0 < item["drivers"][0]["score"] <= 1


def test_wykluczenie_zmniejsza_liczbe_pozycji():
    body = {
        "origin": "Ukraina",
        "destination": "Poznań",
        "anchors": [{"name": "Okean Elzy", "kind": "artist"}],
        "domains": ["urn:entity:movie"],
        "per_domain": 10,
    }
    before = client.post("/api/plan", json=body).json()
    n_before = sum(len(s["items"]) for s in before["sections"])

    body["exclude_entities"] = ["demo-movie-atlantics"]
    after = client.post("/api/plan", json=body).json()
    n_after = sum(len(s["items"]) for s in after["sections"])

    assert n_after == n_before - 1


def test_index_serwuje_frontend():
    response = client.get("/")
    assert response.status_code == 200
    assert "Smak Domu" in response.text


def test_frontend_zawiera_baner_trybu_demo():
    """Tryb demo musi być widoczny dla użytkownika, nie tylko w JSON-ie."""
    html = client.get("/").text
    assert "demo-banner" in html
