# Tekst zgłoszenia — Qloo Agentic Hackathon

Poniżej gotowe bloki do wklejenia na Devpost. Pola w `<nawiasach>` uzupełnij przed
wysłaniem (publiczny URL, Twoje imię/nazwisko).

> **Uwaga przed wysłaniem:** tekst zakłada, że demo działa na prawdziwym kluczu
> Qloo. Bez `QLOO_API_KEY` aplikacja jest w trybie demo na fixture'ach — to
> widać w interfejsie i **nie wolno** tego zgłaszać jako działające demo
> (wymóg: *„Your demo must be hosted and fully published externally”*).
> Klucz: <https://forms.gle/zz12orkLHTAneLGz6>.

---

## Project Name

Smak Domu (Taste of Home) — a culture bridge for new arrivals

## Tagline

A cultural landing plan for people who just moved countries, built on Qloo
taste affinities.

## Inspiration

When someone moves countries, the practical advice arrives fast — bank account,
registration, SIM card. The cultural part gets a generic answer: "see the old
town, try the local dumplings."

That answer ignores the one thing the newcomer already knows: what they like
back home. Someone arriving in Poznań from Lviv has a taste profile — the music,
the films, the food. Nobody asks them about it, and nothing maps it onto the new
city.

Smak Domu starts from exactly that input. You give it a few anchors from home.
It returns a plan for your first month — films, places, food, music, podcasts —
and for every item it tells you **why it showed up**, naming the anchor that
pulled it and with what weight.

## What it does

1. **Resolve.** Anchor names ("Okean Elzy", "borscht", "Amélie") are resolved to
   Qloo entity IDs via `/search`.
2. **Fan out.** One `/v2/insights` request per domain — films, artists, places,
   podcasts, books, brands, weekend destinations — all carrying the same
   anchors, with `feature.explainability=true`. Location-aware domains also get
   `filter.location.query` set to the destination city.
3. **Compose.** Results become a "first 30 days" plan, grouped by domain, each
   item with its affinity score, tags, and the explainability trail behind it.
4. **Refine.** Every item has a "not this" button. It feeds the entity into
   `filter.exclude.entities` and recomputes the plan.

Step 4 is the loop that makes it agentic rather than a one-shot lookup: the plan
responds to what you reject, not just to what you typed at the start.

## How we built it

FastAPI backend, vanilla JS frontend, no framework lock-in.

The planner (`app/planner.py`) owns the resolve → fan-out → compose → refine
cycle. The Qloo client (`app/qloo_client.py`) is the only place that talks to
the API; it uses `X-Api-Key` against `hackathon.api.qloo.com` and treats a 404
from `/search` as "no results" rather than a failure.

An optional narration layer (`app/narrator.py`) turns the explainability trail
into a sentence. It falls back to a deterministic narrator on any failure, so a
model outage never breaks the plan.

84 tests. The integration suite (`tests/test_qloo_integration.py`) runs the
documented Insights response shape through the whole planner, which is what
caught two production bugs — both in code paths that only execute with a real
key.

## Challenges we ran into

**The API stays silent instead of failing.** Per the docs, a parameter that
doesn't apply to the given `filter.type` is quietly ignored and you get `200`
with an empty list. That means a typo looks identical to "nothing matches." We
treat an empty result as a diagnostic signal in the UI instead of rendering an
empty plan.

**Response shape is not what the parameter list suggests.** Entities carry
`entity_id`, not `id`. `tags` is a list of objects (`{id, name, type}`), not
strings. `image` lives at `properties.image.url`. We wrote the parser against
the documented example response rather than against the parameter reference, and
the integration suite now pins that shape.

**Result size is `take`, not `size`.** We had a `size` parameter copied from
`/search` into two other calls; it was being ignored, so result size was never
actually applied. There is now a test that asserts the exact set of parameters
sent, and a guard against undocumented names creeping back in.

## Why it needs Qloo

A language model will happily suggest "try the dumplings" and invent a
restaurant to go with it. It does not know the affinity between Okean Elzy and
Polish folk, or which arthouse cinema in Poznań programs films close to *Amélie*.

Qloo supplies three things this app cannot produce on its own:

- **Real affinities between entities in a specific city** (`filter.location.query`)
- **Explainability** (`feature.explainability=true`) — which input entities
  drove a recommendation, weighted 0–1
- **Cross-domain taste** — music → film → place → podcast in one profile

Remove Qloo and there is nothing left to display. The demo mode that runs before
an API key arrives is deterministic fixture data, labelled as such in the UI,
and it exists only so the interface could be built ahead of key issuance.

## Accomplishments that we're proud of

- The "not this" loop: rejecting an item actually reshapes the plan, through
  `filter.exclude.entities`, not by client-side filtering.
- Explainability surfaced as a first-class UI element rather than buried in a
  tooltip.
- 84 tests including an end-to-end suite on the documented response shape.

## What we learned

Read the example response, not just the parameter reference. Every bug in this
project came from assuming a shape the docs never promised, and each one would
have surfaced only after an API key was in place.

## What's next for Smak Domu

- Multi-city comparison: same taste profile, two cities, side by side.
- Calendar handoff — turn the plan into real reservations and event entries.
- Community layer: newcomers in the same city sharing anchor profiles.

## Built with

FastAPI · Qloo Insights API · vanilla JavaScript · Uvicorn

## Links

- Live demo: <PUBLIC_URL>
- Source: <https://github.com/peteraangelic-pixel/KonkursyMat> (MIT)

---

# Krótka wersja (jeśli jest limit znaków)

Smak Domu turns "what I liked back home" into a first-month cultural plan in a
new city. You give it anchors from home — music, film, food. It resolves them to
Qloo entities, fans out one `/v2/insights` call per domain with
`feature.explainability=true`, and returns films, places, food and music for
your destination city. Every item says which anchor pulled it and how strongly.
A "not this" button feeds `filter.exclude.entities` and recomputes the plan.

Without Qloo there is nothing to show: the affinities, the explainability trail
and the cross-domain taste profile all come from it. A language model will
suggest "try the dumplings" and invent a restaurant. It cannot tell you which
arthouse cinema in Poznań programs films close to *Amélie*.

FastAPI + vanilla JS, 84 tests including an end-to-end suite on the documented
Insights response shape. MIT licensed.
