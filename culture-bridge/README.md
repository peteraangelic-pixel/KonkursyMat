# Smak Domu / Culture Bridge

Agentowy plan kulturowego lądowania dla osób, które właśnie zmieniły kraj.

Ktoś przyjeżdża z Lwowa do Poznania i wszystko jest obce: jedzenie, muzyka, kino,
miejsca. Generyczna odpowiedź brzmi „zobacz Stary Rynek i spróbuj pierogów”.
Ten projekt odpowiada inaczej — **wychodzi od tego, co już lubisz u siebie**,
i szuka najbliższych odpowiedników na miejscu, a do każdej propozycji dopisuje
*dlaczego*: która kotwica i z jaką siłą ją pociągnęła.

## Dlaczego to nie działa bez Qloo

To jest kluczowe wymaganie konkursu: *„If your submission would work the same
without Qloo, you're building the wrong thing.”*

Sam model językowy podpowie „spróbuj pierogów” i zmyśli lokale. Nie wie, jakie
afinacje zachodzą między Okean Elzy a polskim folkiem, ani które kino studyjne
w Poznaniu ma repertuar bliski *Amélie*. Qloo daje:

- **prawdziwe afinacje** między encjami w konkretnym mieście (`filter.location.query`),
- **wyjaśnialność** (`feature.explainability=true`) — które encje wejściowe
  i z jaką wagą 0–1 wpłynęły na rekomendację,
- **domeny krzyżowe** — muzyka → film → miejsce → podcast w jednym profilu smaku.

Bez afinacji smaku to byłaby zwykła lista przebojów z dopisanym powodem.

## Jak działa agent

```
1. resolve   nazwy („Okean Elzy”, „barszcz”) → identyfikatory encji przez /search
2. fan-out   osobne /v2/insights dla każdej domeny, z tymi samymi kotwicami
             + feature.explainability=true
3. compose   plan „pierwszych 30 dni” + powód przy każdej pozycji
4. refine    „to nie to” → filter.exclude.entities → pętla jeszcze raz
```

Krok 4 jest w UI: przycisk **to nie to** przy każdej pozycji wyklucza encję
i przelicza plan.

## Uruchomienie

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # uzupełnij QLOO_API_KEY
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Aplikacja: http://localhost:8000

### Tryb demo vs. dane Qloo

Klucz Qloo jest wydawany ręcznie i czeka się na niego kilka dni roboczych
([formularz](https://forms.gle/zz12orkLHTAneLGz6)). Żeby aplikacja dała się
zademonstrować zanim klucz przyjdzie, bez `QLOO_API_KEY` działa na
deterministycznych fixture'ach.

**Tryb demo jest zawsze widoczny** — baner na górze strony, plakietka
`TRYB DEMO` przy tytule i ostrzeżenie w odpowiedzi API. Każda pozycja ma
`source: "demo"`. Nie udajemy, że to dane Qloo.

Fixture'y przypisują powody **wyłącznie** do kotwic, które użytkownik faktycznie
podał — pozycja bez powiązania z Twoim profilem w ogóle się nie pokaże, tak jak
w prawdziwym API, gdzie wynik wynika z sygnału.

### Ważne dla klucza hackathonowego

- klucz działa **wyłącznie** z `https://hackathon.api.qloo.com`
  (`api.qloo.com` i `staging.api.qloo.com` zwrócą 401),
- klucz idzie w nagłówku **`X-Api-Key`** — nie Bearer, nie query param,
- `/v2/insights` to **GET**, parametry w query stringu,
- `/recs` i `/recommendations` to endpointy legacy — nie używamy ich,
- API **milczy** zamiast zgłosić błąd, gdy parametr nie pasuje do `filter.type`.
  Dlatego pusty wynik jest u nas traktowany jako sygnał diagnostyczny,
  a klient nie wysyła żadnych nieudokumentowanych parametrów,
- rozmiar wyniku to **`take`** (1–50, domyślnie 20), a paginacja przez `page`,
- `/search` zwraca **404 „No results”** — to normalny wynik, nie awaria.

### Kształt odpowiedzi Insights API

Parser jest napisany pod udokumentowany przykład odpowiedzi
(`docs.qloo.com/reference/basic-insights-use-case`), nie pod zgadywankę.
Cztery rzeczy, które łatwo pomylić i które mamy pokryte testami:

| Pole | Jak jest naprawdę | Pułapka |
|---|---|---|
| identyfikator | `entity_id` | nie `id` — puste ID zabija wykluczanie w UI |
| `tags` | lista obiektów `{id, name, type}` | `str(t)` wypisuje do UI repr słownika |
| `properties.image` | obiekt `{"url": ...}` | `str(image)` daje słownik jako `src` |
| `popularity` | osobna miara | **nie** podstawiamy jej pod afinację |

Testy w `tests/test_qloo_client.py` używają fixture'a przepisanego z tej
dokumentacji, więc rozjazd z API wychodzi w testach, a nie dopiero na demo.

## Testy

```bash
. .venv/bin/activate && python -m pytest tests/ -q
```

Testy przechodzą przez prawdziwy kod, nie przez jego kopię:

- `test_qloo_client.py` — budowanie parametrów i nagłówków na `httpx.MockTransport`
  (w tym mapowanie 401/403 na czytelne komunikaty), cache, parsowanie odpowiedzi,
- `test_planner.py` — cztery kroki pętli agenta, w tym regresja na przypisywanie
  kotwic, których użytkownik nie podał,
- `test_narrator.py` — warstwa narracji: domyślna ścieżka bez klucza oraz powrót
  do wersji deterministycznej przy awarii modelu (HTTP 500, puste `choices`,
  nieznany kształt odpowiedzi, błąd sieci, pusty tekst),
- `test_api.py` — pełna ścieżka HTTP: żądanie → planer → odpowiedź.

## Struktura

```
app/
  config.py       ustawienia ze środowiska
  models.py       schematy (Anchor, PlanRequest, LandingPlan, Recommendation)
  qloo_client.py  klient Insights API + mapowanie udokumentowanych błędów
  provider.py     protokół dostawcy: QlooClient | DemoProvider
  narrator.py     zdanie podsumowujące: deterministycznie lub przez model
  planner.py      pętla agenta (resolve → fan-out → compose → refine)
  main.py         FastAPI
static/           frontend bez etapu budowania
tests/
```

### Warstwa narracji

Podsumowanie planu powstaje w osobnej warstwie:

- **domyślnie deterministycznie** — bez żadnego klucza API, aplikacja działa
  na czystej maszynie,
- **opcjonalnie przez model** — gdy ustawisz `LLM_API_KEY` **i** `LLM_PROVIDER`.
  Sam klucz nie wystarczy, więc przypadkowo wklejony sekret nie zmienia
  zachowania aplikacji.

Każda awaria warstwy językowej (sieć, limit, nieznany kształt odpowiedzi,
pusty tekst) kończy się powrotem do narracji deterministycznej — jest ozdobą,
nie fundamentem. `/api/health` raportuje `llm_enabled` na podstawie tego,
który narrator faktycznie zbudowano, a nie samej obecności klucza w środowisku.

Frontend celowo nie ma etapu budowania: konkurs wymaga hostowanego, działającego
demo, a im mniej kroków do uruchomienia, tym mniej rzeczy może się zepsuć.

## Hosting

Wymóg konkursu: *„Your demo must be hosted and fully published externally”*.
Wystarczy cokolwiek, co uruchomi Uvicorna i pozwala ustawić `QLOO_API_KEY`
jako zmienną środowiskową — Render, Fly.io, Railway. Klucz nie może trafić
do kodu frontendu, bo trafiłby do przeglądarki.

### Render

Blueprint **`render.yaml` leży w korzeniu repo**, nie tutaj. Render szuka tego
pliku w katalogu głównym, a komendy `buildCommand` / `startCommand` wykonuje
względem niego — dlatego usługa ma ustawione `rootDir: culture-bridge`. Bez
tego pola build szukałby `requirements.txt` i pakietu `app` w korzeniu, gdzie
ich nie ma.

Po utworzeniu usługi ustaw w panelu `QLOO_API_KEY` — bez niej aplikacja ruszy
w trybie demo i pokaże o tym baner.

## Lista przed zgłoszeniem

- [ ] `QLOO_API_KEY` ustawiony na hostingu, baner demo znika
- [x] repo publiczne, licencja MIT widoczna w sekcji **About** *(GitHub wykrywa MIT od merge'a `78dfbea`)*
- [ ] demo dostępne pod publicznym URL, bez logowania
- [ ] sprawdzone na prawdziwych kotwicach i prawdziwym mieście
- [x] opis zgłoszenia wyjaśnia, co jest „Qloo-powered” *(zobacz [SUBMISSION.md](SUBMISSION.md))*
- [x] wideo demo **nie jest wymagane** w tym konkursie

### Wypłata nagrody z Polski (bez firmy)

Zweryfikowane w regulaminie i dokumentacji Devpost:

- Konkurs jest otwarty dla **osób fizycznych** („Individuals who are at least
  the age of majority where they reside"). Firma nie jest wymagana.
- **Polska nie jest wykluczona.** Wyłączone są m.in. Brazylia, Quebec, Rosja,
  Krym, Kuba, Iran i Korea Płn.
- Zwycięzca spoza USA odbierający nagrodę **jako osoba fizyczna** składa
  formularz **W-8BEN** (organizacje składają W-8BEN-E). Formularz podatkowy
  jest warunkiem wypłaty.

Do potwierdzenia samodzielnie, bo tego nie zweryfikowałem: dokładna stawka
potrącenia u źródła dla dochodu z nagrody (obowiązuje konwencja
polsko-amerykańska z 8.10.1974, ale konkretnej stawki dla nagród nie
sprawdziłem) oraz rozliczenie po polskiej stronie — warto z księgowym.

## Licencja

MIT — zobacz [LICENSE](LICENSE).
