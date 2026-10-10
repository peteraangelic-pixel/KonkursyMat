"""Testy planera agentowego — przechodzą przez tę samą ścieżkę co tryb produkcyjny."""

from __future__ import annotations

from typing import Any

import pytest

from app.models import Anchor, PlanRequest
from app.planner import DOMAIN_LABELS, Planner
from app.provider import DemoProvider
from app.qloo_client import QlooError


class FakeProvider:
    """Minimalny dostawca do testów — rejestruje wywołania i zwraca fixture'y."""

    def __init__(self, *, fail_on: set[str] | None = None, empty_for: set[str] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.fail_on = fail_on or set()
        self.empty_for = empty_for or set()

    def search_entities(self, query: str, types=None, take: int = 5):
        self.calls.append({"op": "search", "query": query, "types": types})
        table = {
            "Okean Elzy": {"id": "artist-1", "type": "urn:entity:artist"},
            "Amélie": {"id": "movie-1", "type": "urn:entity:movie"},
        }
        hit = table.get(query)
        return [hit] if hit else []

    def insights(self, filter_type: str, **kwargs):
        self.calls.append({"op": "insights", "type": filter_type, **kwargs})
        if filter_type in self.fail_on:
            raise QlooError(f"403 dla {filter_type}")
        if filter_type in self.empty_for:
            return {"results": []}
        return {
            "results": [
                {
                    "id": f"{filter_type}-rec-1",
                    "name": f"Pozycja z {filter_type}",
                    "affinity": 0.82,
                    "tags": ["urn:tag:demo"],
                    "description": "Opis testowy",
                    "query": {
                        "explainability": {
                            "entities": [{"id": "artist-1", "name": "Okean Elzy", "score": 0.74}]
                        }
                    },
                }
            ]
        }

    # interpretacja — współdzielona z DemoProvider, żeby nie duplikować
    extract_items = staticmethod(DemoProvider.extract_items)
    explainability_for = staticmethod(DemoProvider.explainability_for)
    item_id = staticmethod(DemoProvider.item_id)
    item_name = staticmethod(DemoProvider.item_name)
    item_affinity = staticmethod(DemoProvider.item_affinity)
    item_tags = staticmethod(DemoProvider.item_tags)
    item_description = staticmethod(DemoProvider.item_description)
    item_image = staticmethod(DemoProvider.item_image)
    item_address = staticmethod(DemoProvider.item_address)


def make_request(**overrides) -> PlanRequest:
    base = dict(
        origin="Ukraina (Lwów)",
        destination="Poznań",
        anchors=[Anchor(name="Okean Elzy", kind="artist"), Anchor(name="Amélie", kind="movie")],
        domains=["urn:entity:movie", "urn:entity:place"],
    )
    base.update(overrides)
    return PlanRequest(**base)


# ------------------------------------------------------- 1. resolve kotwic


def test_kotwice_sa_rozwiazywane_na_identyfikatory_qloo():
    provider = FakeProvider()
    planner = Planner(provider, "qloo")
    plan = planner.build_plan(make_request())

    searches = [c for c in provider.calls if c["op"] == "search"]
    assert {s["query"] for s in searches} == {"Okean Elzy", "Amélie"}
    # rozwiązane ID trafiają do sygnału
    insight_calls = [c for c in provider.calls if c["op"] == "insights"]
    assert insight_calls[0]["interest_entities"] == ["artist-1", "movie-1"]


def test_nierozwiazana_kotwica_daje_ostrzezenie_i_nie_blokuje_planu():
    provider = FakeProvider()
    planner = Planner(provider, "qloo")
    request = make_request(anchors=[Anchor(name="barszcz", kind="dish"), Anchor(name="Amélie", kind="movie")])
    plan = planner.build_plan(request)

    assert any("barszcz" in w for w in plan.warnings)
    # plan nadal powstał, na tej kotwicy, która się rozwiązała
    insight_calls = [c for c in provider.calls if c["op"] == "insights"]
    assert insight_calls[0]["interest_entities"] == ["movie-1"]
    assert sum(len(s.items) for s in plan.sections) > 0


def test_rodzaj_kotwicy_zawezsza_wyszukiwanie():
    provider = FakeProvider()
    Planner(provider, "qloo").build_plan(make_request())
    searches = {c["query"]: c["types"] for c in provider.calls if c["op"] == "search"}
    assert searches["Okean Elzy"] == ["urn:entity:artist"]
    assert searches["Amélie"] == ["urn:entity:movie", "urn:entity:tv_show"]


# ----------------------------------------------------------- 2. fan-out


def test_kazda_domena_dostaje_osobne_zapytanie():
    provider = FakeProvider()
    planner = Planner(provider, "qloo")
    planner.build_plan(make_request(domains=["urn:entity:movie", "urn:entity:artist", "urn:entity:place"]))

    types = [c["type"] for c in provider.calls if c["op"] == "insights"]
    assert types == ["urn:entity:movie", "urn:entity:artist", "urn:entity:place"]


def test_lokalizacja_jest_dolaczana_tylko_dla_domen_z_geokodem():
    provider = FakeProvider()
    Planner(provider, "qloo").build_plan(
        make_request(domains=["urn:entity:movie", "urn:entity:place"], destination="Poznań")
    )
    by_type = {c["type"]: c for c in provider.calls if c["op"] == "insights"}
    assert by_type["urn:entity:place"]["location_query"] == "Poznań"
    # film nie ma geokodu — doczepianie miejscowości byłoby błędem parametru
    assert "location_query" not in by_type["urn:entity:movie"]


def test_wyjasnialnosc_jest_zawsze_wlaczona():
    provider = FakeProvider()
    Planner(provider, "qloo").build_plan(make_request())
    for call in [c for c in provider.calls if c["op"] == "insights"]:
        assert call["explainability"] is True


# ------------------------------------------------------------ 3. compose


def test_kazda_rekomendacja_ma_powod_i_zrodlo():
    planner = Planner(FakeProvider(), "qloo")
    plan = planner.build_plan(make_request())

    items = [i for s in plan.sections for i in s.items]
    assert items, "plan nie zawiera żadnych pozycji"
    for item in items:
        assert item.why, "pozycja bez wyjaśnienia"
        assert item.drivers, "pozycja bez listy czynników"
        assert item.source == "qloo"


def test_powod_wskazuje_kotwice_i_je_sile():
    planner = Planner(FakeProvider(), "qloo")
    plan = planner.build_plan(make_request())
    item = plan.sections[0].items[0]
    assert "Okean Elzy" in item.why
    assert item.drivers[0].score == pytest.approx(0.74)


def test_sekcje_maja_ludzkie_etykiety():
    planner = Planner(FakeProvider(), "qloo")
    plan = planner.build_plan(make_request())
    assert {s.label for s in plan.sections} == {
        DOMAIN_LABELS["urn:entity:movie"],
        DOMAIN_LABELS["urn:entity:place"],
    }


def test_plan_rozkłada_sie_na_tygodnie():
    planner = Planner(FakeProvider(), "qloo")
    plan = planner.build_plan(make_request(per_domain=4))
    assert plan.weeks, "brak podziału na tygodnie"
    assert plan.weeks[0]["week"] == 1
    assert plan.weeks[0]["steps"]


# ------------------------------------------------------------- 4. refine


def test_wykluczenie_trafia_do_filter_exclude_entities():
    provider = FakeProvider()
    planner = Planner(provider, "qloo")
    planner.build_plan(make_request(exclude_entities=["movie-1"], exclude_tags=["urn:tag:zle"]))

    call = [c for c in provider.calls if c["op"] == "insights"][0]
    assert call["exclude_entities"] == ["movie-1"]
    assert call["exclude_tags"] == ["urn:tag:zle"]


def test_wykluczona_pozycja_znika_z_planu():
    """DemoProvider honoruje wykluczenia — sprawdzamy pełną pętlę."""
    planner = Planner(DemoProvider(), "demo")
    request = make_request(domains=["urn:entity:movie"], per_domain=10)

    before = planner.build_plan(request)
    ids_before = {i.qloo_id for s in before.sections for i in s.items}
    assert "demo-movie-atlantics" in ids_before

    request2 = make_request(
        domains=["urn:entity:movie"], per_domain=10, exclude_entities=["demo-movie-atlantics"]
    )
    after = planner.build_plan(request2)
    ids_after = {i.qloo_id for s in after.sections for i in s.items}
    assert "demo-movie-atlantics" not in ids_after
    assert len(ids_after) == len(ids_before) - 1


# --------------------------------------------------------- odporność


def test_bled_domeny_nie_przerywa_calego_planu():
    provider = FakeProvider(fail_on={"urn:entity:place"})
    planner = Planner(provider, "qloo")
    plan = planner.build_plan(make_request())

    by_label = {s.label: s for s in plan.sections}
    assert by_label[DOMAIN_LABELS["urn:entity:place"]].items == []
    assert "403" in by_label[DOMAIN_LABELS["urn:entity:place"]].note
    # druga domena dowiozła wynik
    assert by_label[DOMAIN_LABELS["urn:entity:movie"]].items


def test_pusta_domena_dostaje_diagnostyczny_komunikat():
    provider = FakeProvider(empty_for={"urn:entity:place"})
    plan = Planner(provider, "qloo").build_plan(make_request())
    place = next(s for s in plan.sections if s.domain == "urn:entity:place")
    assert place.items == []
    assert "Pusty wynik" in place.note


def test_brak_kotwic_po_rozwiazaniu_daje_ostrzezenie_o_wymaganiu_api():
    provider = FakeProvider()
    plan = Planner(provider, "qloo").build_plan(make_request(anchors=[Anchor(name="barszcz")]))
    assert any("co najmniej jednego" in w for w in plan.warnings)


# --------------------------------------------------------- tryb demo


def test_tryb_demo_oznacza_zrodlo_i_dodaje_baner():
    plan = Planner(DemoProvider(), "demo").build_plan(make_request())
    assert plan.data_source == "demo"
    assert plan.warnings and "TRYB DEMO" in plan.warnings[0]
    for section in plan.sections:
        for item in section.items:
            assert item.source == "demo"


def test_demo_nie_przypisuje_kotwic_ktorych_uzytkownik_nie_podal():
    """REGRESJA: fixture'y miały wpisane „barszcz” na sztywno i dopisywały go
    jako powód nawet wtedy, gdy użytkownik podał tylko muzykę i film."""
    planner = Planner(DemoProvider(), "demo")
    plan = planner.build_plan(
        make_request(
            anchors=[Anchor(name="Okean Elzy", kind="artist"), Anchor(name="Amélie", kind="movie")],
            domains=list(DOMAIN_LABELS),
            per_domain=10,
        )
    )
    podane = {a.name for a in plan_anchors(plan)}
    for section in plan.sections:
        for item in section.items:
            for driver in item.drivers:
                assert driver.entity_name in podane, (
                    f"{item.name}: czynnik „{driver.entity_name}” nie był wprowadzony "
                    f"przez użytkownika (podano: {sorted(podane)})"
                )


def plan_anchors(plan):
    """Kotwice, które faktycznie wpłynęły na plan (czyli rozwiązane)."""
    from app.models import Anchor

    seen: dict[str, Anchor] = {}
    for section in plan.sections:
        for item in section.items:
            for d in item.drivers:
                seen[d.entity_id] = Anchor(name=d.entity_name, qloo_id=d.entity_id, resolved=True)
    return list(seen.values())


def test_demo_bez_kotwic_nie_zmysla_powodow():
    planner = Planner(DemoProvider(), "demo")
    plan = planner.build_plan(make_request(anchors=[], domains=["urn:entity:movie"]))
    assert sum(len(s.items) for s in plan.sections) == 0


def test_demo_dostarcza_dane_dla_scenariusza_poznan():
    plan = Planner(DemoProvider(), "demo").build_plan(
        make_request(
            anchors=[Anchor(name="Okean Elzy", kind="artist"), Anchor(name="Amélie", kind="movie")],
            destination="Poznań",
            domains=list(DOMAIN_LABELS),
            per_domain=5,
        )
    )
    assert sum(len(s.items) for s in plan.sections) >= 4
