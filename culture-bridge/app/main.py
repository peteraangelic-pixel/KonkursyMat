"""Serwer Culture Bridge / Smak Domu.

Aplikacja FastAPI serwująca API planera i statyczny frontend.
Celowo bez etapu budowania frontendu — dzięki temu da się to hostować
gdziekolwiek, co jest wymogiem konkursu („demo must be hosted and fully
published externally”).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import load_settings
from .models import LandingPlan, PlanRequest
from .narrator import build_narrator
from .planner import DOMAIN_LABELS, Planner
from .provider import build_provider
from .qloo_client import QlooError

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="Culture Bridge / Smak Domu",
    description=(
        "Agentowy plan kulturowego lądowania dla osób, które właśnie zmieniły kraj. "
        "Rekomendacje wynikają z afinacji smaku w Qloo, nie z generycznej listy przebojów."
    ),
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/health")
def health() -> dict[str, object]:
    settings = load_settings()
    _, llm_active = build_narrator(settings)
    return {
        "status": "ok",
        "qloo_connected": settings.qloo_enabled,
        "data_source": "qloo" if settings.qloo_enabled else "demo",
        "qloo_base_url": settings.qloo_base_url,
        # Raportujemy to, co faktycznie zbudowano — nie samą obecność klucza.
        "llm_enabled": llm_active,
    }


@app.get("/api/domains")
def domains() -> dict[str, list[dict[str, str]]]:
    """Domeny, które planer potrafi obsłużyć — frontend rysuje z tego wybór."""
    return {
        "domains": [
            {"id": key, "label": label} for key, label in DOMAIN_LABELS.items()
        ]
    }


@app.post("/api/plan", response_model=LandingPlan)
def create_plan(request: PlanRequest) -> LandingPlan:
    settings = load_settings()
    provider, source = build_provider(settings)
    narrator, _ = build_narrator(settings)
    planner = Planner(provider, source, narrator=narrator)

    if not request.anchors:
        raise HTTPException(
            status_code=422,
            detail=(
                "Podaj przynajmniej jedną kotwicę smakową — film, artystę albo potrawę "
                "z kraju pochodzenia. Bez tego nie ma z czego wyliczyć afinacji."
            ),
        )

    try:
        return planner.build_plan(request)
    except QlooError as exc:
        # Błędy Qloo są czytelne dla człowieka — oddajemy je jako 502 z komunikatem,
        # żeby UI pokazało przyczynę zamiast pustego ekranu.
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
