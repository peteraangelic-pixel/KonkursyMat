"""Planer agentowy Culture Bridge.

Pętla agenta wygląda tak:

  1. **resolve**  — kotwice smakowe (nazwy wpisane przez człowieka) zamieniamy
                    na identyfikatory encji Qloo przez ``/search``.
  2. **fan-out**  — dla każdej domeny (film, muzyka, miejsca, podcast) osobne
                    zapytanie do ``/v2/insights`` z tymi samymi kotwicami,
                    plus ``feature.explainability=true``.
  3. **compose**  — składamy plan „pierwszych 30 dni” i dopisujemy do każdej
                    pozycji powód: która kotwica i z jaką siłą ją pociągnęła.
  4. **refine**   — „to nie to” dokłada identyfikatory do ``filter.exclude.*``
                    i przechodzi pętlę jeszcze raz.

Sedno pomysłu: sam model językowy podpowie „spróbuj pierogów” i zmyśli lokale.
Qloo daje prawdziwe afinacje między encjami w konkretnym mieście i pozwala
powiedzieć *dlaczego* — to jest ta różnica między „technicznie działa”
a „naprawdę dobre”, o którą prosi brief konkursu.
"""

from __future__ import annotations

from typing import Any

from .models import (
    ENTITY_ARTIST,
    ENTITY_MOVIE,
    ENTITY_PLACE,
    ENTITY_PODCAST,
    Anchor,
    DomainSection,
    ExplainabilityEntry,
    LandingPlan,
    PlanRequest,
    Recommendation,
)
from .narrator import DeterministicNarrator, Narrator
from .provider import TasteProvider
from .qloo_client import QlooError, QlooFatalError

DOMAIN_LABELS = {
    ENTITY_MOVIE: "Filmy i seriale",
    "urn:entity:tv_show": "Seriale",
    ENTITY_ARTIST: "Muzyka i koncerty",
    ENTITY_PLACE: "Miejsca i jedzenie",
    ENTITY_PODCAST: "Podcasty i osłuchanie się z językiem",
    "urn:entity:book": "Książki",
    "urn:entity:brand": "Marki i sklepy",
    "urn:entity:destination": "Wycieczki na weekend",
}

# Domeny, w których pytamy o konkretną miejscowość — tylko miejsca mają geokod.
LOCATION_AWARE = {ENTITY_PLACE, "urn:entity:destination", "urn:entity:brand"}


def _shorten(text: str, limit: int = 260) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


class Planner:
    def __init__(
        self, provider: TasteProvider, source: str, narrator: Narrator | None = None
    ) -> None:
        self.provider = provider
        self.source = source
        # Narrator jest wstrzykiwany, więc planer nie wie, czy zdanie podsumowujące
        # powstało deterministycznie, czy przez model — i nie musi wiedzieć.
        self.narrator: Narrator = narrator or DeterministicNarrator()

    # ------------------------------------------------------------- 1. resolve

    def resolve_anchor(self, anchor: Anchor) -> Anchor:
        """Rozwiązuje nazwę na identyfikator Qloo. Nieudane rozwiązanie nie blokuje planu."""
        if anchor.qloo_id:
            anchor.resolved = True
            return anchor

        search_types: list[str] | None = None
        if anchor.kind == "artist":
            search_types = ["urn:entity:artist"]
        elif anchor.kind in ("movie", "tv_show"):
            search_types = ["urn:entity:movie", "urn:entity:tv_show"]

        try:
            hits = self.provider.search_entities(anchor.name, types=search_types, take=3)
        except QlooFatalError:
            # Zły klucz albo nieosiągalne API dotyczy każdego zapytania — nie ma
            # sensu udawać, że ta jedna kotwica się nie rozwiązała, i brnąć
            # dalej z pustym planem.
            raise
        except QlooError:
            return anchor

        if hits:
            top = hits[0]
            # Qloo zwraca `entity_id`, nie `id` — ten sam rozjazd, który naprawiliśmy
            # w kliencie dla wyników Insights. Bez tego każda kotwica zostawała
            # nierozwiązana, a plan powstawał bez żadnego sygnału.
            anchor.qloo_id = str(top.get("entity_id") or top.get("id") or top.get("_id") or "")
            # `type` w odpowiedzi Qloo to ogólne "urn:entity"; konkretny typ jest w `subtype`.
            anchor.qloo_type = str(top.get("subtype") or top.get("type") or "")
            anchor.resolved = bool(anchor.qloo_id)
        return anchor

    # -------------------------------------------------------------- 2. fan-out

    def _query_domain(self, request: PlanRequest, domain: str, anchor_ids: list[str]) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {
            "interest_entities": anchor_ids or None,
            "exclude_entities": request.exclude_entities or None,
            "exclude_tags": request.exclude_tags or None,
            "age_range": request.age_range,
            "results_per_page": request.per_domain,
            "explainability": True,
        }
        if domain in LOCATION_AWARE and request.destination:
            kwargs["location_query"] = request.destination

        payload = self.provider.insights(domain, **kwargs)
        items = self.provider.extract_items(payload)
        return items[: request.per_domain]

    # -------------------------------------------------------------- 3. compose

    def _to_recommendation(self, item: dict[str, Any], domain: str, anchor_names: dict[str, str]) -> Recommendation:
        drivers: list[ExplainabilityEntry] = []
        for d in self.provider.explainability_for(item):
            name = d["entity_name"] or anchor_names.get(d["entity_id"], "")
            drivers.append(
                ExplainabilityEntry(entity_id=d["entity_id"], entity_name=name, score=d["score"])
            )
        drivers.sort(key=lambda x: -x.score)

        top = drivers[0] if drivers else None
        if top and top.entity_name:
            why = f"Dopasowanie {top.score:.0%} przez: {top.entity_name}"
        elif drivers:
            why = "Dopasowanie na podstawie Twoich kotwic smakowych"
        else:
            why = "Brak danych o wyjaśnialności dla tej pozycji"

        return Recommendation(
            qloo_id=self.provider.item_id(item),
            name=self.provider.item_name(item),
            domain=domain,
            affinity=self.provider.item_affinity(item),
            tags=self.provider.item_tags(item),
            description=_shorten(self.provider.item_description(item)),
            image=self.provider.item_image(item),
            address=self.provider.item_address(item),
            why=why,
            drivers=drivers,
            source="qloo" if self.source == "qloo" else "demo",
        )

    def _build_weeks(self, sections: list[DomainSection]) -> list[dict[str, Any]]:
        """Rozkłada plan na cztery tygodnie — po jednym kroku z każdej domeny."""
        pools = {s.domain: list(s.items) for s in sections if s.items}
        weeks: list[dict[str, Any]] = []
        for week in range(1, 5):
            steps: list[dict[str, Any]] = []
            for domain, items in pools.items():
                if len(items) >= week:
                    item = items[week - 1]
                    steps.append(
                        {
                            "label": DOMAIN_LABELS.get(domain, domain),
                            "name": item.name,
                            "why": item.why,
                        }
                    )
            if steps:
                weeks.append({"week": week, "steps": steps})
        return weeks

    def build_plan(self, request: PlanRequest) -> LandingPlan:
        warnings: list[str] = []
        qloo_calls = 0

        # 1. resolve — tylko encje mają identyfikatory; wolnotekstowe kotwice
        #    (np. „barszcz”) pomijamy w sygnale, bo /v2/insights wymaga ID.
        resolved: list[Anchor] = []
        for anchor in request.anchors:
            resolved.append(self.resolve_anchor(anchor))
            if anchor.qloo_id:
                qloo_calls += 1

        anchor_ids = [a.qloo_id for a in resolved if a.qloo_id]
        anchor_names = {a.qloo_id: a.name for a in resolved if a.qloo_id}
        unresolved = [a.name for a in resolved if not a.qloo_id]
        if unresolved:
            warnings.append(
                "Nie udało się rozwiązać w Qloo: " + ", ".join(unresolved)
                + ". Te kotwice nie wpłynęły na rekomendacje."
            )
        if not anchor_ids and self.source == "qloo":
            warnings.append(
                "Brak rozwiązanych kotwic — /v2/insights wymaga co najmniej jednego "
                "poprawnego sygnału, więc wyniki mogą być puste."
            )

        # 2. fan-out + 3. compose
        sections: list[DomainSection] = []
        for domain in request.domains:
            label = DOMAIN_LABELS.get(domain, domain)
            try:
                items = self._query_domain(request, domain, anchor_ids)
                qloo_calls += 1
            except QlooFatalError:
                # 401/403 albo nieosiągalne API to błąd konfiguracji, nie brak
                # danych dla tej domeny. Połknięty wyglądałby jak „pusty wynik",
                # a pozostałe domeny padłyby z tej samej przyczyny — przerywamy
                # i zgłaszamy 502.
                raise
            except QlooError as exc:
                sections.append(DomainSection(domain=domain, label=label, items=[], note=str(exc)))
                warnings.append(f"{label}: {exc}")
                continue

            recs = [self._to_recommendation(item, domain, anchor_names) for item in items]
            note = ""
            if not recs:
                note = (
                    "Pusty wynik. Najczęstsza przyczyna wg dokumentacji Qloo: parametr "
                    f"nieobsługiwany dla {domain} (API milczy zamiast zgłosić błąd) albo "
                    "brak danych dla tej miejscowości w środowisku hackathonowym."
                )
            sections.append(DomainSection(domain=domain, label=label, items=recs, note=note))

        weeks = self._build_weeks(sections)
        narrative = self.narrator.narrate(
            origin=request.origin,
            destination=request.destination,
            anchors=resolved,
            sections=sections,
        )

        if self.source == "demo":
            warnings.insert(
                0,
                "TRYB DEMO: brak QLOO_API_KEY. Poniższe pozycje to fixture'y, "
                "nie dane Qloo — służą wyłącznie do pokazania działania aplikacji.",
            )

        return LandingPlan(
            origin=request.origin,
            destination=request.destination,
            sections=sections,
            narrative=narrative,
            weeks=weeks,
            data_source="qloo" if self.source == "qloo" else "demo",
            qloo_calls=qloo_calls,
            warnings=warnings,
        )


