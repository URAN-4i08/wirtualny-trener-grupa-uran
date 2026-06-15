# Cyber Trener - specyfikacja wymagan PIO

Dokument przygotowany na potrzeby przedmiotu **Podstawy Inzynierii Oprogramowania**. Bazuje na gotowym projekcie KCK "Cyber Trener" i porzadkuje go w formie wymaganej dla pracy zespolowej prowadzonej sprintami.

## 1. Cel projektu

Celem systemu jest wsparcie nauki **odbicia dolnego w siatkowce** poprzez automatyczna analize obrazu z kamery, ocene postawy cwiczacego oraz przekazywanie informacji zwrotnej na ekranie i glosowo.

Projekt ma pokazac praktyczne uzycie:

- pracy zespolowej w sprintach z elementami Scrum,
- backlogu i zadan realizowanych na feature branchach,
- TDD dla wydzielonej logiki domenowej,
- code review przed scalaniem zmian,
- CI uruchamianego dla pull requestow.

## 2. Zakres funkcjonalny prototypu

### W zakresie

1. Analiza sylwetki cwiczacego z wykorzystaniem MediaPipe Pose.
2. Detekcja pilki z wykorzystaniem YOLO.
3. Ocena pozycji gotowosci do odbicia dolnego:
   - ugiecie kolan,
   - ustawienie lokci,
   - zlaczenie dloni / platforma przedramion,
   - rozstaw stop,
   - widocznosc sylwetki w kadrze.
4. Rozpoznanie faz ruchu:
   - `OCZEKIWANIE`,
   - `PRZYGOTOWANIE`,
   - `KONTAKT`,
   - `FOLLOW_THROUGH`.
5. Wyswietlanie podpowiedzi i kafelkow gotowosci w interfejsie React.
6. Obsluga pojedynczej kamery, opcjonalnego trybu Dual-Cam oraz uploadu pliku wideo.
7. Sterowanie glosowe wybranymi akcjami aplikacji.
8. Opcjonalne komunikaty TTS.
9. Logowanie uzytkownika i zapis historii treningow w Supabase.
10. Prezentacja statystyk sesji w dashboardzie i historii.

### Poza zakresem obecnej wersji

1. Pelna analiza taktyczna meczu siatkarskiego.
2. Ocena wszystkich technik siatkarskich - projekt koncentruje sie na odbiciu dolnym.
3. Produkcyjne wdrozenie chmurowe.
4. Gwarancja dzialania dla kazdego typu kamery i oswietlenia.
5. Automatyczne trenowanie wlasnego modelu detekcji pilki.

## 3. Interesariusze

| Interesariusz | Potrzeba |
| --- | --- |
| Cwiczacy / student | Otrzymuje szybki feedback o bledach technicznych. |
| Trener / prowadzacy | Moze ocenic prototyp, poprosic o drobna zmiane w kodzie i sprawdzic organizacje pracy. |
| Zespol projektowy | Pracuje wedlug backlogu, sprintow, TDD, feature branch i code review. |
| Uzytkownik techniczny | Uruchamia backend, frontend i konfiguracje Supabase. |

## 4. Reguly domenowe

Reguly domenowe wynikaja z konsultacji sportowej opisanej w `KONSULTACJA_TRENERA.md`.

| Priorytet | Regula | Uzasadnienie | Miejsce w kodzie |
| --- | --- | --- | --- |
| 1 | Kolana nie moga byc calkowicie wyprostowane. | Nogi amortyzuja ruch i nadaja kierunek odbiciu. | `logic/coach_engine.py`, `logic/biomechanics.py` |
| 2 | Lokcie powinny tworzyc stabilna platforme. | Zgiete lokcie powoduja miekkie i niekontrolowane odbicie. | `logic/coach_engine.py`, `logic/biomechanics.py` |
| 3 | Dlonie powinny byc blisko siebie. | Kontakt powinien nastapic na przedramionach, a nie przypadkowo na nadgarstkach. | `logic/coach_engine.py`, `logic/biomechanics.py` |
| 4 | Stopy powinny dawac stabilna baze. | Zbyt waski lub zbyt szeroki rozstaw utrudnia utrzymanie pozycji. | `logic/biomechanics.py` |
| 5 | Po odbiciu system pokazuje krotkie podsumowanie. | Cwiczacy nie musi patrzec na ekran w trakcie ruchu. | `backend/training_session.py`, `frontend/src/components/live/*` |

## 5. Wymagania funkcjonalne

| ID | Wymaganie | Kryterium akceptacji | Priorytet |
| --- | --- | --- | --- |
| WF-01 | System wykrywa sylwetke w kadrze. | Po ustawieniu osoby przed kamera UI pokazuje metryki postawy zamiast komunikatu o braku sylwetki. | Must |
| WF-02 | System oblicza katy kolan i lokci. | Dla poprawnych punktow ciala backend zwraca katy i ocene punktowa. | Must |
| WF-03 | System wykrywa zbyt proste kolana. | Przy pozycji stojacej pojawia sie komunikat "Ugnij kolana". | Must |
| WF-04 | System wykrywa rozlaczone dlonie. | Przy szeroko rozstawionych nadgarstkach pojawia sie komunikat "Zlacz dlonie". | Must |
| WF-05 | System wykrywa kontakt pilki z platforma. | Gdy pilka jest blisko nadgarstkow, licznik odbic zwieksza sie maksymalnie raz dla jednego kontaktu. | Must |
| WF-06 | System prezentuje faze ruchu. | UI rozroznia oczekiwanie, przygotowanie, kontakt i follow-through. | Must |
| WF-07 | System obsluguje nagranie wideo. | Po wgraniu pliku backend przetwarza klatki i pozwala odtworzyc analize. | Should |
| WF-08 | System obsluguje Dual-Cam. | Po wlaczeniu trybu system laczy dane front/bok i pokazuje wynik fuzji. | Should |
| WF-09 | Uzytkownik moze sterowac analiza glosem. | Komendy "rozpocznij analize" i "zatrzymaj analize" uruchamiaja odpowiednie akcje. | Should |
| WF-10 | Uzytkownik moze zapisac sesje treningowa. | Po zakonczonej sesji zalogowany uzytkownik widzi ja w historii. | Must |
| WF-11 | Uzytkownik moze przegladac statystyki. | Dashboard pokazuje zapisane treningi i podstawowe metryki. | Should |
| WF-12 | Uzytkownik moze usunac trening z historii. | Po usunieciu wpis znika z listy oraz z tabeli statystyk. | Could |

## 6. Wymagania niefunkcjonalne

| ID | Wymaganie | Kryterium akceptacji |
| --- | --- | --- |
| WN-01 | Czytelnosc kodu | Logika domenowa jest oddzielona od UI i API, a nazwy funkcji wskazuja odpowiedzialnosc. |
| WN-02 | Testowalnosc | Czyste funkcje logiki moga byc testowane bez kamery, modelu YOLO i przegladarki. |
| WN-03 | CI | Pull request uruchamia automatycznie lint/build frontendu oraz testy logiki backendowej. |
| WN-04 | Konfigurowalnosc | Dane Supabase i parametry live sa przekazywane przez zmienne srodowiskowe. |
| WN-05 | Bezpieczenstwo danych | Frontend uzywa publicznego klucza Supabase, a zapis danych wymaga tokenu zalogowanego uzytkownika. |
| WN-06 | Praca lokalna | Po instalacji zaleznosci aplikacja dziala lokalnie na laptopie w sali. |
| WN-07 | Latwosc prezentacji | Repozytorium zawiera instrukcje uruchomienia i scenariusz demonstracji. |

## 7. Dane i integracje

### Supabase

System korzysta z Supabase Auth i tabel:

- `trainings` - sesje treningowe uzytkownika,
- `training_stats` - statystyki przypisane do sesji.

Zasady bezpieczenstwa:

- w kodzie nie wolno umieszczac klucza `service_role`,
- zapis treningu wymaga tokenu sesji,
- tabele w schemacie publicznym powinny miec wlaczone RLS i polityki ograniczajace dostep do wlasciciela danych.

### API i WebSocket

- REST: konfiguracja zrodla, sesje, kamery, upload wideo.
- WebSocket: metryki live i komendy glosowe.
- MJPEG: podglad obrazu z naniesionymi metrykami.

## 8. Kryteria odbioru projektu PIO

1. Repozytorium zawiera dokument wymagan, backlog i diagram UML.
2. Repozytorium zawiera konfiguracje CI uruchamiana dla pull requestow.
3. Co najmniej jedna czesc logiki domenowej posiada testy automatyczne.
4. Zadania sa opisane jako male, weryfikowalne elementy mozliwe do realizacji na feature branchach.
5. Dokumentacja wskazuje, jak projekt spelnia wymagania z PDF-a:
   - Scrum / sprinty,
   - TDD,
   - Feature Branch,
   - Code Review,
   - CI,
   - prezentacja dzialajacego prototypu.

