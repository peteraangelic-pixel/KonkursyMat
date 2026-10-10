"""Testy klienta Qloo.

Używamy ``httpx.MockTransport``, więc przechodzimy przez prawdziwy kod klienta
(budowanie parametrów, nagłówki, mapowanie kodów błędów) bez dostępu do sieci.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.config import Settings
from app.qloo_client import QlooClient, QlooError

BASE = "https://hackathon.api.qloo.com"


def make_client(handler, api_key: str = "test-key") -> QlooClient:
    settings = Settings(qloo_api_key=api_key, qloo_base_url=BASE)
    return QlooClient(settings=settings, _transport=httpx.MockTransport(handler))


def echo_handler(request: httpx.Request) -> httpx.Response:
    """Zwraca to, co dostał — pozwala assertions robić na prawdziwym żądaniu."""
    return httpx.Response(
        200,
        json={
            "results": [],
            "_seen_path": request.url.path,
            "_seen_params": dict(request.url.params),
            "_seen_api_key": request.headers.get("X-Api-Key"),
            "_seen_auth": request.headers.get("Authorization"),
            "_seen_method": request.method,
        },
    )


# --------------------------------------------------------- poprawność zapytania


def test_insights_uzywa_get_i_wlasciwego_naglowka():
    client = make_client(echo_handler)
    payload = client.insights("urn:entity:movie", interest_entities=["e1", "e2"])

    assert payload["_seen_method"] == "GET"
    assert payload["_seen_api_key"] == "test-key"
    # Przewodnik: „Do not pass it as a query parameter or as a Bearer token.”
    assert payload["_seen_auth"] is None


def test_insights_wysyla_wymagany_filter_type():
    client = make_client(echo_handler)
    payload = client.insights("urn:entity:place")
    assert payload["_seen_params"]["filter.type"] == "urn:entity:place"
    assert payload["_seen_path"] == "/v2/insights"


def test_sygnaly_sa_laczone_przecinkami():
    client = make_client(echo_handler)
    payload = client.insights(
        "urn:entity:movie",
        interest_entities=["a", "b", "c"],
        interest_tags=["urn:tag:x"],
        exclude_entities=["z"],
    )
    params = payload["_seen_params"]
    assert params["signal.interests.entities"] == "a,b,c"
    assert params["signal.interests.tags"] == "urn:tag:x"
    assert params["filter.exclude.entities"] == "z"


def test_wyjasnialnosc_jest_wlaczona():
    client = make_client(echo_handler)
    payload = client.insights("urn:entity:movie", explainability=True)
    assert payload["_seen_params"]["feature.explainability"] == "true"


def test_lokalizacja_trafia_do_filter_location_query():
    client = make_client(echo_handler)
    payload = client.insights("urn:entity:place", location_query="Poznań", location_radius=5000)
    params = payload["_seen_params"]
    assert params["filter.location.query"] == "Poznań"
    assert params["filter.location.radius"] == "5000"


def test_puste_parametry_nie_sa_wysylane():
    """API po cichu ignoruje puste wartości — nie chcemy zaśmiecać zapytania."""
    client = make_client(echo_handler)
    payload = client.insights("urn:entity:movie", interest_entities=[], location_query="")
    params = payload["_seen_params"]
    assert "signal.interests.entities" not in params
    assert "filter.location.query" not in params


def test_rozmiar_wyniku_idzie_przez_udokumentowany_take():
    """Insights API ma `take` (1–50). Wcześniej wysyłaliśmy zmyślony
    `filter.results_per_page`, który API po cichu by zignorowało."""
    client = make_client(echo_handler)
    payload = client.insights("urn:entity:movie", results_per_page=6)
    params = payload["_seen_params"]
    assert params["take"] == "6"
    assert "filter.results_per_page" not in params
    assert "results_per_page" not in params
    assert client.page_size == 6


def test_take_jest_przycinany_do_dokumentowanych_granic():
    """Dokumentacja: `take` to 1–50. Wartość spoza zakresu nie może wyjść na zewnątrz."""
    client = make_client(echo_handler)
    assert client.insights("urn:entity:movie", results_per_page=999)["_seen_params"]["take"] == "50"
    assert client.insights("urn:entity:movie", results_per_page=0)["_seen_params"]["take"] == "1"


def test_search_i_tags_uzywaja_osobnych_sciezek():
    client = make_client(echo_handler)
    search = client.search_entities("Sting")
    assert search == []
    tags = client.search_tags("cuisine")
    assert tags == []


def test_search_zwraca_pusta_liste_przy_404():
    """/search dokumentuje 404 jako „No results” — to wynik, nie awaria."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "No results"})

    client = make_client(handler)
    assert client.search_entities("nie ma takiego") == []
    assert client.search_tags("nie ma takiego") == []


def test_search_przekazuje_parametry_z_dokumentacji():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        seen["_path"] = request.url.path
        return httpx.Response(200, json={"results": [{"id": "e1", "name": "Sting"}]})

    client = make_client(handler)
    result = client.search_entities("Sting", types=["urn:entity:artist"], take=3)

    assert result == [{"id": "e1", "name": "Sting"}]
    assert seen["_path"] == "/search"
    assert seen["query"] == "Sting"
    assert seen["take"] == "3"
    assert seen["sort_by"] == "match"
    assert seen["types"] == "urn:entity:artist"
    assert "size" not in seen


# ------------------------------------------------------------- mapowanie błędów


@pytest.mark.parametrize(
    "status,body,fragment",
    [
        (401, {"error": "No API key found in request"}, "hackathon.api.qloo.com"),
        (403, {"error": "You do not have permission to access urn:entity:music"}, "urn:entity:artist"),
    ],
)
def test_bledy_http_maja_czytelny_komunikat(status, body, fragment):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    client = make_client(handler)
    with pytest.raises(QlooError) as exc:
        client.insights("urn:entity:movie")
    assert fragment in str(exc.value)


def test_blad_sieci_jest_przechwycony():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    client = make_client(handler)
    with pytest.raises(QlooError) as exc:
        client.insights("urn:entity:movie")
    assert "Nie udało się połączyć" in str(exc.value)


def test_nie_json_zwraca_czytelny_blad():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>not json</html>")

    client = make_client(handler)
    with pytest.raises(QlooError):
        client.insights("urn:entity:movie")


# --------------------------------------------------------------------- cache


def test_cache_ogranicza_liczbe_wyowan():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"results": []})

    client = make_client(handler)
    client.insights("urn:entity:movie", interest_entities=["a"])
    client.insights("urn:entity:movie", interest_entities=["a"])
    assert calls["n"] == 1

    # inny zestaw parametrów = osobne zapytanie
    client.insights("urn:entity:movie", interest_entities=["b"])
    assert calls["n"] == 2


# ------------------------------------------------------------- interpretacja


def test_extract_items_radzi_sobie_z_roznymi_ksztaltami_odpowiedzi():
    assert QlooClient.extract_items({"results": [{"id": "1"}]}) == [{"id": "1"}]
    assert QlooClient.extract_items({"results": {"results": [{"id": "2"}]}}) == [{"id": "2"}]
    assert QlooClient.extract_items({"entities": [{"id": "3"}]}) == [{"id": "3"}]
    assert QlooClient.extract_items({"foo": "bar"}) == []


def test_explainability_wyciaga_sile_wplywu_kotwic():
    item = {
        "id": "x",
        "query": {
            "explainability": {
                "entities": [{"id": "a1", "name": "Amélie", "score": 0.71}]
            }
        },
    }
    drivers = QlooClient.explainability_for(item)
    assert drivers == [{"entity_id": "a1", "entity_name": "Amélie", "score": 0.71}]


def test_explainability_brak_danych_nie_wysypuje_sie():
    assert QlooClient.explainability_for({"id": "x"}) == []
    assert QlooClient.explainability_for({"id": "x", "query": {"explainability": {"warning": "n/d"}}}) == []


def test_item_helpers():
    item = {
        "id": "p1",
        "name": "Bar",
        "affinity": 0.8,
        "tags": ["urn:tag:a", "urn:tag:b"],
        "description": "opis",
        "address": "ul. X",
        "properties": {"geocode": {"name": "Poznań", "country_code": "PL"}},
    }
    assert QlooClient.item_name(item) == "Bar"
    assert QlooClient.item_affinity(item) == 0.8
    assert QlooClient.item_tags(item) == ["urn:tag:a", "urn:tag:b"]
    assert QlooClient.item_description(item) == "opis"
    assert "Poznań" in QlooClient.item_address(item)
    assert QlooClient.item_image(item) is None
