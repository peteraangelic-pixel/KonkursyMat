"""Testy warstwy narracji.

Sprawdzamy przede wszystkim dwie rzeczy, które łatwo zepsuć:
  1. że plan działa bez żadnego klucza API (domyślna ścieżka),
  2. że awaria modelu językowego NIE kładzie planu — wracamy do wersji
     deterministycznej, bo warstwa językowa jest ozdobą, nie fundamentem.
"""

from __future__ import annotations

import httpx
import pytest

from app.config import Settings
from app.models import Anchor, DomainSection, Recommendation
from app.narrator import (
    DeterministicNarrator,
    LlmNarrator,
    build_narrator,
)


def sample_sections() -> list[DomainSection]:
    return [
        DomainSection(
            domain="urn:entity:artist",
            label="Muzyka i koncerty",
            items=[
                Recommendation(
                    qloo_id="a1",
                    name="DagaDana",
                    domain="urn:entity:artist",
                    affinity=0.86,
                    why="Dopasowanie 88% przez: Okean Elzy",
                )
            ],
        )
    ]


def sample_anchors() -> list[Anchor]:
    return [Anchor(name="Okean Elzy", kind="artist", qloo_id="x1", resolved=True)]


# ------------------------------------------------- narrator deterministyczny


def test_narrator_deterministyczny_wymienia_kotwice_i_miasto():
    text = DeterministicNarrator().narrate(
        origin="Ukraina",
        destination="Poznań",
        anchors=sample_anchors(),
        sections=sample_sections(),
    )
    assert "Okean Elzy" in text
    assert "Poznań" in text
    assert "1" in text  # liczba znalezionych pozycji


def test_narrator_deterministyczny_dziala_bez_rozwiazanych_kotwic():
    text = DeterministicNarrator().narrate(
        origin="Ukraina",
        destination="Poznań",
        anchors=[Anchor(name="barszcz", resolved=False)],
        sections=[],
    )
    assert "Poznań" in text
    assert "kotwic" in text


def test_narrator_nie_zmysla_pozycji():
    """Podsumowanie nie może wymienić niczego, czego nie ma w sekcjach."""
    text = DeterministicNarrator().narrate(
        origin="Ukraina",
        destination="Poznań",
        anchors=sample_anchors(),
        sections=[],
    )
    assert "DagaDana" not in text
    assert "Znalezionych pozycji: 0" in text


# ---------------------------------------------------------- narrator LLM


def make_llm_settings(**overrides) -> Settings:
    base = dict(
        qloo_api_key="q",
        llm_api_key="sk-test",
        llm_provider="openai",
        llm_base_url="https://llm.test/v1",
        llm_model="test-model",
    )
    base.update(overrides)
    return Settings(**base)


def ok_transport(reply: str) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": reply}}]}
        )

    return httpx.MockTransport(handler)


def test_llm_narrator_zwraca_tekst_modelu():
    narrator = LlmNarrator(make_llm_settings(), transport=ok_transport("Tekst z modelu."))
    text = narrator.narrate(
        origin="Ukraina",
        destination="Poznań",
        anchors=sample_anchors(),
        sections=sample_sections(),
    )
    assert text == "Tekst z modelu."


def test_llm_narrator_wysyla_klucz_jako_bearer():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("Authorization", "")
        seen["path"] = request.url.path
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    narrator = LlmNarrator(make_llm_settings(), transport=httpx.MockTransport(handler))
    narrator.narrate(
        origin="Ukraina",
        destination="Poznań",
        anchors=sample_anchors(),
        sections=sample_sections(),
    )
    assert seen["auth"] == "Bearer sk-test"
    # base_url kończy się na /v1, więc pełna ścieżka to /v1/chat/completions
    assert seen["path"] == "/v1/chat/completions"


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(500, json={"error": "boom"}),
        lambda request: httpx.Response(200, json={"choices": []}),
        lambda request: httpx.Response(200, json={"unexpected": True}),
    ],
    ids=["http-500", "puste-choices", "nieznany-ksztalt"],
)
def test_awaria_modelu_nie_kladzie_planu(handler):
    """Każda z tych awarii musi skończyć się tekstem deterministycznym."""
    narrator = LlmNarrator(make_llm_settings(), transport=httpx.MockTransport(handler))
    text = narrator.narrate(
        origin="Ukraina",
        destination="Poznań",
        anchors=sample_anchors(),
        sections=sample_sections(),
    )
    expected = DeterministicNarrator().narrate(
        origin="Ukraina",
        destination="Poznań",
        anchors=sample_anchors(),
        sections=sample_sections(),
    )
    assert text == expected
    assert text  # nie pusty


def test_blad_sieci_modelu_te_zwraca_fallback():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sieć padła")

    narrator = LlmNarrator(make_llm_settings(), transport=httpx.MockTransport(handler))
    text = narrator.narrate(
        origin="Ukraina",
        destination="Poznań",
        anchors=sample_anchors(),
        sections=sample_sections(),
    )
    assert "Poznań" in text


def test_pusta_odpowiedz_modelu_daje_fallback():
    narrator = LlmNarrator(make_llm_settings(), transport=ok_transport("   "))
    text = narrator.narrate(
        origin="Ukraina",
        destination="Poznań",
        anchors=sample_anchors(),
        sections=sample_sections(),
    )
    assert "Poznań" in text


# ------------------------------------------------------------- dobór narratora


def test_bez_klucza_llm_wybierany_jest_deterministyczny():
    narrator, active = build_narrator(Settings(qloo_api_key="q"))
    assert isinstance(narrator, DeterministicNarrator)
    assert active is False


def test_sam_klucz_bez_dostawcy_nie_wlacza_llm():
    """Przypadkowo wklejony klucz nie może zmienić zachowania aplikacji."""
    narrator, active = build_narrator(Settings(qloo_api_key="q", llm_api_key="sk-x"))
    assert isinstance(narrator, DeterministicNarrator)
    assert active is False


def test_klucz_i_dostawca_wlaczaja_llm():
    narrator, active = build_narrator(make_llm_settings())
    assert isinstance(narrator, LlmNarrator)
    assert active is True


def test_llm_narrator_ma_deterministyczny_fallback():
    narrator, _ = build_narrator(make_llm_settings())
    assert isinstance(narrator, LlmNarrator)
    assert isinstance(narrator.fallback, DeterministicNarrator)
