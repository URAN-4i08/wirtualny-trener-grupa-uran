# Konsultacja merytoryczna — odbicie dolne w siatkówce

Dokument opisuje ustalenia z konsultacji z osobą uprawiającą siatkówkę (trener / zawodnik). Stanowi podstawę reguł w `logic/coach_engine.py` i `logic/biomechanics.py` oraz scenariusza użycia aplikacji.

> Wymóg projektu KCK (*Cyber trener*): system powinien być nadzorowany przez osobę znającą sport i typowe błędy techniczne. Niniejszy plik dokumentuje tę część pracy zespołu.

---

## Cel ćwiczenia w aplikacji

Aplikacja wspiera **naukę podstaw techniki odbicia dolnego** — scenariusz treningowy to:

1. Ćwiczący **podrzuca piłkę do góry** (samodzielnie lub z partnera).
2. Przyjmuje **pozycję gotowości** przed kontaktem.
3. Wykonuje **odbicie sposobem dolnym** (platforma z przedramion, złączone dłonie).
4. Po odbiciu ma **chwilę na sprawdzenie feedbacku** na ekranie i powrót do kolejnej próby.

To nie jest symulacja pełnego przyjęcia po serwisie w meczu, lecz **ćwiczenie techniczne** pod kątem poprawnej postawy i momentu kontaktu.

---

## Priorytety oceny (kolejność od najważniejszego)

| Priorytet | Element techniczny | Co sprawdzamy | Typowy komunikat |
|-----------|-------------------|---------------|------------------|
| 1 | **Ugięcie kolan** | Nogi amortyzują — kolana nie mogą być sztywno wyprostowane | „Ugnij kolana” |
| 2 | **Wyprost łokci** | Łokcie wyprostowane, platforma sztywna | „Wyprostuj łokcie” |
| 3 | **Złączone dłonie / platforma** | Nadgarstki blisko siebie, kontakt na przedramionach | „Złącz dłonie” |
| 4 | **Ustawienie stóp** | Stopy równoległe, stabilny rozstaw względem barków | „Popraw stopy” |

### Poza zakresem bieżącej implementacji

W trakcie konsultacji wspomniano o **pochyleniu tułowia do przodu**. Na obecnym etapie projektu **nie implementujemy** tego kryterium — skupiamy się na dopracowaniu punktów 1–4 i stabilności detekcji na żywo.

---

## Model feedbacku (ustalenia zespołu + trener)

### Przed i w trakcie przygotowania do odbicia

- System **ciągle** analizuje postawę, gdy w kadrze jest sylwetka.
- Komunikaty pojawiają się na ekranie (i opcjonalnie głosem TTS).
- W panelu bocznym widać **kafelki gotowości**: Stopy, Kolana, Ręce, Nogi — zielone gdy warunek spełniony.

### W momencie kontaktu z piłką

- YOLO wykrywa piłkę; backend ocenia technikę w chwili zbliżenia do przedramion / nadgarstków.
- Licznik odbić inkrementuje się przy każdym nowym kontakcie.

### Po odbiciu (3 sekundy)

- Faza **FOLLOW_THROUGH** — przez ok. **3 sekundy** na ekranie pozostaje podsumowanie ostatniego odbicia.
- Ćwiczący **nie musi patrzeć na monitor w trakcie ruchu** — może podejść do laptopa po powtórzeniu i sprawdzić błędy przed kolejną próbą.
- To odpowiada wymaganiu z polecenia projektu: interfejs głosowy / audio w trakcie, ekran do analizy **po** próbie.

---

## Scena laboratoryjna (docelowa konfiguracja)

| Element | Opis |
|---------|------|
| Laptop | Uruchamia backend + frontend; podłączony do rzutnika (opcjonalnie) |
| Kamera laptopa | Widok frontowy — dłonie, piłka, platforma |
| Telefon (kabel USB) | Widok boczny — dokładniejsza ocena kolan i pracy nóg (tryb Dual-Cam, opcjonalny) |
| Mikrofon | Laptop — komendy głosowe (Vosk) |
| Głośniki laptopa | Komunikaty TTS trenera |

Druga kamera **nie jest wymagana** — przy jednej kamerze system działa, ale zaleca się podłączenie telefonu dla lepszej oceny ugięcia kolan.

---

## Mapowanie kryteriów → kod

| Kryterium | Moduł | Funkcja / klasa |
|-----------|-------|-----------------|
| Kolana (live, wygładzone) | `logic/coach_engine.py` | `VolleyballPostureEvaluator` |
| Kolana (fazy, dual-cam) | `logic/biomechanics.py` | `analizuj_bok()`, `analizuj_faze()` |
| Łokcie, dłonie, platforma | `logic/coach_engine.py` | `VolleyballPostureEvaluator` |
| Łokcie, złączone dłonie | `logic/biomechanics.py` | `analizuj_front()` |
| Stopy — rozstawienie | `logic/biomechanics.py` | `analizuj_stopy()` |
| Moment odbicia | `server.py` | `BallContactTracker` |
| Fuzja 2 kamer | `logic/biomechanics.py` | `fuzja_sensorow()` |

Progi liczbowe są w plikach źródłowych w sekcjach konfiguracji — do strojenia na realnych nagraniach z sali.

---

## Typowe błędy ćwiczących (wg konsultacji)

1. **Sztywne kolana** — brak amortyzacji, postawa zbyt wysoka.
2. **Zgięte łokcie** — platforma „za miękka”, piłka nie odbija się pionowo.
3. **Rozłączone dłonie** — odbicie nadgarstkami zamiast przedramionami.
4. **Zbyt wąski lub zbyt szeroki rozstaw stóp** — niestabilna baza.
5. **Odbicie bez pracy nóg** — ruch tylko rękami (wykrywane m.in. przy Dual-Cam).

---

## Dalsze dopracowanie logiki (plan zespołu)

- Kalibracja progów na nagraniach z sali (macOS, kamera kablowa, stały kadr).
- Rozdzielenie oceny **łokci** i **rąk** w interfejsie (osobne kafelki).
- Dokładniejsza ocena **równoległości stóp** (obecnie: głównie rozstawienie).
- Zapis **% poprawności per element** w statystykach sesji (pod raport naukowy).
- Ujednolicenie komunikatów PL w całym pipeline (TTS + UI).

---

## Odniesienie do polecenia KCK

| Wymaganie PDF | Realizacja |
|---------------|------------|
| Sport technicznie trudny | Siatkówka — odbicie dolne |
| Konsultacja z ekspertem | Ten dokument + reguły w kodzie |
| Instalacja stacjonarna w sali | Laptop + kamera(e), nie aplikacja mobilna |
| Interfejs głosowy + ekran po próbie | Vosk + TTS + faza FOLLOW_THROUGH (3 s) |
| Dwie kamery | Dual-Cam (opcjonalnie) |
| Własne funkcje obliczeniowe | `calculate_angle`, EMA, histereza, `analizuj_*`, fuzja sensorów |

---

*Ostatnia aktualizacja dokumentacji: czerwiec 2026 — Grupa Uran*
