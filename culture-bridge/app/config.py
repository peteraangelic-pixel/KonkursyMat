"""Konfiguracja aplikacji Culture Bridge / Smak Domu.

Wszystko, czego potrzebuje aplikacja, pochodzi ze zmiennych środowiskowych,
żeby dało się ją hostować gdziekolwiek (Render, Fly, GitLab Pages + API).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Klucz wydany na hackathon działa WYŁĄCZNIE przeciw temu hostowi.
# staging.api.qloo.com i api.qloo.com zwrócą 401 dla klucza hackathonowego.
DEFAULT_QLOO_BASE_URL = "https://hackathon.api.qloo.com"


@dataclass(frozen=True)
class Settings:
    """Ustawienia uruchomieniowe.

    `qloo_api_key` może być pusty — wtedy aplikacja działa w trybie DEMO
    na deterministycznych fixture'ach. Tryb jest zawsze widoczny w UI,
    żeby nikt nie pomylił danych demonstracyjnych z prawdziwym API.
    """

    qloo_api_key: str = ""
    qloo_base_url: str = DEFAULT_QLOO_BASE_URL
    llm_api_key: str = ""
    llm_provider: str = "none"
    request_timeout: float = 20.0
    cache_ttl_seconds: int = 3600

    @property
    def qloo_enabled(self) -> bool:
        return bool(self.qloo_api_key.strip())

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key.strip()) and self.llm_provider != "none"


def load_settings(env: dict[str, str] | None = None) -> Settings:
    """Czyta ustawienia ze środowiska. `env` pozwala wstrzyknąć dict w testach."""
    src = os.environ if env is None else env
    return Settings(
        qloo_api_key=src.get("QLOO_API_KEY", "").strip(),
        qloo_base_url=src.get("QLOO_BASE_URL", DEFAULT_QLOO_BASE_URL).strip().rstrip("/"),
        llm_api_key=src.get("LLM_API_KEY", "").strip(),
        llm_provider=src.get("LLM_PROVIDER", "none").strip().lower(),
        request_timeout=float(src.get("QLOO_TIMEOUT", "20")),
        cache_ttl_seconds=int(src.get("QLOO_CACHE_TTL", "3600")),
    )
