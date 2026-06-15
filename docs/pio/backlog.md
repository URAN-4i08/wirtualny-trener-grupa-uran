# Cyber Trener - backlog i plan sprintow PIO

Dokument opisuje sposob organizacji pracy nad adaptacja projektu KCK do wymagan przedmiotu **Podstawy Inzynierii Oprogramowania**.

## 1. Role zespolowe

| Sprint | Scrum Master | Zakres odpowiedzialnosci |
| --- | --- | --- |
| Sprint 1 | Szymon Zamachowski | Zebranie wymagan, backlog, UML, konfiguracja repozytorium i CI. |
| Sprint 2 | Piotr Michalak | Zadania TDD, testy logiki domenowej, feature branche, code review. |
| Sprint 3 | Krzysztof Olbinski | Stabilizacja prototypu, poprawki UI/API, przygotowanie prezentacji. |
| Podsumowanie | Dominik Kwintal | Spakowanie kodu, finalna dokumentacja, scenariusz demonstracji. |

Role moga zostac zamienione przez zespol, ale w kazdym sprincie funkcje Scrum Mastera powinna pelnic inna osoba.

## 2. Definition of Done

Zadanie jest zakonczone, gdy:

1. ma opisany cel i kryteria akceptacji,
2. zostalo wykonane na osobnym feature branchu,
3. zawiera test automatyczny, jesli dotyczy logiki domenowej,
4. przechodzi lokalna weryfikacje lub CI,
5. zostalo przejrzane przez inna osobe z zespolu,
6. jest udokumentowane, jesli zmienia zachowanie widoczne dla uzytkownika.

## 3. Product backlog

| ID | User story / zadanie | Kryteria akceptacji | Priorytet | Obszar |
| --- | --- | --- | --- | --- |
| PB-01 | Jako prowadzacy chce zobaczyc dokument wymagan, aby ocenic zgodnosc projektu z zalozeniami. | Istnieje `docs/pio/wymagania.md` z zakresem, wymaganiami i kryteriami odbioru. | Must | Dokumentacja |
| PB-02 | Jako zespol chce miec backlog, aby planowac prace sprintami. | Istnieje backlog z priorytetami i kryteriami akceptacji. | Must | Organizacja |
| PB-03 | Jako prowadzacy chce zobaczyc diagram UML, aby zrozumiec architekture systemu. | Istnieje diagram domeny i komponentow w `docs/pio/uml.md`. | Must | Dokumentacja |
| PB-04 | Jako zespol chce miec CI dla PR-ow, aby szybko wykrywac regresje. | GitHub Actions uruchamia build/lint frontendu i testy logiki. | Must | CI |
| PB-05 | Jako developer chce testowac obliczanie katow, aby bezpiecznie zmieniac progi biomechaniki. | Testy pokrywaja `calculate_angle` i przypadki brzegowe. | Must | TDD |
| PB-06 | Jako developer chce testowac ocene postawy, aby miec szybka informację o regresji. | Testy sprawdzaja komunikat dla poprawnej i blednej postawy. | Must | TDD |
| PB-07 | Jako developer chce testowac fuzje Dual-Cam, aby utrzymac stabilna punktacje. | Testy sprawdzaja wynik bez pilki, z poprawnym kontaktem i z prostymi kolanami. | Should | TDD |
| PB-08 | Jako cwiczacy chce widziec osobne informacje o elementach techniki, aby wiedziec co poprawic. | UI rozroznia stopy, kolana, rece/platforme, ruch. | Should | Frontend |
| PB-09 | Jako cwiczacy chce zapisac trening, aby sprawdzic historie postepow. | Sesja po zakonczeniu trafia do tabel Supabase i jest widoczna w historii. | Must | Backend / Supabase |
| PB-10 | Jako prowadzacy chce uruchomic demo wedlug instrukcji, aby szybko sprawdzic prototyp. | Dokument uruchomienia zawiera kroki instalacji i scenariusz prezentacji. | Must | Dokumentacja |
| PB-11 | Jako zespol chce miec opis procesu code review, aby kazdy uczestniczyl w kontroli jakosci. | PR-y zawieraja opis zmian, testy i osobe reviewujaca. | Should | Organizacja |
| PB-12 | Jako uzytkownik chce sterowac analiza glosem, aby nie dotykac laptopa podczas cwiczenia. | Komendy start/stop i nawigacja dzialaja z poziomu panelu glosowego. | Should | Audio / UI |
| PB-13 | Jako developer chce udokumentowac schemat Supabase, aby odtworzyc baze w nowym projekcie. | Repozytorium zawiera opis tabel, kluczy i polityk RLS. | Should | Baza danych |
| PB-14 | Jako zespol chce przygotowac prezentacje, aby pokazac aplikacje i proces wytwórczy. | Prezentacja omawia projekt, narzedzia, technologie, sprinty i problemy. | Must | Podsumowanie |

## 4. Sprint 1 - wymagania, repozytorium, CI

### Cel sprintu

Przygotowac projekt do prowadzenia zgodnie z zasadami PIO: wymagania, backlog, UML, CI i pierwsza baza pod TDD.

### Zadania

| ID | Zadanie | Kryterium akceptacji | Sugerowana galaz |
| --- | --- | --- | --- |
| S1-01 | Spisac wymagania PIO na podstawie projektu KCK. | `docs/pio/wymagania.md` zawiera zakres, wymagania i kryteria odbioru. | `feature/pio-requirements` |
| S1-02 | Przygotowac product backlog i plan sprintow. | `docs/pio/backlog.md` zawiera PB, sprinty i Definition of Done. | `feature/pio-backlog` |
| S1-03 | Przygotowac wysokopoziomowy UML. | `docs/pio/uml.md` zawiera diagram domeny i komponentow. | `feature/pio-uml` |
| S1-04 | Dodac GitHub Actions. | Workflow uruchamia sie dla `push` i `pull_request`. | `feature/pio-ci` |
| S1-05 | Dodac pierwsze testy logiki. | Testy przechodza komenda `python -m unittest discover`. | `feature/pio-tests` |

## 5. Sprint 2 - TDD i stabilizacja logiki domenowej

### Cel sprintu

Wykonac male zadania programistyczne z uzyciem TDD i feature branch, szczegolnie w logice oceniania techniki.

### Zadania

| ID | Zadanie | Test przed implementacja | Kryterium akceptacji |
| --- | --- | --- | --- |
| S2-01 | Dopracowac testy `calculate_angle`. | Test dla 90, 180 i kata odbitego przez granice 180 stopni. | Funkcja zwraca przewidywalne wartosci. |
| S2-02 | Testowac histereze komunikatu kolan. | Test pozycji z wyprostowanymi i ugietymi kolanami. | Komunikat nie przelacza sie chaotycznie. |
| S2-03 | Testowac fuzje Dual-Cam. | Test danych front/bok z kontaktem i praca nog. | Wynik fuzji miesci sie w oczekiwanym zakresie. |
| S2-04 | Opisac code review. | Szablon checklisty review w dokumentacji. | Kazdy PR ma checklistę. |
| S2-05 | Uzupelnic dokumentacje Supabase. | Opis tabel i RLS. | Nowa osoba wie, jak odtworzyc baze. |

## 6. Sprint 3 - finalny zakres prototypu i prezentacja

### Cel sprintu

Ustabilizowac prototyp, ograniczyc zakres do dzialajacych funkcji i przygotowac materialy do oddania.

### Zadania

| ID | Zadanie | Kryterium akceptacji |
| --- | --- | --- |
| S3-01 | Zweryfikowac scenariusz demo w sali. | Instrukcja demo jest aktualna i mozliwa do wykonania krok po kroku. |
| S3-02 | Sprawdzic build frontendu. | `npm run build` konczy sie sukcesem. |
| S3-03 | Sprawdzic backend bez kamery w zakresie importu/logiki. | Testy unit przechodza bez uruchamiania YOLO i MediaPipe. |
| S3-04 | Przygotowac prezentacje. | Slajdy zawieraja opis projektu, metodologii, narzedzi, technologii i problemow. |
| S3-05 | Przygotowac paczke finalna. | Kod, dokumenty i prezentacja sa gotowe do dodania na WIKAMP. |

## 7. Proponowana tablica zadan

Kolumny:

1. **Backlog** - pomysly i zadania niegotowe do realizacji.
2. **Ready for sprint** - zadania z opisem i kryteriami akceptacji.
3. **In progress** - zadania realizowane na feature branchu.
4. **Code review** - zadania z pull requestem.
5. **CI / Testy** - zadania po review, czekajace na wynik pipeline.
6. **Done** - zadania spelniajace Definition of Done.

## 8. Checklista pull requestu

Kazdy PR powinien zawierac:

- [ ] krotki opis zmiany,
- [ ] numer zadania z backlogu,
- [ ] informacje, jakie testy uruchomiono,
- [ ] screen lub opis efektu w UI, jesli dotyczy,
- [ ] wskazanie osoby wykonujacej code review,
- [ ] brak sekretow i kluczy prywatnych w zmianach.

## 9. Ryzyka projektowe

| Ryzyko | Wplyw | Reakcja |
| --- | --- | --- |
| Niestabilna detekcja pilki przy slabym swietle. | Niska jakosc demo. | Uzyc dobrego oswietlenia i przygotowanego nagrania awaryjnego. |
| Brak kamery bocznej podczas prezentacji. | Ograniczony Dual-Cam. | Pokazac tryb jednej kamery i opisac Dual-Cam w dokumentacji. |
| Ciezkie zaleznosci CV w CI. | Wolniejsze lub niestabilne pipeline'y. | Testowac czysta logike bez importu OpenCV/MediaPipe. |
| Niepoprawna konfiguracja Supabase. | Brak historii treningow. | Przygotowac opis zmiennych `.env` i schematu bazy. |
| Zbyt duzy zakres funkcji. | Niedokonczone elementy. | Trzymac finalny prototyp przy odbiciu dolnym i najwazniejszych kryteriach techniki. |

