"""Schematy danych przepływających przez aplikację."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# Typy encji wspierane przez Insights API na czas hackathonu.
# Uwaga: przewodnik hackathonowy wymienia `urn:entity:video_game`,
# a przegląd parametrów `urn:entity:videogame` — trzymamy obie nazwy
# i rozstrzygamy to w kliencie, bo API milczy zamiast zgłaszać błąd.
ENTITY_MOVIE = "urn:entity:movie"
ENTITY_TV_SHOW = "urn:entity:tv_show"
ENTITY_ARTIST = "urn:entity:artist"
ENTITY_PLACE = "urn:entity:place"
ENTITY_PODCAST = "urn:entity:podcast"
ENTITY_BOOK = "urn:entity:book"
ENTITY_BRAND = "urn:entity:brand"
ENTITY_DESTINATION = "urn:entity:destination"


class Anchor(BaseModel):
    """Kotwica smakowa z kraju pochodzenia — punkt wyjścia całego planu."""

    name: str = Field(..., min_length=1, description="Nazwa wpisana przez użytkownika")
    kind: Literal["artist", "movie", "tv_show", "dish", "free"] = "free"
    qloo_id: str | None = None
    qloo_type: str | None = None
    resolved: bool = False


class PlanRequest(BaseModel):
    """Żądanie wygenerowania planu kulturowego lądowania."""

    origin: str = Field(..., min_length=1, description="Kraj/miasto pochodzenia")
    destination: str = Field(..., min_length=1, description="Miasto docelowe")
    anchors: list[Anchor] = Field(default_factory=list)
    notes: str = ""
    age_range: str | None = None
    # Pętla doprecyzowania: użytkownik mówi „to nie to", my wykluczamy.
    exclude_entities: list[str] = Field(default_factory=list)
    exclude_tags: list[str] = Field(default_factory=list)
    domains: list[str] = Field(
        default_factory=lambda: [ENTITY_MOVIE, ENTITY_ARTIST, ENTITY_PLACE, ENTITY_PODCAST]
    )
    per_domain: int = Field(default=6, ge=1, le=20)


class ExplainabilityEntry(BaseModel):
    """Która kotwica i z jaką siłą pociągnęła tę rekomendację."""

    entity_id: str
    entity_name: str = ""
    score: float = 0.0


class Recommendation(BaseModel):
    qloo_id: str
    name: str
    domain: str
    affinity: float = 0.0
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    image: str | None = None
    address: str = ""
    why: str = ""
    drivers: list[ExplainabilityEntry] = Field(default_factory=list)
    source: Literal["qloo", "demo"] = "demo"


class DomainSection(BaseModel):
    domain: str
    label: str
    items: list[Recommendation] = Field(default_factory=list)
    note: str = ""


class LandingPlan(BaseModel):
    origin: str
    destination: str
    sections: list[DomainSection] = Field(default_factory=list)
    narrative: str = ""
    weeks: list[dict[str, Any]] = Field(default_factory=list)
    data_source: Literal["qloo", "demo"] = "demo"
    qloo_calls: int = 0
    warnings: list[str] = Field(default_factory=list)
