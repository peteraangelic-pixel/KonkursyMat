"""Dostawca danych o smaku.

Dwie implementacje jednego protokołu:
  * ``QlooClient`` — prawdziwe API Qloo,
  * ``DemoProvider`` — deterministyczne fixture'y.

Dzięki temu planer działa identycznie w obu trybach, a testy przechodzą
przez tę samą ścieżkę kodu, która obsługuje produkcyjne wywołania.

Tryb demo istnieje z jednego powodu: klucz Qloo jest wydawany ręcznie i czeka
się na niego kilka dni roboczych. Aplikacja musi działać i dać się zademonstrować
zanim klucz przyjdzie. Każda encja z demo jest oznaczona ``source="demo"``
i UI pokazuje wyraźny baner — nie udajemy, że to dane Qloo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .qloo_client import QlooClient


class TasteProvider(Protocol):
    """Minimalny kontrakt, jakiego potrzebuje planer."""

    def search_entities(self, query: str, types: list[str] | None = None, take: int = 5) -> list[dict[str, Any]]: ...

    def insights(self, filter_type: str, **kwargs: Any) -> dict[str, Any]: ...

    @staticmethod
    def extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]: ...

    @staticmethod
    def explainability_for(item: dict[str, Any]) -> list[dict[str, Any]]: ...

    @staticmethod
    def item_id(item: dict[str, Any]) -> str: ...

    @staticmethod
    def item_name(item: dict[str, Any]) -> str: ...

    @staticmethod
    def item_affinity(item: dict[str, Any]) -> float: ...

    @staticmethod
    def item_tags(item: dict[str, Any]) -> list[str]: ...

    @staticmethod
    def item_description(item: dict[str, Any]) -> str: ...

    @staticmethod
    def item_image(item: dict[str, Any]) -> str | None: ...

    @staticmethod
    def item_address(item: dict[str, Any]) -> str: ...


# ----------------------------------------------------------------------------
# Fixture'y demo
# ----------------------------------------------------------------------------

# Kotwice rozpoznawane w trybie demo. Klucze celowo małe i bez znaków
# diakrytycznych, żeby „Okean Elzy” i „okean elzy” trafiły w to samo.
_DEMO_ANCHORS: dict[str, dict[str, str]] = {
    "okean elzy": {"id": "demo-artist-okean", "type": "urn:entity:artist", "name": "Okean Elzy"},
    "sting": {"id": "demo-artist-sting", "type": "urn:entity:artist", "name": "Sting"},
    "barszcz": {"id": "demo-tag-borscht", "type": "urn:tag:cuisine:ukrainian", "name": "barszcz"},
    "pierogi": {"id": "demo-tag-dumplings", "type": "urn:tag:cuisine:polish", "name": "pierogi"},
    "amielie": {"id": "demo-movie-amelie", "type": "urn:entity:movie", "name": "Amélie"},
    "amelie": {"id": "demo-movie-amelie", "type": "urn:entity:movie", "name": "Amélie"},
    "parasite": {"id": "demo-movie-parasite", "type": "urn:entity:movie", "name": "Parasite"},
}


def _normalize(text: str) -> str:
    table = str.maketrans(
        {"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z",
         "é": "e", "è": "e", "ë": "e", "à": "a", "á": "a", "ö": "o", "ü": "u", "í": "i"}
    )
    return text.strip().lower().translate(table)


_DEMO_RESULTS: dict[str, list[dict[str, Any]]] = {
    "urn:entity:movie": [
        {
            "id": "demo-movie-atlantics",
            "name": "Atlantique",
            "affinity": 0.83,
            "tags": ["urn:tag:genre:media:drama", "urn:tag:origin:france"],
            "description": "Dramat z wątkiem nadprzyrodzonym; rytm narracji bliski kinu, które lubisz z domu.",
            "properties": {"geocode": {"name": "Poznań", "country_code": "PL"}},
            "query": {"explainability": {"entities": [
                {"id": "demo-movie-amelie", "name": "Amélie", "score": 0.71},
                {"id": "demo-artist-okean", "name": "Okean Elzy", "score": 0.34},
            ]}},
        },
        {
            "id": "demo-movie-cold-war",
            "name": "Zimna wojna",
            "affinity": 0.78,
            "tags": ["urn:tag:genre:media:romance", "urn:tag:origin:poland"],
            "description": "Polski film o muzyce i emigracji — naturalny most między domem a nowym krajem.",
            "properties": {"geocode": {"name": "Poznań", "country_code": "PL"}},
            "query": {"explainability": {"entities": [
                {"id": "demo-artist-okean", "name": "Okean Elzy", "score": 0.66},
            ]}},
        },
        {
            "id": "demo-movie-ida",
            "name": "Ida",
            "affinity": 0.71,
            "tags": ["urn:tag:genre:media:drama", "urn:tag:origin:poland"],
            "description": "Oszczędna forma, dużo niedopowiedzeń — jeśli lubisz kino, które ufa widzowi.",
            "properties": {"geocode": {"name": "Poznań", "country_code": "PL"}},
            "query": {"explainability": {"entities": [
                {"id": "demo-movie-amelie", "name": "Amélie", "score": 0.58},
            ]}},
        },
    ],
    "urn:entity:artist": [
        {
            "id": "demo-artist-daga",
            "name": "DagaDana",
            "affinity": 0.86,
            "tags": ["urn:tag:genre:music:folk", "urn:tag:origin:poland"],
            "description": "Polsko-ukraiński duet folkowy — dosłownie most między dwiema tradycjami.",
            "properties": {"geocode": {"name": "Poznań", "country_code": "PL"}},
            "query": {"explainability": {"entities": [
                {"id": "demo-artist-okean", "name": "Okean Elzy", "score": 0.88},
            ]}},
        },
        {
            "id": "demo-artist-kwiat",
            "name": "Kwiat Jabłoni",
            "affinity": 0.74,
            "tags": ["urn:tag:genre:music:folk_pop", "urn:tag:origin:poland"],
            "description": "Współczesny folk z akustycznym rdzeniem; podobna wrażliwość na melodię.",
            "properties": {"geocode": {"name": "Poznań", "country_code": "PL"}},
            "query": {"explainability": {"entities": [
                {"id": "demo-artist-okean", "name": "Okean Elzy", "score": 0.61},
            ]}},
        },
        {
            "id": "demo-artist-lem",
            "name": "LemON",
            "affinity": 0.69,
            "tags": ["urn:tag:genre:music:rock", "urn:tag:origin:poland"],
            "description": "Rock z wschodnim akcentem wokalnym — bliski brzmieniu, z którego przyjeżdżasz.",
            "properties": {"geocode": {"name": "Poznań", "country_code": "PL"}},
            "query": {"explainability": {"entities": [
                {"id": "demo-artist-okean", "name": "Okean Elzy", "score": 0.55},
            ]}},
        },
    ],
    "urn:entity:place": [
        {
            "id": "demo-place-bar-a-miel",
            "name": "Bar a Mleczny",
            "affinity": 0.81,
            "tags": ["urn:tag:cuisine:polish", "urn:tag:price:low"],
            "description": "Bar mleczny — najtańszy sposób, żeby zrozumieć codzienną kuchnię nowego miasta.",
            "address": "Św. Marcin, Poznań",
            "properties": {"geocode": {"name": "Poznań", "country_code": "PL"}},
            "query": {"explainability": {"entities": [
                {"id": "demo-tag-borscht", "name": "barszcz", "score": 0.74},
            ]}},
        },
        {
            "id": "demo-place-ukrainska",
            "name": "Ukraińska Chata",
            "affinity": 0.88,
            "tags": ["urn:tag:cuisine:ukrainian"],
            "description": "Smak domu na miejscu — punkt startowy, od którego łatwiej ruszyć dalej.",
            "address": "Jeżyce, Poznań",
            "properties": {"geocode": {"name": "Poznań", "country_code": "PL"}},
            "query": {"explainability": {"entities": [
                {"id": "demo-tag-borscht", "name": "barszcz", "score": 0.92},
            ]}},
        },
        {
            "id": "demo-place-kino-muze",
            "name": "Kino Muza",
            "affinity": 0.76,
            "tags": ["urn:tag:venue:cinema", "urn:tag:culture:arthouse"],
            "description": "Kino studyjne z repertuarem, do którego pasują filmy z Twojej listy.",
            "address": "Św. Marcin, Poznań",
            "properties": {"geocode": {"name": "Poznań", "country_code": "PL"}},
            "query": {"explainability": {"entities": [
                {"id": "demo-movie-amelie", "name": "Amélie", "score": 0.68},
            ]}},
        },
    ],
    "urn:entity:podcast": [
        {
            "id": "demo-podcast-dwojka",
            "name": "Dwójka: Kultura w dobrym gatunku",
            "affinity": 0.72,
            "tags": ["urn:tag:topic:culture", "urn:tag:language:polish"],
            "description": "Osłuchanie się z językiem przez temat, który i tak Cię interesuje.",
            "properties": {},
            "query": {"explainability": {"entities": [
                {"id": "demo-movie-amelie", "name": "Amélie", "score": 0.49},
            ]}},
        },
    ],
}


@dataclass
class DemoProvider:
    """Zwraca fixture'y w kształcie odpowiedzi Qloo, bez dostępu do sieci."""

    page_size: int = 6

    def search_entities(self, query: str, types: list[str] | None = None, take: int = 5) -> list[dict[str, Any]]:
        hit = _DEMO_ANCHORS.get(_normalize(query))
        if not hit:
            return []
        return [{"id": hit["id"], "name": hit["name"], "type": hit["type"]}]

    def insights(self, filter_type: str, **kwargs: Any) -> dict[str, Any]:
        """Zwraca fixture'y, ale uczciwie przypisane do WPROWADZONYCH kotwic.

        Fixture'y mają na sztywno wpisane czynniki (np. „barszcz”), a użytkownik
        mógł ich nie podać. Dlatego filtrujemy czynniki do tych, które faktycznie
        przyszły w `interest_entities`, i odrzucamy pozycje bez żadnego powiązania
        — tak samo zachowuje się prawdziwe API, gdzie wynik wynika z sygnału.
        """
        exclude = set(kwargs.get("exclude_entities") or [])
        interest = set(kwargs.get("interest_entities") or [])

        # Bez kotwic nie ma z czego wynikać — nie zwracamy nic, zamiast
        # pokazywać pozycje z pustym uzasadnieniem. (Prawdziwe /v2/insights
        # wymaga co najmniej jednego poprawnego sygnału, więc zachowanie jest spójne.)
        if not interest:
            return {"results": [], "_demo": True}

        out: list[dict[str, Any]] = []
        for item in _DEMO_RESULTS.get(filter_type, []):
            if item["id"] in exclude:
                continue
            drivers = ((item.get("query") or {}).get("explainability") or {}).get("entities") or []
            kept = [d for d in drivers if d["id"] in interest]
            if not kept:
                continue
            patched = dict(item)
            patched["query"] = {"explainability": {"entities": kept}}
            out.append(patched)
        return {"results": out, "_demo": True}

    @staticmethod
    def extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        results = payload.get("results")
        return results if isinstance(results, list) else []

    @staticmethod
    def explainability_for(item: dict[str, Any]) -> list[dict[str, Any]]:
        drivers = ((item.get("query") or {}).get("explainability") or {}).get("entities") or []
        return [
            {
                "entity_id": str(d.get("id", "")),
                "entity_name": str(d.get("name", "")),
                "score": float(d.get("score", 0.0)),
            }
            for d in drivers
        ]

    @staticmethod
    def item_id(item: dict[str, Any]) -> str:
        # Fixture'y używają `id`, prawdziwe API `entity_id` — obsługujemy oba,
        # żeby ścieżka kodu była wspólna dla trybu demo i produkcyjnego.
        return str(item.get("entity_id") or item.get("id") or "")

    @staticmethod
    def item_name(item: dict[str, Any]) -> str:
        return str(item.get("name") or "bez nazwy")

    @staticmethod
    def item_affinity(item: dict[str, Any]) -> float:
        return float(item.get("affinity") or 0.0)

    @staticmethod
    def item_tags(item: dict[str, Any]) -> list[str]:
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
        return str(item.get("description") or "")

    @staticmethod
    def item_image(item: dict[str, Any]) -> str | None:
        return None

    @staticmethod
    def item_address(item: dict[str, Any]) -> str:
        return str(item.get("address") or "")


def build_provider(settings: Any) -> tuple[TasteProvider, str]:
    """Wybiera dostawcę na podstawie konfiguracji. Zwraca (dostawca, źródło)."""
    if getattr(settings, "qloo_enabled", False):
        return QlooClient(settings=settings), "qloo"
    return DemoProvider(), "demo"
