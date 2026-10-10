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
            interest = params.get("signal.interests.entities", "")
            exclude = {x for x in params.get("filter.exclude.entities", "").split(",") if x}
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
