"""Warstwa narracji.

Plan powstaje w planerze; narrator odpowiada wyłącznie za zdanie podsumowujące.
Rozdzielenie jest celowe:

  * ``DeterministicNarrator`` — domyślny, bez żadnego klucza API. Plan musi
    działać na czystej maszynie, bez rejestracji u trzeciej dostawcy.
  * ``LlmNarrator`` — opcjonalny, gdy ustawiony jest ``LLM_API_KEY``. Każda
    awaria (sieć, limit, zła odpowiedź) kończy się powrotem do wersji
    deterministycznej, więc demo nigdy nie pada przez warstwę językową.

``/api/health`` raportuje ``llm_enabled`` na podstawie tego, który narrator
faktycznie zbudowano — nie na podstawie samej obecności klucza w środowisku.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from .config import Settings
from .models import Anchor, DomainSection

# Domyślny endpoint w formacie OpenAI-compatible. Pasuje do OpenAI, OpenRouter,
# Groq i lokalnego Ollamy — wystarczy zmienić LLM_BASE_URL.
DEFAULT_LLM_BASE_URL = "https://api.openai.com/v1"
DEFAULT_LLM_MODEL = "gpt-4o-mini"


class Narrator(Protocol):
    """Jedna metoda: z kotwic i sekcji zrób jedno zdanie podsumowania."""

    def narrate(
        self,
        *,
        origin: str,
        destination: str,
        anchors: list[Anchor],
        sections: list[DomainSection],
    ) -> str: ...


class DeterministicNarrator:
    """Składa podsumowanie z danych. Bez sieci, bez klucza, zawsze działa."""

    def narrate(
        self,
        *,
        origin: str,
        destination: str,
        anchors: list[Anchor],
        sections: list[DomainSection],
    ) -> str:
        found = sum(len(s.items) for s in sections)
        names = [a.name for a in anchors if a.resolved][:3]
        anchor_part = ", ".join(names) if names else "podanych przez Ciebie kotwic"
        return (
            f"Zaczynamy od tego, co już lubisz ({anchor_part}), i szukamy najbliższych "
            f"odpowiedników w: {destination}. Zamiast generycznej listy "
            f"„co zobaczyć w {destination}”, każda pozycja wynika z Twojego smaku — "
            f"i ma dopisane, dlaczego. Znalezionych pozycji: {found}."
        )


class LlmNarrator:
    """Narracja przez model językowy, z twardym powrotem do wersji deterministycznej."""

    def __init__(
        self,
        settings: Settings,
        fallback: Narrator | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.fallback = fallback or DeterministicNarrator()
        self._transport = transport
        self.model = settings.llm_model or DEFAULT_LLM_MODEL
        self.base_url = (settings.llm_base_url or DEFAULT_LLM_BASE_URL).rstrip("/")

    def narrate(
        self,
        *,
        origin: str,
        destination: str,
        anchors: list[Anchor],
        sections: list[DomainSection],
    ) -> str:
        deterministic = self.fallback.narrate(
            origin=origin, destination=destination, anchors=anchors, sections=sections
        )
        try:
            text = self._call_model(origin, destination, anchors, sections)
        except Exception:
            # Warstwa językowa jest ozdobą — nie może położyć demo.
            return deterministic
        text = (text or "").strip()
        return text if text else deterministic

    def _call_model(
        self,
        origin: str,
        destination: str,
        anchors: list[Anchor],
        sections: list[DomainSection],
    ) -> str:
        top = [
            {"name": i.name, "domain": s.label, "why": i.why, "affinity": round(i.affinity, 2)}
            for s in sections
            for i in s.items[:3]
        ]
        payload = {
            "model": self.model,
            "temperature": 0.4,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Piszesz po polsku, maksymalnie trzy zdania, bez nagłówków i bez "
                        "punktów. Zwracasz się do osoby, która właśnie przeprowadziła się "
                        "z {origin} do {destination} i czuje się obco. Wyjaśnij, że plan "
                        "wychodzi od jej własnego smaku, a nie od listy przebojów, i że przy "
                        "każdej propozycji jest powód. Nie zmyślaj pozycji spoza danych."
                    ).format(origin=origin, destination=destination),
                },
                {
                    "role": "user",
                    "content": (
                        f"Kotwice: {', '.join(a.name for a in anchors) or 'brak'}\n"
                        f"Najmocniejsze dopasowania: {top}"
                    ),
                },
            ],
        }

        with httpx.Client(
            base_url=self.base_url,
            timeout=self.settings.request_timeout,
            transport=self._transport,
        ) as client:
            response = client.post(
                "/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
            )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data["choices"][0]["message"]["content"]


def build_narrator(settings: Settings) -> tuple[Narrator, bool]:
    """Zwraca (narrator, czy warstwa LLM jest naprawdę aktywna).

    Druga wartość jest tym, co powinien raportować ``/api/health`` — mówi,
    który narrator faktycznie zbudowano, a nie co deklaruje środowisko.
    """
    if settings.llm_enabled:
        return LlmNarrator(settings), True
    return DeterministicNarrator(), False
