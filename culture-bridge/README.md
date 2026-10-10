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
  a klient nie wysyła żadnych nieudokumentowanych parametrów.

## Testy

```bash
. .venv/bin/activate && python -m pytest tests/ -q
```

Testy przechodzą przez prawdziwy kod, nie przez jego kopię:

- `test_qloo_client.py` — budowanie parametrów i nagłówków na `httpx.MockTransport`
  (w tym mapowanie 401/403 na czytelne komunikaty), cache, parsowanie odpowiedzi,
- `test_planner.py` — cztery kroki pętli agenta, w tym regresja na przypisywanie
  kotwic, których użytkownik nie podał,
- `test_api.py` — pełna ścieżka HTTP: żądanie → planer → odpowiedź.

## Struktura

```
app/
  config.py       ustawienia ze środowiska
  models.py       schematy (Anchor, PlanRequest, LandingPlan, Recommendation)
  qloo_client.py  klient Insights API + mapowanie udokumentowanych błędów
  provider.py     protokół dostawcy: QlooClient | DemoProvider
  planner.py      pętla agenta (resolve → fan-out → compose → refine)
  main.py         FastAPI
static/           frontend bez etapu budowania
tests/
```

Frontend celowo nie ma etapu budowania: konkurs wymaga hostowanego, działającego
demo, a im mniej kroków do uruchomienia, tym mniej rzeczy może się zepsuć.

## Hosting

Wymóg konkursu: *„Your demo must be hosted and fully published externally”*.
Wystarczy cokolwiek, co uruchomi Uvicorna i pozwala ustawić `QLOO_API_KEY`
jako zmienną środowiskową — Render, Fly.io, Railway. Klucz nie może trafić
do kodu frontendu, bo trafiłby do przeglądarki.

## Lista przed zgłoszeniem

- [ ] `QLOO_API_KEY` ustawiony na hostingu, baner demo znika
- [ ] repo publiczne, licencja MIT widoczna w sekcji **About**
- [ ] demo dostępne pod publicznym URL, bez logowania
- [ ] sprawdzone na prawdziwych kotwicach i prawdziwym mieście
- [ ] opis zgłoszenia wyjaśnia, co jest „Qloo-powered”
- [ ] wideo demo **nie jest wymagane** w tym konkursie

## Licencja

MIT — zobacz [LICENSE](LICENSE).
