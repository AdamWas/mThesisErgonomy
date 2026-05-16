# Założenia badania

## Cel

Celem badania jest porównanie zużycia tokenów przez wybrane modele LLM podczas wykonywania analogicznych zadań programistycznych dla trzech stylów komunikacji między klientem i serwerem:

- REST
- gRPC
- Graftcode

Badanie skupia się na ergonomii promptowania i ilości kontekstu potrzebnego modelowi do wygenerowania odpowiedzi. Nie oceniamy automatycznie poprawności biznesowej ani kompilowalności wygenerowanego kodu.

## Badane modele

Lista modeli znajduje się w pliku `models.txt`. Każdy aktywny model z tego pliku jest uruchamiany dla tej samej macierzy przypadków, technologii i iteracji.

## Badane technologie

Dla każdego przypadku badawczego wykonywane są osobne zapytania dla:

- `REST`
- `gRPC`
- `Graftcode`

Każda technologia otrzymuje tylko właściwy dla siebie kod wejściowy oraz wartość `SOLUTION_TYPE`.

## Przypadki badawcze

### Case 1: rozszerzenie istniejącego serwisu

Prompt: `prompt.md`

Model otrzymuje istniejący serwis temperatury z metodą zwracającą temperaturę w Celsjuszach. Zadaniem modelu jest dodanie analogicznej metody zwracającej temperaturę w Fahrenheitach.

Ten przypadek bada koszt tokenowy modyfikacji istniejącego rozwiązania przez dodanie nowej metody.

### Case 2: stworzenie analogicznego serwisu

Prompt: `prompt_amount_service.md`

Model otrzymuje istniejący serwis temperatury jako wzorzec struktury i stylu. Zadaniem modelu jest stworzenie analogicznego serwisu kwot z dwiema metodami:

- metoda zwracająca losową kwotę PLN jako string, np. `123.05 PLN`
- metoda zwracająca losową wartość pomnożoną przez `3.65` jako string USD, np. `65.40 USD`

Ten przypadek bada koszt tokenowy stworzenia podobnego rozwiązania na podstawie istniejącego wzorca.

## Iteracje

Każda kombinacja:

- model
- case
- technologia

jest wykonywana wielokrotnie. Liczba powtórzeń jest ustawiana parametrem `--iterations`.

Dla właściwego przebiegu badania przyjęto:

```bash
.venv/bin/python app.py --iterations 10
```

## Dane wejściowe

Kod wejściowy jest pobierany z repozytorium i wstawiany do promptu w sekcji `INPUT CODE`.

Runner podstawia:

- `SOLUTION_TYPE` jako `REST`, `gRPC` albo `Graftcode`
- `INPUT_CODE` jako komplet plików źródłowych właściwych dla danej technologii

Prompty przekazywane modelom nie zawierają informacji o tym, że mierzone jest zużycie tokenów.

## Mierzone dane

Dla każdego requestu zapisywane są:

- model
- case
- technologia
- numer iteracji
- prompt wysłany do modelu
- odpowiedź modelu
- surowe metadane odpowiedzi
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- koszt raportowany przez OpenRouter, jeśli jest dostępny
- czas trwania requestu
- status wykonania

Główną metryką porównawczą jest `total_tokens`. Pomocniczo analizowane są `prompt_tokens` i `completion_tokens`.

## Statusy i walidacja

Runner zapisuje wynik każdego requestu, także gdy wystąpi błąd.

Statusy:

- `success` - request zakończył się odpowiedzią i kompletnym usage
- `failed` - request zakończył się błędem API lub wyjątkiem
- `invalid_usage` - model zwrócił odpowiedź, ale brakuje wymaganych danych tokenowych

Pole `response_format_valid` jest pomocniczą flagą jakości formatu odpowiedzi. Nie wpływa ono na ważność pomiaru tokenów, jeśli `usage_valid=True`.

Typowe powody `response_format_valid=False`:

- model dodał markdown fences
- model dodał tekst przed pierwszym blokiem pliku
- model nie użył oczekiwanych separatorów `=== FILE: ... ===`

## Założenia dotyczące poprawności kodu

Wygenerowany kod nie musi się kompilować w każdym przypadku. Badanie nie wymaga automatycznego budowania ani testowania odpowiedzi modeli.

Nie mierzymy:

- poprawności kompilacji
- zgodności runtime
- jakości architektury
- pełnej poprawności biznesowej

Te aspekty mogą być analizowane osobno, ale nie są warunkiem ważności pomiaru tokenów.

## Organizacja wyników

Wyniki są zapisywane w katalogu `results/<run_id>/`.

Najważniejszy plik:

```text
results/<run_id>/usage.csv
```

Dodatkowo runner zapisuje:

- `prompt.md` dla każdego requestu
- `response.md` dla każdego requestu
- `metadata.json` dla każdego requestu
- częściowe pliki `usage.csv` dla iteracji i case'ów

Struktura katalogów obejmuje:

```text
results/<run_id>/
  usage.csv
  iteration_01/
  iteration_02/
  ...
  amount_service/
  temperature_extension/
```

## Ograniczenia badania

Wyniki mogą zależeć od:

- aktualnej wersji modelu udostępnianej przez OpenRouter
- routingu providera po stronie OpenRoutera
- sposobu raportowania usage przez API
- cache po stronie providera
- niedeterminizmu modeli mimo `temperature=0`

Dlatego istotne jest przechowywanie pełnych promptów, odpowiedzi i metadanych każdego requestu.
