"""Klient Qloo Insights API.

Zbudowany ściśle według przewodnika hackathonowego:
  * klucz w nagłówku ``X-Api-Key`` (nie Bearer, nie query param),
  * ``/v2/insights`` to GET — parametry w query stringu, nie w ciele JSON,
  * base URL klucza hackathonowego to ``hackathon.api.qloo.com``,
  * ``filter.type`` jest wymagany w każdym zapytaniu Insights,
  * ``/recs`` i ``/recommendations`` to endpointy legacy — nie używamy ich.

API milczy zamiast zgłaszać błąd, gdy parametr nie pasuje do ``filter.type``
(zwraca 200 i pustą listę), dlatego pusty wynik jest tu traktowany jako sygnał
diagnostyczny, a nie jako „brak danych”.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from .config import Settings


class QlooError(RuntimeError):
    """Błąd wywołania Qloo z komunikatem zrozumiałym dla człowieka."""


@dataclass
class QlooClient:
    settings: Settings
    _cache: dict[str, tuple[float, dict[str, Any]]] = field(default_factory=dict)
    _transport: httpx.BaseTransport | None = None
    #: Rozmiar, do którego wywołujący chce przyciąć wynik. Insights API nie ma
    #: parametru rozmiaru strony, więc cięcie odbywa się po naszej stronie.
    page_size: int = 6

    # ------------------------------------------------------------------ infra

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.settings.qloo_base_url,
            timeout=self.settings.request_timeout,
            transport=self._transport,
        )

    def _headers(self) -> dict[str, str]:
        return {"X-Api-Key": self.settings.qloo_api_key, "Accept": "application/json"}

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """Wykonuje GET, mapując udokumentowane kody błędów na czytelne komunikaty."""
        clean = {k: v for k, v in params.items() if v not in (None, "", [], {})}
        cache_key = f"{path}?{sorted(clean.items())}"
        hit = self._cache.get(cache_key)
        if hit and (time.time() - hit[0]) < self.settings.cache_ttl_seconds:
            return hit[1]

        try:
            with self._client() as client:
                response = client.get(path, params=clean, headers=self._headers())
        except httpx.HTTPError as exc:  # sieć / DNS / timeout
            raise QlooError(f"Nie udało się połączyć z Qloo ({exc.__class__.__name__}).") from exc

        if response.status_code == 401:
            raise QlooError(
                "401 Unauthorized. Klucz hackathonowy działa wyłącznie z "
                "https://hackathon.api.qloo.com — sprawdź QLOO_BASE_URL i QLOO_API_KEY."
            )
        if response.status_code == 403:
            raise QlooError(
                "403 Forbidden. Ten typ encji nie jest objęty Twoim kluczem "
                "(np. muzyka to 'urn:entity:artist', nie 'urn:entity:music')."
            )
        if response.status_code >= 400:
            detail = response.text[:300]
            raise QlooError(f"Qloo zwróciło {response.status_code}: {detail}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise QlooError("Qloo zwróciło odpowiedź, która nie jest JSON-em.") from exc

        self._cache[cache_key] = (time.time(), payload)
        return payload

    # ------------------------------------------------------------- wyszukiwanie

    def search_entities(self, query: str, types: list[str] | None = None, size: int = 5) -> list[dict[str, Any]]:
        """Rozwiązuje nazwę („Sting”, „Barszcz”) na identyfikator encji Qloo.

        ``/search`` akceptuje inny zbiór typów niż ``filter.type`` w Insights,
        więc nie wolno ich mieszać.
        """
        params: dict[str, Any] = {"query": query, "size": size}
        if types:
            params["types"] = ",".join(types)
        payload = self._get("/search", params)
        return payload.get("results", []) or []

    def search_tags(self, query: str, size: int = 5) -> list[dict[str, Any]]:
        """Znajduje poprawne identyfikatory tagów — ``filter.tags`` nie przyjmuje wolnego tekstu."""
        payload = self._get("/v2/tags", {"query": query, "size": size})
        return payload.get("results", []) or []

    # --------------------------------------------------------------- insights

    def insights(
        self,
        filter_type: str,
        *,
        interest_entities: list[str] | None = None,
        interest_tags: list[str] | None = None,
        exclude_entities: list[str] | None = None,
        exclude_tags: list[str] | None = None,
        location_query: str | None = None,
        location_radius: int | None = None,
        age_range: str | None = None,
        tags: list[str] | None = None,
        results_per_page: int = 6,
        explainability: bool = True,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Zapytanie do /v2/insights.

        Zwraca surowy payload — w tym ``query.explainability``, jeśli włączony.
        """
        params: dict[str, Any] = {
            "filter.type": filter_type,
            "feature.explainability": "true" if explainability else None,
            "page": 1,
        }
        if interest_entities:
            params["signal.interests.entities"] = ",".join(interest_entities)
        if interest_tags:
            params["signal.interests.tags"] = ",".join(interest_tags)
        if exclude_entities:
            params["filter.exclude.entities"] = ",".join(exclude_entities)
        if exclude_tags:
            params["filter.exclude.tags"] = ",".join(exclude_tags)
            params["operator.filter.exclude.tags"] = "union"
        if location_query:
            # Rozmyte dopasowanie nazwy miejscowości; API zwraca 400, gdy nic nie znajdzie.
            params["filter.location.query"] = location_query
            if location_radius is not None:
                params["filter.location.radius"] = location_radius
        if age_range:
            params["signal.demographics.age"] = age_range
        if tags:
            params["filter.tags"] = ",".join(tags)
            params["operator.filter.tags"] = "union"
        if extra:
            params.update({k: v for k, v in extra.items() if v not in (None, "", [])})

        # UWAGA: w dokumentacji Insights API nie ma parametru rozmiaru strony
        # (są tylko `page` i `offset`), a przewodnik ostrzega, że nieobsługiwane
        # parametry są po cichu ignorowane i skutkują pustym wynikiem bez błędu.
        # Dlatego nie wysyłamy nic takiego — przycinamy wynik po swojej stronie.
        self.page_size = max(1, min(int(results_per_page), 20))
        return self._get("/v2/insights", params)

    # ------------------------------------------------------------- interpretacja

    @staticmethod
    def extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Wyciąga listę encji z odpowiedzi Insights (struktura: ``results``)."""
        results = payload.get("results")
        if isinstance(results, list):
            return results
        if isinstance(results, dict):
            inner = results.get("results") or results.get("entities")
            if isinstance(inner, list):
                return inner
        entities = payload.get("entities")
        return entities if isinstance(entities, list) else []

    @staticmethod
    def explainability_for(item: dict[str, Any]) -> list[dict[str, Any]]:
        """Które kotwice wejściowe pociągnęły tę rekomendację i z jaką siłą (0–1)."""
        expl = (item.get("query") or {}).get("explainability") or {}
        drivers = expl.get("entities") or expl.get("signals") or []
        out: list[dict[str, Any]] = []
        for d in drivers if isinstance(drivers, list) else []:
            if not isinstance(d, dict):
                continue
            out.append(
                {
                    "entity_id": str(d.get("id") or d.get("entity_id") or ""),
                    "entity_name": str(d.get("name") or d.get("entity_name") or ""),
                    "score": float(d.get("score") or d.get("normalized_score") or 0.0),
                }
            )
        return out

    @staticmethod
    def item_name(item: dict[str, Any]) -> str:
        return str(item.get("name") or (item.get("properties") or {}).get("name") or "bez nazwy")

    @staticmethod
    def item_affinity(item: dict[str, Any]) -> float:
        for key in ("affinity", "score", "affinity_score"):
            value = item.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return 0.0

    @staticmethod
    def item_tags(item: dict[str, Any]) -> list[str]:
        tags = item.get("tags") or []
        return [str(t) for t in tags][:8] if isinstance(tags, list) else []

    @staticmethod
    def item_description(item: dict[str, Any]) -> str:
        props = item.get("properties") or {}
        return str(item.get("description") or props.get("description") or "")

    @staticmethod
    def item_image(item: dict[str, Any]) -> str | None:
        props = item.get("properties") or {}
        image = item.get("image") or props.get("image")
        return str(image) if image else None

    @staticmethod
    def item_address(item: dict[str, Any]) -> str:
        props = item.get("properties") or {}
        geocode = props.get("geocode") or {}
        parts = [
            str(item.get("address") or props.get("address") or ""),
            str(geocode.get("name") or ""),
            str(geocode.get("country_code") or ""),
        ]
        return ", ".join(p for p in parts if p)
