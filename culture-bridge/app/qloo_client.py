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


class QlooFatalError(QlooError):
    """Błąd dotyczący KAŻDEGO zapytania — próba innej domeny go nie naprawi.

    Planer połyka zwykły ``QlooError`` dla pojedynczej domeny, bo pusty lub
    odrzucony wynik jednej domeny nie unieważnia pozostałych. Błędy z tej
    rodziny dotyczą całego wywołania, więc połknięte dałyby użytkownikowi pusty
    plan bez przyczyny — co wygląda identycznie jak „brak danych dla tego
    miasta". Dlatego przerywają plan i wychodzą na zewnątrz jako 502.
    """


class QlooAuthError(QlooFatalError):
    """401/403 — zły klucz albo klucz użyty z niewłaściwym hostem."""


class QlooConnectionError(QlooFatalError):
    """Sieć, DNS, timeout albo nieosiągalny ``QLOO_BASE_URL``."""


@dataclass
class QlooClient:
    settings: Settings
    _cache: dict[str, tuple[float, dict[str, Any]]] = field(default_factory=dict)
    _transport: httpx.BaseTransport | None = None
    #: Rozmiar strony wysyłany do Insights API. Jest to udokumentowany parametr
    #: ``take`` (1–50, domyślnie 20) — patrz ``insights()`` poniżej.
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

    def _get(self, path: str, params: dict[str, Any], allow_empty_on_404: bool = False) -> dict[str, Any]:
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
            raise QlooConnectionError(
                f"Nie udało się połączyć z Qloo ({exc.__class__.__name__}). "
                f"Sprawdź QLOO_BASE_URL — dla klucza hackathonowego musi to być "
                "https://hackathon.api.qloo.com."
            ) from exc

        if response.status_code == 401:
            raise QlooAuthError(
                "401 Unauthorized. Klucz hackathonowy działa wyłącznie z "
                "https://hackathon.api.qloo.com — sprawdź QLOO_BASE_URL i QLOO_API_KEY."
            )
        if response.status_code == 403:
            raise QlooAuthError(
                "403 Forbidden. Ten typ encji nie jest objęty Twoim kluczem "
                "(np. muzyka to 'urn:entity:artist', nie 'urn:entity:music')."
            )
        if response.status_code == 404 and allow_empty_on_404:
            # /search dokumentuje 404 jako „No results” — to normalny wynik,
            # nie awaria. Zwracamy pusty zestaw zamiast rzucać wyjątkiem.
            return {"results": []}
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

    def search_entities(self, query: str, types: list[str] | None = None, take: int = 5) -> list[dict[str, Any]]:
        """Rozwiązuje nazwę („Sting”, „Barszcz”) na identyfikator encji Qloo.

        Dwie rzeczy z dokumentacji ``/search``, na które tu uważamy:
          * rozmiar wyniku to ``take``, nie ``size`` — parametr spoza dokumentacji
            zostałby po cichu zignorowany,
          * ``404`` znaczy „No results”, nie awarię.

        ``/search`` akceptuje też inny zbiór typów niż ``filter.type`` w Insights
        (m.in. ``urn:entity:locality``, ``urn:entity:actor``), więc nie wolno ich mieszać.
        """
        params: dict[str, Any] = {"query": query, "take": max(1, int(take)), "sort_by": "match"}
        if types:
            params["types"] = ",".join(types)
        payload = self._get("/search", params, allow_empty_on_404=True)
        return payload.get("results", []) or []

    def search_tags(self, query: str) -> list[dict[str, Any]]:
        """Znajduje poprawne identyfikatory tagów — ``filter.tags`` nie przyjmuje wolnego tekstu.

        Wysyłamy WYŁĄCZNIE ``query``. Istnienie tego endpointu i jego przeznaczenie
        potwierdza przewodnik hackathonowy, ale jego strona referencyjna zwraca 404,
        więc nie znamy reszty parametrów. Wcześniej był tu ``take`` przepisany
        z ``/search`` — a przewodnik ostrzega, że parametr spoza dokumentacji jest
        po cichu ignorowany. Lepiej nie wysyłać nic niezweryfikowanego.

        Metoda nie jest na razie używana przez planer; zostaje jako potwierdzone
        w dokumentacji wejście do rozszerzenia o sygnały tagowe.
        """
        payload = self._get("/v2/tags", {"query": query}, allow_empty_on_404=True)
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

        # Rozmiar wyniku to udokumentowany `take` (1–50, domyślnie 20), a paginacja
        # idzie przez `page`. Pilnujemy granic, bo przewodnik ostrzega, że parametr
        # spoza dokumentacji jest po cichu ignorowany i daje pusty wynik bez błędu.
        self.page_size = max(1, min(int(results_per_page), 50))
        params["take"] = self.page_size
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
    def item_id(item: dict[str, Any]) -> str:
        """Identyfikator encji.

        Udokumentowana odpowiedź Insights używa ``entity_id`` (np.
        ``"entity_id": "F0D354AA-BA7E-49D2-8ABA-9A8250F5C852"``), nie ``id``.
        Bez tego ``qloo_id`` byłby pusty, a przycisk „to nie to” nigdy by się
        nie pojawił — bo wykluczanie nie miałoby czego wykluczyć.
        """
        return str(item.get("entity_id") or item.get("id") or item.get("_id") or "")

    @staticmethod
    def item_name(item: dict[str, Any]) -> str:
        return str(item.get("name") or (item.get("properties") or {}).get("name") or "bez nazwy")

    @staticmethod
    def item_affinity(item: dict[str, Any]) -> float:
        """Wynik dopasowania.

        Kolejność jest celowa: najpierw pola afinacji, a ``query.affinity``
        jako miejsce, w którym Insights API trzyma ranking. ``popularity``
        NIE jest tu używane — to inna miara i podstawianie jej pod afinację
        pokazywałoby użytkownikowi nieprawdę.
        """
        for key in ("affinity", "score", "affinity_score"):
            value = item.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        query = item.get("query") or {}
        for key in ("affinity", "score"):
            value = query.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return 0.0

    @staticmethod
    def item_tags(item: dict[str, Any]) -> list[str]:
        """Tagi jako czytelne nazwy.

        W odpowiedzi Qloo tag to obiekt ``{"id", "name", "type"}``, nie napis.
        Samo ``str(t)`` wypisałoby do UI cały słownik.
        """
        tags = item.get("tags")
        if not isinstance(tags, list):
            return []
        out: list[str] = []
        for tag in tags[:8]:
            if isinstance(tag, dict):
                out.append(str(tag.get("name") or tag.get("id") or "").strip())
            elif isinstance(tag, str):
                out.append(tag)
        return [t for t in out if t]

    @staticmethod
    def item_description(item: dict[str, Any]) -> str:
        props = item.get("properties") or {}
        return str(item.get("description") or props.get("description") or "")

    @staticmethod
    def item_image(item: dict[str, Any]) -> str | None:
        """URL obrazka.

        W odpowiedzi Qloo ``properties.image`` to obiekt ``{"url": ...}``,
        więc ``str(image)`` dałby ``"{'url': 'https://...'}"`` jako src.
        """
        props = item.get("properties") or {}
        for candidate in (item.get("image"), props.get("image")):
            if isinstance(candidate, dict):
                url = candidate.get("url")
                if url:
                    return str(url)
            elif isinstance(candidate, str) and candidate:
                return candidate
        return None

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
