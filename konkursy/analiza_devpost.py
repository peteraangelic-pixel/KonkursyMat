#!/usr/bin/env python3
"""
Analiza konkursów Devpost (stan na 2026-10-10).

Dane wejściowe (CANDIDATES) są przepisane wprost ze stron konkursów na Devpost:
kwota nagród, liczba zarejestrowanych uczestników, liczba slotów nagród,
termin, wymagania i status dostępności. Skrypt przelicza wskaźniki i generuje
`ANALIZA_DEVPOST.md` — dzięki temu liczby w raporcie są wyliczone, nie wpisane ręcznie.

Uruchomienie:  python3 konkursy/analiza_devpost.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

TODAY = date(2026, 10, 10)

# Jedyny twardy punkt odniesienia, jaki mamy na temat tego, jaka część
# zarejestrowanych realnie oddaje projekt: Meta podała o poprzedniej edycji,
# że „over 2,900 developers joined the competition and delivered more than 650
# submissions”. To ZAŁOŻENIE MODELU, nie pomiar dla każdego konkursu.
META_LAST_YEAR_JOINED = 2900
META_LAST_YEAR_SUBMISSIONS = 650
SUBMIT_RATE = META_LAST_YEAR_SUBMISSIONS / META_LAST_YEAR_JOINED


@dataclass
class Candidate:
    name: str
    url: str
    deadline: date
    prize_usd: float
    participants: int
    prize_slots: int
    status: str  # mocny / możliwy / słaby / wykluczony
    needs_video: bool
    blockers: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def days_left(self) -> int:
        return (self.deadline - TODAY).days

    @property
    def usd_per_participant(self) -> float:
        return self.prize_usd / self.participants

    @property
    def est_submissions(self) -> float:
        return self.participants * SUBMIT_RATE

    @property
    def est_odds_pct(self) -> float:
        """Szansa na dowolną nagrodę = sloty / szacowana liczba zgłoszeń."""
        if self.est_submissions <= 0:
            return 0.0
        return min(100.0, 100.0 * self.prize_slots / self.est_submissions)


CANDIDATES = [
    Candidate(
        name="Life After Code (GitLab Transcend Hackathon)",
        url="https://gitlab-transcend.devpost.com/",
        deadline=date(2026, 10, 27),
        prize_usd=45_000,
        participants=1539,
        prize_slots=10,
        status="mocny",
        needs_video=True,
        blockers=[
            "konto GitLab + rejestracja jako GitLab Contributor (aprobata ~24 h)",
            "GitLab Duo Agent Platform (agenci / flows / MCP) — warunek konieczny zgłoszenia",
            "publiczne repo GitLab z licencją MIT + widoczna historia pipeline CI/CD",
            "wideo demo < 3 min na YouTube (musi je nagrać człowiek)",
        ],
        notes=(
            "10 slotów nagród przy 1539 uczestnikach — najlepszy stosunek puli do pola, "
            "jaki znalazłem wśród konkursów realnie dla nas dostępnych. Nagrody są "
            "rozdrobnione na ścieżki (A: Start Fresh / B: Bring Your Own) i poziomy "
            "autonomii (assisted / supervised / hands-off), a do tego dochodzą osobne "
            "pule: „Most Stages Covered” (2 × $5 000), „Most Environmentally Impactful” "
            "($5 000) i „Most Creative” ($4 000). Tematyka — automatyzacja cyklu DevSecOps "
            "agentami — to dokładnie to, co agent kodujący robi najlepiej: pipeline'y, "
            "przeglądy MR, skany bezpieczeństwa, deployment. Bonus +0,2 pkt za deploy na "
            "Google Cloud. Kryteria oceny: Technological Implementation, Design, Potential "
            "Impact, Innovation/Idea, Presentation."
        ),
    ),
    Candidate(
        name="Qloo Agentic Hackathon",
        url="https://qloo.devpost.com/",
        deadline=date(2026, 10, 30),
        prize_usd=25_000,
        participants=962,
        prize_slots=3,
        status="mocny",
        needs_video=False,
        blockers=[
            "klucz API Qloo (wydawany przez formularz Google)",
            "aplikacja MUSI być hostowana i w pełni opublikowana (nie wystarczy lokalnie)",
            "publiczne repo z licencją open source widoczną w sekcji About",
        ],
        notes=(
            "JEDYNY z przejrzanych konkursów, który wprost NIE wymaga filmu demo "
            "(„Demo videos are not required. Instead of asking for a recording, we're "
            "requiring something judges can actually use”) — a film to jedyny element "
            "zgłoszenia, którego nie potrafię wytworzyć. Za to wymaga działającego, "
            "dostępnego online demo, które jurorzy klikają sami. Dodatkowa stawka: Jason "
            "Calacanis osobiście doinwestuje $25 000 w swój ulubiony projekt. Minus: tylko "
            "3 nagrody ($15k / $6k / $4k), brak nagród kategorii, a w jury inwestorzy i "
            "celebryci — więc liczy się efekt „wow” i dopracowany produkt, nie sama "
            "technologia. Kryteria: Technological Implementation, Design, Potential Impact, "
            "Quality of Idea."
        ),
    ),
    Candidate(
        name="PayPal AI Hackathon",
        url="https://paypalaihackathon.devpost.com/",
        deadline=date(2026, 11, 12),
        prize_usd=67_500,
        participants=11_023,
        prize_slots=23,
        status="możliwy",
        needs_video=True,
        blockers=[
            "konto PayPal Developer (środowisko sandbox jest darmowe)",
            "wideo demo < 3 min na YouTube",
            "publiczne repo open source z licencją widoczną w sekcji About",
            "hostowane demo ALBO kompletne instrukcje uruchomienia dla jurorów",
        ],
        notes=(
            "Najdłuższy zapas czasu (33 dni) i najwięcej slotów nagród (23). Kluczowa "
            "obserwacja: nagrody sponsorów — AG Grid ($5k/$2k/$1k×3), APIMatic ($1k×3), "
            "Bryntum ($1k×3), Channel3 ($1,5k), Render (kredyty) — są praktycznie "
            "nieobsadzone, bo żeby o nie walczyć, trzeba świadomie wbudować ich narzędzie, "
            "a większość uczestników tego nie zrobi. Wymóg merytoryczny jest jeden i "
            "bardzo szeroki: „your project must meaningfully use both PayPal and AI”. Brak "
            "narzuconych tracków i problemów; dozwolone są też projekty istniejące, jeśli "
            "w oknie konkursu zrobi się w nich istotny postęp."
        ),
    ),
    Candidate(
        name="Build With AI: Basics (Devpost)",
        url="https://learn-ai-basics.devpost.com/",
        deadline=date(2026, 10, 26),
        prize_usd=2_500,
        participants=2_981,
        prize_slots=3,
        status="możliwy",
        needs_video=True,
        blockers=[
            "projekt MUSI powstać od zera, w pustym folderze, w trakcie trwania konkursu",
            "trzeba użyć Devpost Learn Skill Pack (npx skills add challengepost/learn-ai-basics)",
            "repo musi zawierać scope.md, prd.md i spec.md wygenerowane przez te skille",
            "wideo demo 1–3 min („Reviewers won't clone or run code, so the video has to show it working”)",
        ],
        notes=(
            "Mała pula ($2 500: $1 250 / $750 / $500), ale najniższy próg wejścia i kryteria "
            "(Design, Innovation/Idea, Presentation) ustawione dokładnie pod to, co agent "
            "robi dobrze: plan przed kodem, spójny produkt, czytelna prezentacja. Jury to "
            "trzy osoby z Devpostu, nie zewnętrzni eksperci. Konkurs otwiera się co miesiąc, "
            "więc można go traktować jako powtarzalny poligon. Każdy poprawny uczestnik "
            "dostaje odznakę Devpost Learn."
        ),
    ),
    Candidate(
        name="Nebius x NVIDIA Global AI Hackathon",
        url="https://nebiusglobalaihackathon.devpost.com/",
        deadline=date(2026, 10, 30),
        prize_usd=50_000,
        participants=20_733,
        prize_slots=38,
        status="słaby",
        needs_video=True,
        blockers=[
            "konto Nebius (Token Factory / AI Cloud) — całość musi tam działać",
            "co najmniej jeden open-source'owy model NVIDIA (Nemotron itp.)",
            "działające demo + repo open source + pisemny feedback o narzędziach Nebius",
            "wideo demo ≤ 3 min na YouTube",
        ],
        notes=(
            "Najwięcej slotów (38), ale to złudne: 20 z nich to „City Winner Awards” "
            "($500) przyznawane za udział w stacjonarnych eventach Builders & Brews, a 10 "
            "to „Most Valuable Feedback” ($100). Realna walka toczy się o pozostałe 8 "
            "(w tym 4 tracki nagradzane Jetsonem Orin Nano, nie gotówką). 20 733 "
            "uczestników i $2,41 na głowę — bardzo gęsto."
        ),
    ),
    Candidate(
        name="OpenCV AI Competition 2026 (powered by AWS)",
        url="https://opencv26.devpost.com/",
        deadline=date(2026, 10, 27),
        prize_usd=20_250,
        participants=4_585,
        prize_slots=0,  # pełnej listy nagród nie przejrzałem
        status="słaby",
        needs_video=True,
        blockers=[
            "każde zgłoszenie musi używać OpenCV 5 do istotnej analizy obrazu/wideo",
            "znaczący komponent musi działać na AWS",
            "raport techniczny + diagram architektury + przypięte zależności",
            "wideo ≤ 5 min pokazujące ZESPÓŁ, działającą aplikację i wyniki",
            "faza grantów na compute (propozycje od 13 sierpnia) już minęła",
        ],
        notes=(
            "Dwumiesięczny konkurs o wyraźnie inżynieryjnym profilu (Physical AI, SLAM, "
            "digital twins, COOL na Gravitonie). Wideo musi pokazać zespół, więc bez "
            "udziału człowieka przed kamerą się nie domknie. Są dwie dodatkowe ścieżki po "
            "$1 000 (Best Use of COOL, Agentic Vision Award); pełnej listy nagród nie "
            "przejrzałem, stąd brak liczby slotów."
        ),
    ),
    Candidate(
        name="Build, Ship, Shape: Amazon Developer Hackathon",
        url="https://amazonappdev2026.devpost.com/",
        deadline=date(2026, 10, 23),
        prize_usd=138_000,
        participants=52_973,
        prize_slots=0,  # szczegółów nie przejrzałem
        status="słaby",
        needs_video=True,
        blockers=["52 973 uczestników — największe pole ze wszystkich przejrzanych"],
        notes=(
            "Największa pula gotówkowa ($138 000), ale też najgorszy stosunek nagród do "
            "uczestnika: $2,61 na głowę. Regulaminu i listy nagród nie przejrzałem — "
            "wniosek opiera się wyłącznie na liczbach z listingu."
        ),
    ),
    Candidate(
        name="Meta VR Start Developer Competition 2026",
        url="https://start-developer-competition-26.devpost.com/",
        deadline=date(2026, 11, 18),
        prize_usd=1_000_000,
        participants=2_831,
        prize_slots=0,  # pełnej listy nagród nie przejrzałem
        status="wykluczony",
        needs_video=True,
        blockers=[
            "trzeba być członkiem programu Meta Start (osobna aplikacja)",
            "aplikacja na urządzenia Meta VR (Quest / Meta VR Glasses)",
            "interakcje „hands-first” — w praktyce wymaga fizycznego headsetu",
        ],
        notes=(
            "Największa pula ($1 000 000, najwyższe nagrody po $100 000) i stosunkowo mało "
            "uczestników (2 831, czyli $353 na głowę — najlepszy wskaźnik w całym zestawie). "
            "Ale bez sprzętu VR nie da się tego ani zbudować, ani zademonstrować, a "
            "członkostwo w programie Start wymaga osobnej aplikacji. Gdybyś miał Quest — "
            "to zmienia postać rzeczy."
        ),
    ),
    Candidate(
        name="AWS CDS Agentic AI Partner Hackathon",
        url="https://aws-cds-partner.devpost.com/",
        deadline=date(2026, 10, 28),
        prize_usd=40_000,
        participants=841,
        prize_slots=0,  # pełnej listy nagród nie przejrzałem
        status="wykluczony",
        needs_video=True,
        blockers=[
            "dostęp ograniczony: „Professionals/Post grads only”",
            "konkurs dla partnerów AWS — wymagane opportunity ID w AWS Partner Central (ACE)",
            "kod musi w runtime używać AWS Communication Developer Services",
        ],
        notes=(
            "Małe pole (841 osób) i duża pula ($40 000, czyli $47,56 na głowę), ale bariera "
            "formalna — status partnera AWS i obowiązkowy wpis w ACE — wyklucza osobę "
            "fizyczną niebędącą partnerem. Pomijam, chyba że masz firmę partnerską AWS."
        ),
    ),
    Candidate(
        name="EurekaDev 2026",
        url="https://eurekadev.devpost.com/",
        deadline=date(2026, 10, 20),
        prize_usd=19_122,
        participants=381,
        prize_slots=0,  # przejrzałem głównie track Coding
        status="wykluczony",
        needs_video=True,
        blockers=[
            "wiek 13–19 lat, wyłącznie uczniowie szkół średnich",
            "firmy i organizacje zawodowe wykluczone z udziału",
            "obowiązkowy Discord + 4-minutowe wideo projektu",
            "„AI use for writing code/research document is discouraged, but allowed”",
        ],
        notes=(
            "Najniższa konkurencja ze wszystkich przejrzanych (381 osób, $50,19 na głowę) i "
            "osobna kategoria „Math & Physics”, która pasowałaby do profilu tego repo. "
            "Statystycznie byłby to najlepszy strzał — ale limit wieku to twarda bariera. "
            "Warto też zauważyć, że organizatorzy wprost odradzają użycie AI do pisania "
            "kodu, a jakość jest kryterium oceny."
        ),
    ),
]


def _sp(value: float) -> str:
    """Liczba z polskim separatorem tysięcy (spacja) zamiast przecinka."""
    return f"{value:,.0f}".replace(",", " ")


def fmt_money(value: float) -> str:
    return f"{_sp(value)} $"


def fmt_pct(value: float) -> str:
    return f"{value:.1f}".replace(".", ",") + "%"


def render() -> str:
    ranked = sorted(CANDIDATES, key=lambda c: -c.usd_per_participant)
    live = [c for c in ranked if c.status in ("mocny", "możliwy")]

    lines: list[str] = []
    add = lines.append

    add("# Devpost — w którym konkursie mamy realne szanse coś wygrać")
    add("")
    add(f"_Stan danych: {TODAY.isoformat()}. Źródło: strony konkursów na devpost.com._")
    add("")
    add("## Założenie modelu")
    add("")
    add(
        "Devpost pokazuje liczbę **zarejestrowanych uczestników**, a nie liczbę zgłoszeń. "
        "Zgłoszeń jest zawsze wielokrotnie mniej. Jedyny twardy punkt odniesienia, jaki "
        "mam, podała Meta o poprzedniej edycji swojego konkursu: "
        f"{META_LAST_YEAR_JOINED} zarejestrowanych → ponad {META_LAST_YEAR_SUBMISSIONS} "
        f"zgłoszeń, czyli ~{SUBMIT_RATE:.0%} skuteczności. Ta wartość jest ZAŁOŻENIEM "
        "przeniesionym na wszystkie konkursy poniżej, nie pomiarem dla każdego z nich."
    )
    add("")
    add("## Ranking (wg puli nagród na uczestnika)")
    add("")
    add("| Konkurs | Termin | Zostało | Pula | Uczestnicy | Pula/uczestnika | Sloty | Szac. pole | Szansa* |")
    add("|---|---|---|---|---|---|---|---|---|")
    for c in ranked:
        slots = str(c.prize_slots) if c.prize_slots else "b.d."
        odds = fmt_pct(c.est_odds_pct) if c.prize_slots else "b.d."
        add(
            f"| [{c.name}]({c.url}) | {c.deadline.isoformat()} | {c.days_left} dni "
            f"| {fmt_money(c.prize_usd)} | {_sp(c.participants)} "
            f"| {fmt_money(c.usd_per_participant)} | {slots} | ~{_sp(c.est_submissions)} | {odds} |"
        )
    add("")
    add(
        "*Szansa = sloty nagród / szacowana liczba zgłoszeń. To rząd wielkości, nie prognoza. "
        "„b.d.” = nie przejrzałem pełnej listy nagród."
    )
    add("")

    add("## Rekomendacja")
    add("")
    top = live[0]
    add(
        f"**{top.name}** — najlepszy stosunek puli do pola ({fmt_money(top.usd_per_participant)} "
        f"na uczestnika) i najwięcej slotów nagród ({top.prize_slots}) spośród konkursów, "
        "które realnie możemy obsłużyć."
    )
    add("")
    add(
        "Drugi strzał, równoległy i tani: **Qloo Agentic Hackathon** — jedyny, który nie wymaga "
        "filmu demo, więc całą pracę deweloperską mogę wykonać ja."
    )
    add("")
    add(
        "Trzeci, z najdłuższym zapasem czasu: **PayPal AI Hackathon** (33 dni, 23 sloty nagród, "
        "w tym praktycznie nieobsadzone nagrody sponsorów)."
    )
    add("")
    add(
        "Trzy powyższe da się prowadzić jednocześnie — wymagania techniczne się nie kłócą, "
        "a jedynym wąskim gardłem jest liczba filmów demo do nagrania."
    )
    add("")

    add("## Podział pracy: co mogę ja, co musisz Ty")
    add("")
    add("| Etap | Ja | Ty |")
    add("|---|---|---|")
    add("| Przegląd regulaminów, wybór konkursu, strategia nagród | ✅ | — |")
    add("| Architektura i cały kod projektu | ✅ | akceptacja kierunku |")
    add("| Dokumentacja, README, opis zgłoszenia na Devpost | ✅ | wklejenie treści |")
    add("| Konto Devpost / GitLab / Qloo / PayPal, akceptacja regulaminów | ❌ | ✅ obowiązkowo |")
    add("| Klucze API i deployment na publiczny hosting | ❌ (brak kont) | ✅ obowiązkowo |")
    add("| Nagranie i wrzucenie wideo demo na YouTube | ❌ | ✅ tam, gdzie wideo jest wymagane |")
    add("| Dane podatkowe i odbiór nagrody | ❌ | ✅ |")
    add("")

    add("## Co blokuje każdy z wariantów")
    add("")
    for c in live:
        add(f"### {c.name}")
        add("")
        add(f"- Termin: **{c.deadline.isoformat()}** ({c.days_left} dni)")
        add(f"- Wideo demo wymagane: **{'TAK' if c.needs_video else 'NIE'}**")
        for b in c.blockers:
            add(f"- {b}")
        add("")

    add("## Wykluczone i dlaczego")
    add("")
    for c in ranked:
        if c.status == "wykluczony":
            add(f"- **{c.name}** — {c.blockers[0]}")
    add("")

    add("## Uczciwe zastrzeżenia")
    add("")
    add(
        "- **Nie mogę nagrać filmu demo.** Każdy konkurs oznaczony „wideo: TAK” wymaga Twojego "
        "udziału przy nagraniu. To jedyne twarde ograniczenie, które dzieli nas od domknięcia "
        "zgłoszenia."
    )
    add(
        "- **Nie mam żadnych kont** (Devpost, GitLab, Qloo, PayPal, Nebius, AWS) i nie mogę ich "
        "założyć. Rejestracja, akceptacja regulaminów i odbiór nagrody są po Twojej stronie."
    )
    add(
        "- **Szacowane prawdopodobieństwa są dolną granicą, nie prognozą.** Nie uwzględniają tego, "
        "że większość zgłoszeń w takich konkursach jest słaba i że dopracowany projekt startuje "
        "z lepszej pozycji niż średnia. Nie podaję liczby skorygowanej o jakość, bo nie mam "
        "danych, na których mógłbym ją oprzeć."
    )
    add(
        "- **Własność i oryginalność.** Regulaminy (np. Qloo) wymagają, by projekt był oryginalną "
        "pracą zgłaszającego i jego wyłączną własnością. Zgłoszenie składa człowiek; AI jest "
        "narzędziem — w konkursach AI-first (GitLab, Build With AI) wprost oczekiwanym — ale "
        "regulamin konkretnego konkursu warto przeczytać przed startem."
    )
    add(
        "- **Dane się ruszają.** Liczba uczestników rosła w trakcie przeglądania (Amazon: "
        "52 972 → 52 973 między dwoma pobraniami tej samej strony), więc traktuj ją jako stan "
        "z dzisiejszego dnia."
    )
    add(
        "- **Nie przejrzałem wszystkiego.** Dla Amazona, OpenCV, Meta VR i AWS CDS nie znam pełnej "
        "listy nagród — w tabeli mają „b.d.”. Wnioski o nich opierają się na liczbach z listingu."
    )
    add("")

    add("## Szczegóły")
    add("")
    for c in ranked:
        add(f"### {c.name}")
        add("")
        add(f"- Status: **{c.status}**")
        add(f"- {c.notes}")
        add("")

    return "\n".join(lines)


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "ANALIZA_DEVPOST.md"
    out.write_text(render(), encoding="utf-8")

    print(f"SUBMIT_RATE (założenie z danych Mety): {SUBMIT_RATE:.4f}")
    print(f"Zapisano: {out}")
    print()
    print(f"{'konkurs':52s} {'$/ucz':>8s} {'sloty':>6s} {'szac. pole':>11s} {'szansa':>8s}")
    for c in sorted(CANDIDATES, key=lambda c: -c.usd_per_participant):
        slots = str(c.prize_slots) if c.prize_slots else "b.d."
        odds = f"{c.est_odds_pct:.1f}%" if c.prize_slots else "b.d."
        print(
            f"{c.name[:52]:52s} {c.usd_per_participant:8.2f} {slots:>6s} "
            f"{c.est_submissions:11.0f} {odds:>8s}"
        )

    # kontrola sum nagród przepisanych z regulaminów
    checks = {
        "Life After Code (GitLab Transcend Hackathon)": 45_000,
        "Qloo Agentic Hackathon": 25_000,
        "PayPal AI Hackathon": 67_500,
        "Build With AI: Basics (Devpost)": 2_500,
        "Nebius x NVIDIA Global AI Hackathon": 50_000,
    }
    by_name = {c.name: c for c in CANDIDATES}
    for name, expected in checks.items():
        got = by_name[name].prize_usd
        assert got == expected, f"{name}: oczekiwano {expected}, jest {got}"

    # GitLab: 6 nagród ścieżkowych + 2× Most Stages + Env + Creative = 10 slotów
    gitlab_cash = 4000 + 4000 + 5000 + 4000 + 4000 + 5000 + 5000 * 2 + 5000 + 4000
    assert gitlab_cash == 45_000, f"GitLab: suma nagród {gitlab_cash} != 45 000"
    assert by_name["Life After Code (GitLab Transcend Hackathon)"].prize_slots == 10

    # PayPal: 8 głównych + AG Grid 5 + APIMatic 3 + Bryntum 3 + Channel3 1 + Render 3
    paypal_slots = sum([1] * 8 + [1, 1, 3] + [3] + [3] + [1] + [1, 1, 1])
    assert paypal_slots == by_name["PayPal AI Hackathon"].prize_slots == 23, "PayPal: sloty"

    # Qloo: 1. / 2. / 3. miejsce
    assert by_name["Qloo Agentic Hackathon"].prize_slots == 3

    print()
    print("Kontrola sum nagród i liczby slotów: OK")


if __name__ == "__main__":
    main()
