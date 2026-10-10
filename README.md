# KonkursyMat

Repo robocze na zgłoszenia konkursowe. Licencja **MIT** — patrz [LICENSE](LICENSE).

## Zgłoszenie: Smak Domu / Culture Bridge

Katalog [`culture-bridge/`](culture-bridge/) — zgłoszenie do **Qloo Agentic
Hackathon**. To tutaj jest działająca aplikacja i jej testy.

- **README z instrukcją uruchomienia:** [`culture-bridge/README.md`](culture-bridge/README.md)
- **Konfiguracja deployu:** `render.yaml` w korzeniu repo (Render, plan darmowy)
  + `culture-bridge/Procfile`
- **Licencja:** MIT, w korzeniu i w `culture-bridge/`

Co robi aplikacja: osoba przyjeżdżająca do nowego miasta podaje kilka rzeczy,
które lubi „z domu" (muzyka, film, smak). Qloo Insights API zamienia to w plan
pierwszych tygodni — filmy, miejsca, jedzenie, muzyka — a każda pozycja mówi,
**dlaczego się pojawiła** i który gust ją pociągnął.

### Dlaczego to jest „Qloo-powered"

Aplikacja nie ma własnego katalogu, własnych tagów ani własnego silnika
rekomendacji. Cała treść — encje, tagi, afinacje, explainability — pochodzi z
Qloo. Bez Qloo nie ma czego wyświetlić; tryb demo służy wyłącznie do pracy
nad UI przed otrzymaniem klucza i jest w interfejsie oznaczony banerem.

## Pozostałe katalogi

- `ANALIZA_DEVPOST.md` — raport porównujący szanse w konkursach z Devpost
  (generator: `konkursy/analiza_devpost.py`).
