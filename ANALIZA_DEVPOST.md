# Devpost — w którym konkursie mamy realne szanse coś wygrać

_Stan danych: 2026-10-10. Źródło: strony konkursów na devpost.com._

## Założenie modelu

Devpost pokazuje liczbę **zarejestrowanych uczestników**, a nie liczbę zgłoszeń. Zgłoszeń jest zawsze wielokrotnie mniej. Jedyny twardy punkt odniesienia, jaki mam, podała Meta o poprzedniej edycji swojego konkursu: 2900 zarejestrowanych → ponad 650 zgłoszeń, czyli ~22% skuteczności. Ta wartość jest ZAŁOŻENIEM przeniesionym na wszystkie konkursy poniżej, nie pomiarem dla każdego z nich.

## Ranking (wg puli nagród na uczestnika)

| Konkurs | Termin | Zostało | Pula | Uczestnicy | Pula/uczestnika | Sloty | Szac. pole | Szansa* |
|---|---|---|---|---|---|---|---|---|
| [Meta VR Start Developer Competition 2026](https://start-developer-competition-26.devpost.com/) | 2026-11-18 | 39 dni | 1 000 000 $ | 2 831 | 353 $ | b.d. | ~635 | b.d. |
| [EurekaDev 2026](https://eurekadev.devpost.com/) | 2026-10-20 | 10 dni | 19 122 $ | 381 | 50 $ | b.d. | ~85 | b.d. |
| [AWS CDS Agentic AI Partner Hackathon](https://aws-cds-partner.devpost.com/) | 2026-10-28 | 18 dni | 40 000 $ | 841 | 48 $ | b.d. | ~188 | b.d. |
| [Life After Code (GitLab Transcend Hackathon)](https://gitlab-transcend.devpost.com/) | 2026-10-27 | 17 dni | 45 000 $ | 1 539 | 29 $ | 10 | ~345 | 2,9% |
| [Qloo Agentic Hackathon](https://qloo.devpost.com/) | 2026-10-30 | 20 dni | 25 000 $ | 962 | 26 $ | 3 | ~216 | 1,4% |
| [PayPal AI Hackathon](https://paypalaihackathon.devpost.com/) | 2026-11-12 | 33 dni | 67 500 $ | 11 023 | 6 $ | 23 | ~2 471 | 0,9% |
| [OpenCV AI Competition 2026 (powered by AWS)](https://opencv26.devpost.com/) | 2026-10-27 | 17 dni | 20 250 $ | 4 585 | 4 $ | b.d. | ~1 028 | b.d. |
| [Build, Ship, Shape: Amazon Developer Hackathon](https://amazonappdev2026.devpost.com/) | 2026-10-23 | 13 dni | 138 000 $ | 52 973 | 3 $ | b.d. | ~11 873 | b.d. |
| [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/) | 2026-10-30 | 20 dni | 50 000 $ | 20 733 | 2 $ | 38 | ~4 647 | 0,8% |
| [Build With AI: Basics (Devpost)](https://learn-ai-basics.devpost.com/) | 2026-10-26 | 16 dni | 2 500 $ | 2 981 | 1 $ | 3 | ~668 | 0,4% |

*Szansa = sloty nagród / szacowana liczba zgłoszeń. To rząd wielkości, nie prognoza. „b.d.” = nie przejrzałem pełnej listy nagród.

## Rekomendacja

**Life After Code (GitLab Transcend Hackathon)** — najlepszy stosunek puli do pola (29 $ na uczestnika) i najwięcej slotów nagród (10) spośród konkursów, które realnie możemy obsłużyć.

Drugi strzał, równoległy i tani: **Qloo Agentic Hackathon** — jedyny, który nie wymaga filmu demo, więc całą pracę deweloperską mogę wykonać ja.

Trzeci, z najdłuższym zapasem czasu: **PayPal AI Hackathon** (33 dni, 23 sloty nagród, w tym praktycznie nieobsadzone nagrody sponsorów).

Trzy powyższe da się prowadzić jednocześnie — wymagania techniczne się nie kłócą, a jedynym wąskim gardłem jest liczba filmów demo do nagrania.

## Podział pracy: co mogę ja, co musisz Ty

| Etap | Ja | Ty |
|---|---|---|
| Przegląd regulaminów, wybór konkursu, strategia nagród | ✅ | — |
| Architektura i cały kod projektu | ✅ | akceptacja kierunku |
| Dokumentacja, README, opis zgłoszenia na Devpost | ✅ | wklejenie treści |
| Konto Devpost / GitLab / Qloo / PayPal, akceptacja regulaminów | ❌ | ✅ obowiązkowo |
| Klucze API i deployment na publiczny hosting | ❌ (brak kont) | ✅ obowiązkowo |
| Nagranie i wrzucenie wideo demo na YouTube | ❌ | ✅ tam, gdzie wideo jest wymagane |
| Dane podatkowe i odbiór nagrody | ❌ | ✅ |

## Co blokuje każdy z wariantów

### Life After Code (GitLab Transcend Hackathon)

- Termin: **2026-10-27** (17 dni)
- Wideo demo wymagane: **TAK**
- konto GitLab + rejestracja jako GitLab Contributor (aprobata ~24 h)
- GitLab Duo Agent Platform (agenci / flows / MCP) — warunek konieczny zgłoszenia
- publiczne repo GitLab z licencją MIT + widoczna historia pipeline CI/CD
- wideo demo < 3 min na YouTube (musi je nagrać człowiek)

### Qloo Agentic Hackathon

- Termin: **2026-10-30** (20 dni)
- Wideo demo wymagane: **NIE**
- klucz API Qloo (wydawany przez formularz Google)
- aplikacja MUSI być hostowana i w pełni opublikowana (nie wystarczy lokalnie)
- publiczne repo z licencją open source widoczną w sekcji About

### PayPal AI Hackathon

- Termin: **2026-11-12** (33 dni)
- Wideo demo wymagane: **TAK**
- konto PayPal Developer (środowisko sandbox jest darmowe)
- wideo demo < 3 min na YouTube
- publiczne repo open source z licencją widoczną w sekcji About
- hostowane demo ALBO kompletne instrukcje uruchomienia dla jurorów

### Build With AI: Basics (Devpost)

- Termin: **2026-10-26** (16 dni)
- Wideo demo wymagane: **TAK**
- projekt MUSI powstać od zera, w pustym folderze, w trakcie trwania konkursu
- trzeba użyć Devpost Learn Skill Pack (npx skills add challengepost/learn-ai-basics)
- repo musi zawierać scope.md, prd.md i spec.md wygenerowane przez te skille
- wideo demo 1–3 min („Reviewers won't clone or run code, so the video has to show it working”)

## Wykluczone i dlaczego

- **Meta VR Start Developer Competition 2026** — trzeba być członkiem programu Meta Start (osobna aplikacja)
- **EurekaDev 2026** — wiek 13–19 lat, wyłącznie uczniowie szkół średnich
- **AWS CDS Agentic AI Partner Hackathon** — dostęp ograniczony: „Professionals/Post grads only”

## Uczciwe zastrzeżenia

- **Nie mogę nagrać filmu demo.** Każdy konkurs oznaczony „wideo: TAK” wymaga Twojego udziału przy nagraniu. To jedyne twarde ograniczenie, które dzieli nas od domknięcia zgłoszenia.
- **Nie mam żadnych kont** (Devpost, GitLab, Qloo, PayPal, Nebius, AWS) i nie mogę ich założyć. Rejestracja, akceptacja regulaminów i odbiór nagrody są po Twojej stronie.
- **Szacowane prawdopodobieństwa są dolną granicą, nie prognozą.** Nie uwzględniają tego, że większość zgłoszeń w takich konkursach jest słaba i że dopracowany projekt startuje z lepszej pozycji niż średnia. Nie podaję liczby skorygowanej o jakość, bo nie mam danych, na których mógłbym ją oprzeć.
- **Własność i oryginalność.** Regulaminy (np. Qloo) wymagają, by projekt był oryginalną pracą zgłaszającego i jego wyłączną własnością. Zgłoszenie składa człowiek; AI jest narzędziem — w konkursach AI-first (GitLab, Build With AI) wprost oczekiwanym — ale regulamin konkretnego konkursu warto przeczytać przed startem.
- **Dane się ruszają.** Liczba uczestników rosła w trakcie przeglądania (Amazon: 52 972 → 52 973 między dwoma pobraniami tej samej strony), więc traktuj ją jako stan z dzisiejszego dnia.
- **Nie przejrzałem wszystkiego.** Dla Amazona, OpenCV, Meta VR i AWS CDS nie znam pełnej listy nagród — w tabeli mają „b.d.”. Wnioski o nich opierają się na liczbach z listingu.

## Szczegóły

### Meta VR Start Developer Competition 2026

- Status: **wykluczony**
- Największa pula ($1 000 000, najwyższe nagrody po $100 000) i stosunkowo mało uczestników (2 831, czyli $353 na głowę — najlepszy wskaźnik w całym zestawie). Ale bez sprzętu VR nie da się tego ani zbudować, ani zademonstrować, a członkostwo w programie Start wymaga osobnej aplikacji. Gdybyś miał Quest — to zmienia postać rzeczy.

### EurekaDev 2026

- Status: **wykluczony**
- Najniższa konkurencja ze wszystkich przejrzanych (381 osób, $50,19 na głowę) i osobna kategoria „Math & Physics”, która pasowałaby do profilu tego repo. Statystycznie byłby to najlepszy strzał — ale limit wieku to twarda bariera. Warto też zauważyć, że organizatorzy wprost odradzają użycie AI do pisania kodu, a jakość jest kryterium oceny.

### AWS CDS Agentic AI Partner Hackathon

- Status: **wykluczony**
- Małe pole (841 osób) i duża pula ($40 000, czyli $47,56 na głowę), ale bariera formalna — status partnera AWS i obowiązkowy wpis w ACE — wyklucza osobę fizyczną niebędącą partnerem. Pomijam, chyba że masz firmę partnerską AWS.

### Life After Code (GitLab Transcend Hackathon)

- Status: **mocny**
- 10 slotów nagród przy 1539 uczestnikach — najlepszy stosunek puli do pola, jaki znalazłem wśród konkursów realnie dla nas dostępnych. Nagrody są rozdrobnione na ścieżki (A: Start Fresh / B: Bring Your Own) i poziomy autonomii (assisted / supervised / hands-off), a do tego dochodzą osobne pule: „Most Stages Covered” (2 × $5 000), „Most Environmentally Impactful” ($5 000) i „Most Creative” ($4 000). Tematyka — automatyzacja cyklu DevSecOps agentami — to dokładnie to, co agent kodujący robi najlepiej: pipeline'y, przeglądy MR, skany bezpieczeństwa, deployment. Bonus +0,2 pkt za deploy na Google Cloud. Kryteria oceny: Technological Implementation, Design, Potential Impact, Innovation/Idea, Presentation.

### Qloo Agentic Hackathon

- Status: **mocny**
- JEDYNY z przejrzanych konkursów, który wprost NIE wymaga filmu demo („Demo videos are not required. Instead of asking for a recording, we're requiring something judges can actually use”) — a film to jedyny element zgłoszenia, którego nie potrafię wytworzyć. Za to wymaga działającego, dostępnego online demo, które jurorzy klikają sami. Dodatkowa stawka: Jason Calacanis osobiście doinwestuje $25 000 w swój ulubiony projekt. Minus: tylko 3 nagrody ($15k / $6k / $4k), brak nagród kategorii, a w jury inwestorzy i celebryci — więc liczy się efekt „wow” i dopracowany produkt, nie sama technologia. Kryteria: Technological Implementation, Design, Potential Impact, Quality of Idea.

### PayPal AI Hackathon

- Status: **możliwy**
- Najdłuższy zapas czasu (33 dni) i najwięcej slotów nagród (23). Kluczowa obserwacja: nagrody sponsorów — AG Grid ($5k/$2k/$1k×3), APIMatic ($1k×3), Bryntum ($1k×3), Channel3 ($1,5k), Render (kredyty) — są praktycznie nieobsadzone, bo żeby o nie walczyć, trzeba świadomie wbudować ich narzędzie, a większość uczestników tego nie zrobi. Wymóg merytoryczny jest jeden i bardzo szeroki: „your project must meaningfully use both PayPal and AI”. Brak narzuconych tracków i problemów; dozwolone są też projekty istniejące, jeśli w oknie konkursu zrobi się w nich istotny postęp.

### OpenCV AI Competition 2026 (powered by AWS)

- Status: **słaby**
- Dwumiesięczny konkurs o wyraźnie inżynieryjnym profilu (Physical AI, SLAM, digital twins, COOL na Gravitonie). Wideo musi pokazać zespół, więc bez udziału człowieka przed kamerą się nie domknie. Są dwie dodatkowe ścieżki po $1 000 (Best Use of COOL, Agentic Vision Award); pełnej listy nagród nie przejrzałem, stąd brak liczby slotów.

### Build, Ship, Shape: Amazon Developer Hackathon

- Status: **słaby**
- Największa pula gotówkowa ($138 000), ale też najgorszy stosunek nagród do uczestnika: $2,61 na głowę. Regulaminu i listy nagród nie przejrzałem — wniosek opiera się wyłącznie na liczbach z listingu.

### Nebius x NVIDIA Global AI Hackathon

- Status: **słaby**
- Najwięcej slotów (38), ale to złudne: 20 z nich to „City Winner Awards” ($500) przyznawane za udział w stacjonarnych eventach Builders & Brews, a 10 to „Most Valuable Feedback” ($100). Realna walka toczy się o pozostałe 8 (w tym 4 tracki nagradzane Jetsonem Orin Nano, nie gotówką). 20 733 uczestników i $2,41 na głowę — bardzo gęsto.

### Build With AI: Basics (Devpost)

- Status: **możliwy**
- Mała pula ($2 500: $1 250 / $750 / $500), ale najniższy próg wejścia i kryteria (Design, Innovation/Idea, Presentation) ustawione dokładnie pod to, co agent robi dobrze: plan przed kodem, spójny produkt, czytelna prezentacja. Jury to trzy osoby z Devpostu, nie zewnętrzni eksperci. Konkurs otwiera się co miesiąc, więc można go traktować jako powtarzalny poligon. Każdy poprawny uczestnik dostaje odznakę Devpost Learn.
