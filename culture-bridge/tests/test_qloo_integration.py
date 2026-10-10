"""Test integracyjny: prawdziwy kształt odpowiedzi Qloo → cały planer.

To jest ścieżka, która uaktywnia się DOPIERO po wklejeniu prawdziwego
`QLOO_API_KEY`. Reszta testów albo sprawdza parsowanie pojedynczych pól
(`test_qloo_client.py`), albo pracuje na uproszczonych fixture'ach
(`test_planner.py`). Ten test spina jedno z drugim: `QlooClient` na
`httpx.MockTransport` oddaje odpowiedź przepisaną z dokumentacji Qloo,
a planer musi z niej złożyć poprawny plan.

Fixture jest przepisany z docs.qloo.com/reference/basic-insights-use-case.
"""

from __future__ import annotations

import httpx
import pytest

from app.config import Settings
from app.models import Anchor, PlanRequest
from app.planner import Planner
from app.qloo_client import QlooClient

BASE = "https://hackathon.api.qloo.com"


def qloo_entity(
    entity_id: str,
    name: str,
    *,
    subtype: str = "urn:entity:movie",
    affinity: float | None = None,
    tags: list[dict] | None = None,
    image_url: str | None = None,
    description: str = "Opis z dokumentacji.",
) -> dict:
    """Encja w kształcie, w jakim naprawdę zwraca ją Insights API."""
    props: dict = {"description": description}
    if image_url:
        props["image"] = {"url": image_url}  # obiekt, nie napis
    entity: dict = {
        "name": name,
        "entity_id": entity_id,  # nie "id"
        "type": "urn:entity",
        "subtype": subtype,
        "properties": props,
        "popularity": 0.987,  # inna miara niż afinacja
        "tags": tags if tags is not None else [],
    }
    if affinity is not None:
        entity["query"] = {"affinity": affinity}
    else:
        entity["query"] = {"measurements": {"audience_growth": -0.04}}
    return entity


def explainable(entity: dict, drivers: list[tuple[str, str, float]]) -> dict:
    """Dokłada sekcję explainability, tak jak robi to feature.explainability=true."""
    entity["query"]["explainability"] = {
        "entities": [{"id": i, "name": n, "score": s} for i, n, s in drivers]
    }
    return entity


TAG_MULTIVERSE = {"id": "urn:tag:keyword:media:multiverse", "name": "Multiverse", "type": "urn:tag:keyword:media"}
TAG_DRAMA = {"id": "urn:tag:genre:media:drama", "name": "Drama", "type": "urn:tag:genre:media"}

# Zapis parametrów, które faktycznie poleciały do API — pozwala testować
# wysyłkę `filter.location.query`, a nie tylko to, co wróciło.
SEEN: list[dict[str, str]] = []


def place_entity(entity_id: str, name: str, *, city: str, country: str, affinity: float) -> dict:
    """Miejsce (POI) w kształcie odpowiedzi Insights API — z geokodem w `properties`."""
    return {
        "name": name,
        "entity_id": entity_id,
        "type": "urn:entity",
        "subtype": "urn:entity:place",
        "properties": {
            "description": "Kino studyjne z repertuarem autorskim.",
            "geocode": {"name": city, "country_code": country, "metro": city},
        },
        "popularity": 0.64,
        "tags": [{"id": "urn:tag:venue:cinema", "name": "Cinema", "type": "urn:tag:venue"}],
        "query": {"affinity": affinity},
    }


@pytest.fixture(autouse=True)
def _clear_seen():
    SEEN.clear()
    yield
    SEEN.clear()


@pytest.fixture
def qloo_transport() -> httpx.MockTransport:
    """Udawane API Qloo odpowiadające udokumentowanym kształtem."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        params = request.url.params

        if path == "/search":
            query = params.get("query", "").lower()
            table = {
                "okean elzy": qloo_entity("ART-001", "Okean Elzy", subtype="urn:entity:artist"),
                "amélie": qloo_entity("MOV-001", "Amélie"),
            }
            hit = table.get(query)
            if hit is None:
                return httpx.Response(404, json={"error": "No results"})
            return httpx.Response(200, json={"results": [hit]})

        if path == "/v2/insights":
            exclude = {x for x in params.get("filter.exclude.entities", "").split(",") if x}
            filter_type = params.get("filter.type", "")
            # Zapisujemy, co realnie poleciało — testy sprawdzają parametry, nie domysły.
            SEEN.append(dict(params))

            if filter_type == "urn:entity:place":
                entities = [
                    explainable(
                        place_entity("PLC-100", "Kino Muza", city="Poznań", country="PL", affinity=0.79),
                        [("MOV-001", "Amélie", 0.68)],
                    ),
                ]
            else:
                entities = [
                    explainable(
                        qloo_entity(
                            "MOV-100",
                            "Everything Everywhere All at Once",
                            affinity=0.83,
                            tags=[TAG_MULTIVERSE, TAG_DRAMA],
                            image_url="https://images.qloo.com/mov-100.jpg",
                        ),
                        [("MOV-001", "Amélie", 0.71)],
                    ),
                    explainable(
                        qloo_entity("ART-100", "DagaDana", subtype="urn:entity:artist", affinity=0.77, tags=[TAG_DRAMA]),
                        [("ART-001", "Okean Elzy", 0.66)],
                    ),
                ]
            kept = [e for e in entities if e["entity_id"] not in exclude]
            return httpx.Response(200, json={"success": True, "results": {"entities": kept}})

        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)


@pytest.fixture
def planner(qloo_transport) -> Planner:
    settings = Settings(qloo_api_key="test-key", qloo_base_url=BASE)
    client = QlooClient(settings=settings, _transport=qloo_transport)
    return Planner(client, "qloo")


def request(**overrides) -> PlanRequest:
    base = dict(
        origin="Ukraina (Lwów)",
        destination="Poznań",
        anchors=[Anchor(name="Okean Elzy", kind="artist"), Anchor(name="Amélie", kind="movie")],
        domains=["urn:entity:movie"],
        per_domain=5,
    )
    base.update(overrides)
    return PlanRequest(**base)


# ------------------------------------------------------- cały plan z prawdziwej odpowiedzi


def test_plan_powstaje_z_prawdziwego_ksztaltu_odpowiedzi(planner):
    plan = planner.build_plan(request())
    assert plan.data_source == "qloo"
    assert plan.sections, "brak sekcji"
    assert plan.sections[0].items, "sekcja bez pozycji"
    assert not plan.warnings, f"nieoczekiwane ostrzeżenia: {plan.warnings}"


def test_qloo_id_pochodzi_z_entity_id(planner):
    """Gdyby planer czytał `id`, wszystkie byłyby puste i wykluczanie by nie działało."""
    plan = planner.build_plan(request())
    ids = [i.qloo_id for s in plan.sections for i in s.items]
    assert ids == ["MOV-100", "ART-100"]
    assert all(ids), "puste qloo_id zabiłoby przycisk „to nie to”"


def test_tagi_sa_czytelnymi_nazwami(planner):
    plan = planner.build_plan(request())
    movie = plan.sections[0].items[0]
    assert movie.tags == ["Multiverse", "Drama"]
    assert all("{" not in t for t in movie.tags), "do UI wyciekła repr słownika"


def test_obrazek_jest_urlem(planner):
    plan = planner.build_plan(request())
    movie = plan.sections[0].items[0]
    assert movie.image == "https://images.qloo.com/mov-100.jpg"
    assert "{" not in (movie.image or "")


def test_afinacja_nie_jest_popularity(planner):
    """Encja ma popularity=0.987 i query.affinity=0.83 — ma pokazać 0.83."""
    plan = planner.build_plan(request())
    movie = plan.sections[0].items[0]
    assert movie.affinity == pytest.approx(0.83)


def test_powod_wskazuje_kotwice_z_dokumentacyjnego_ksztaltu(planner):
    plan = planner.build_plan(request())
    movie = plan.sections[0].items[0]
    assert movie.drivers[0].entity_name == "Amélie"
    assert movie.drivers[0].score == pytest.approx(0.71)
    assert "Amélie" in movie.why


def test_opis_przechodzi_z_properties(planner):
    plan = planner.build_plan(request())
    assert plan.sections[0].items[0].description == "Opis z dokumentacji."


# ------------------------------------------------------- pętla doprecyzowania na prawdziwym ID


def test_wykluczenie_uzywa_prawdziwego_entity_id(planner):
    """Kluczowa integracja: ID z `entity_id` musi wrócić do `filter.exclude.entities`."""
    before = planner.build_plan(request())
    assert len(before.sections[0].items) == 2

    after = planner.build_plan(request(exclude_entities=["MOV-100"]))
    remaining = [i.qloo_id for i in after.sections[0].items]
    assert remaining == ["ART-100"]


# ------------------------------------------------------- nierozwiązana kotwica


# ------------------------------------------------------- miejsca + lokalizacja
#
# To jest ścieżka, na której stoi cały pomysł: plan ma dotyczyć KONKRETNEGO
# miasta. Filmy nie mają geokodu, więc doczepianie im miejscowości byłoby
# parametrem nieobsługiwanym dla tego filter.type — czyli po cichu ignorowanym.


def test_miejsca_dostaja_lokalizacje_filmy_nie(planner):
    planner.build_plan(request(domains=["urn:entity:movie", "urn:entity:place"], destination="Poznań"))

    by_type = {s["filter.type"]: s for s in SEEN}
    assert by_type["urn:entity:place"]["filter.location.query"] == "Poznań"
    assert "filter.location.query" not in by_type["urn:entity:movie"], (
        "film nie ma geokodu — ten parametr byłby dla niego po cichu zignorowany"
    )


def test_adres_sklada_sie_z_geokodu(planner):
    """Adres miejsca siedzi w `properties.geocode`, nie w polu `address`."""
    plan = planner.build_plan(request(domains=["urn:entity:place"], destination="Poznań"))
    place = plan.sections[0].items[0]
    assert place.name == "Kino Muza"
    assert "Poznań" in place.address
    assert "PL" in place.address


def test_miejsce_ma_powod_i_afinacje(planner):
    plan = planner.build_plan(request(domains=["urn:entity:place"], destination="Poznań"))
    place = plan.sections[0].items[0]
    assert place.affinity == pytest.approx(0.79)
    assert place.drivers[0].entity_name == "Amélie"
    assert place.tags == ["Cinema"]


def test_kazde_zapytanie_insights_ma_filter_type(planner):
    planner.build_plan(request(domains=["urn:entity:movie", "urn:entity:place"]))
    assert SEEN, "nie wysłano żadnego zapytania Insights"
    for sent in SEEN:
        assert sent.get("filter.type"), "zapytanie bez wymaganego filter.type"
        assert sent.get("feature.explainability") == "true"


def test_brak_nieudokumentowanych_parametrow(planner):
    """Przewodnik: parametr spoza dokumentacji jest po cichu ignorowany.

    Pilnujemy, żeby do zapytania nie wróciły zmyślone nazwy, które kiedyś
    usuwaliśmy (`size`, `filter.results_per_page`).
    """
    planner.build_plan(request(domains=["urn:entity:movie", "urn:entity:place"]))
    zabronione = {"size", "filter.results_per_page", "results_per_page"}
    for sent in SEEN:
        nadmiarowe = zabronione & set(sent)
        assert not nadmiarowe, f"wysłano nieudokumentowane parametry: {sorted(nadmiarowe)}"


# --------------------------------------------------- pelna sciezka HTTP + Qloo
#
# Testy powyżej wołają planer bezpośrednio. Ten sprawdza to, co naprawdę
# dostaje przeglądarka: żądanie HTTP → create_plan() → build_provider() →
# QlooClient → serializacja LandingPlan. To ostatnia warstwa, która uruchamia
# się wyłącznie z prawdziwym kluczem — a oba znalezione tu bugi były właśnie
# w kodzie działającym tylko wtedy.


@pytest.fixture
def http_z_qloo(qloo_transport, monkeypatch):
    """Podmienia build_provider w module main na klienta Qloo z udawanym API."""
    from fastapi.testclient import TestClient

    from app import main as main_module

    settings = Settings(qloo_api_key="test-key", qloo_base_url=BASE)
    client = QlooClient(settings=settings, _transport=qloo_transport)
    monkeypatch.setattr(main_module, "build_provider", lambda _s: (client, "qloo"))
    monkeypatch.setenv("QLOO_API_KEY", "test-key")
    return TestClient(main_module.app)


def test_api_plan_z_dostawca_qloo(http_z_qloo):
    response = http_z_qloo.post(
        "/api/plan",
        json={
            "origin": "Ukraina (Lwów)",
            "destination": "Poznań",
            "anchors": [{"name": "Okean Elzy", "kind": "artist"}, {"name": "Amélie", "kind": "movie"}],
            "domains": ["urn:entity:movie"],
        },
    )
    assert response.status_code == 200, response.text
    plan = response.json()

    assert plan["data_source"] == "qloo", "z kluczem plan musi być oznaczony jako qloo"
    assert not plan["warnings"], f"nieoczekiwane ostrzeżenia: {plan['warnings']}"

    item = plan["sections"][0]["items"][0]
    # Te pola frontend wyświetla — gdyby serializacja je zgubiła, UI byłoby puste.
    assert item["qloo_id"] == "MOV-100"
    assert item["tags"] == ["Multiverse", "Drama"]
    assert item["image"] == "https://images.qloo.com/mov-100.jpg"
    assert item["drivers"][0]["entity_name"] == "Amélie"
    assert 0 < item["drivers"][0]["score"] <= 1
    assert item["why"]


def test_api_plan_z_qloo_przekazuje_wykluczenie(http_z_qloo):
    """Przycisk „to nie to" musi dojść aż do API, nie zostać w przeglądarce."""
    body = {
        "origin": "Ukraina (Lwów)",
        "destination": "Poznań",
        "anchors": [{"name": "Okean Elzy", "kind": "artist"}, {"name": "Amélie", "kind": "movie"}],
        "domains": ["urn:entity:movie"],
    }
    before = http_z_qloo.post("/api/plan", json=body).json()
    ids_before = [i["qloo_id"] for s in before["sections"] for i in s["items"]]
    assert "MOV-100" in ids_before

    body["exclude_entities"] = ["MOV-100"]
    after = http_z_qloo.post("/api/plan", json=body).json()
    ids_after = [i["qloo_id"] for s in after["sections"] for i in s["items"]]
    assert "MOV-100" not in ids_after


def test_api_plan_z_qloo_zglasza_bled_qloo_jako_502(qloo_transport, monkeypatch):
    """Awaria Qloo ma dać czytelny 502, nie pusty ekran ani 500."""
    from fastapi.testclient import TestClient

    from app import main as main_module

    def failing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Invalid API key"})

    settings = Settings(qloo_api_key="zly-klucz", qloo_base_url=BASE)
    client = QlooClient(settings=settings, _transport=httpx.MockTransport(failing))
    monkeypatch.setattr(main_module, "build_provider", lambda _s: (client, "qloo"))
    monkeypatch.setenv("QLOO_API_KEY", "zly-klucz")

    response = TestClient(main_module.app).post(
        "/api/plan",
        json={
            "origin": "Ukraina",
            "destination": "Poznań",
            "anchors": [{"name": "Okean Elzy", "kind": "artist"}],
            "domains": ["urn:entity:movie"],
        },
    )
    assert response.status_code == 502
    assert response.json()["detail"]


def test_api_plan_nieosiagalne_qloo_daje_502(monkeypatch):
    """Awaria sieci / zły QLOO_BASE_URL to nie „brak danych dla tego miasta".

    Połknięty błąd dawał HTTP 200 z zerem pozycji i ostrzeżeniem „brak
    rozwiązanych kotwic", które wskazuje na użytkownika zamiast na konfigurację.
    A dotyczy każdego zapytania — próba innej domeny nic by nie dała.
    """
    from fastapi.testclient import TestClient

    from app import main as main_module

    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    settings = Settings(qloo_api_key="test-key", qloo_base_url=BASE)
    client = QlooClient(settings=settings, _transport=httpx.MockTransport(unreachable))
    monkeypatch.setattr(main_module, "build_provider", lambda _s: (client, "qloo"))
    monkeypatch.setenv("QLOO_API_KEY", "test-key")

    response = TestClient(main_module.app).post(
        "/api/plan",
        json={
            "origin": "Ukraina",
            "destination": "Poznań",
            "anchors": [{"name": "Okean Elzy", "kind": "artist"}],
            "domains": ["urn:entity:movie"],
        },
    )
    assert response.status_code == 502
    assert "QLOO_BASE_URL" in response.json()["detail"]


def test_blad_pojedynczej_domeny_nie_przerywa_calego_planu(qloo_transport, monkeypatch):
    """Druga strona tej samej decyzji: błąd JEDNEJ domeny ma degradować, nie rwać planu."""
    from fastapi.testclient import TestClient

    from app import main as main_module

    def selective(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        params = request.url.params
        if path == "/search":
            return httpx.Response(
                200, json={"results": [qloo_entity("ART-001", "Okean Elzy", subtype="urn:entity:artist")]}
            )
        if path == "/v2/insights":
            if params.get("filter.type") == "urn:entity:book":
                return httpx.Response(400, json={"error": "unsupported filter.type"})
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "results": {
                        "entities": [
                            explainable(qloo_entity("ART-100", "DagaDana", subtype="urn:entity:artist", affinity=0.7), [])
                        ]
                    },
                },
            )
        return httpx.Response(404, json={"error": "not found"})

    settings = Settings(qloo_api_key="test-key", qloo_base_url=BASE)
    client = QlooClient(settings=settings, _transport=httpx.MockTransport(selective))
    monkeypatch.setattr(main_module, "build_provider", lambda _s: (client, "qloo"))
    monkeypatch.setenv("QLOO_API_KEY", "test-key")

    response = TestClient(main_module.app).post(
        "/api/plan",
        json={
            "origin": "Ukraina",
            "destination": "Poznań",
            "anchors": [{"name": "Okean Elzy", "kind": "artist"}],
            "domains": ["urn:entity:artist", "urn:entity:book"],
        },
    )
    assert response.status_code == 200, response.text
    plan = response.json()
    by_domain = {s["domain"]: s for s in plan["sections"]}

    # Zepsuta domena dostała notatkę zamiast pozycji...
    assert not by_domain["urn:entity:book"]["items"]
    assert by_domain["urn:entity:book"]["note"]
    # ...ale zdrowa domena normalnie działa.
    assert by_domain["urn:entity:artist"]["items"]


def test_nierozwiazana_kotwica(qloo_transport):
    """Kotwica, której /search nie znajduje (404), nie może wywalić planu."""
    settings = Settings(qloo_api_key="test-key", qloo_base_url=BASE)
    client = QlooClient(settings=settings, _transport=qloo_transport)
    plan = Planner(client, "qloo").build_plan(
        request(anchors=[Anchor(name="coś nieistniejącego"), Anchor(name="Amélie", kind="movie")])
    )
    assert any("coś nieistniejącego" in w for w in plan.warnings)
    # plan i tak powstał na tej kotwicy, która się rozwiązała
    assert plan.sections[0].items
