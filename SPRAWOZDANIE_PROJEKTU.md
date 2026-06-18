# SPRAWOZDANIE Z PROJEKTU ZESPOLOWEGO

**TEMAT:** Cyber Trener - wirtualny trener odbicia dolnego w siatkowce

**Repozytorium projektu:** <https://github.com/URAN-4i08/wirtualny-trener-grupa-uran>

**Przedmiot:** KCK / Cyber trener

**Uczelnia / grupa:** Politechnika Lodzka, grupa URAN

**Data oddania:** [UZUPELNIC: data]

## Zespol projektowy

1. Szymon Zamachowski - 255735
2. Piotr Michalak - 255654
3. Krzysztof Olbinski - 255667
4. Dominik Kwintal - 255647

**Prowadzacy:** [UZUPELNIC: imie i nazwisko prowadzacego]

---

## 1. Wstep

Projekt **Cyber Trener** jest stacjonarna aplikacja wspomagajaca nauke odbicia pilki sposobem dolnym w siatkowce. System analizuje postawe osoby cwiczacej z obrazu kamery, wykrywa pilke, ocenia kluczowe elementy techniki i przekazuje informacje zwrotne na ekranie oraz opcjonalnie glosowo.

Glownym celem projektu bylo stworzenie narzedzia, ktore pozwala cwiczacemu otrzymac szybka informacje zwrotna bez stalej obecnosci trenera. Aplikacja nie zastepuje instruktora sportowego, ale pomaga wychwytywac najczestsze bledy techniczne podczas podstawowego cwiczenia: przyjecia pozycji gotowosci, kontaktu z pilka na przedramionach oraz kontroli pracy nog.

Projekt odpowiada na problem ograniczonej dostepnosci natychmiastowej korekty techniki podczas samodzielnego treningu. W tradycyjnym treningu siatkarskim poczatkujacy zawodnik czesto potrzebuje osoby obserwujacej z boku, poniewaz w trakcie ruchu trudno samodzielnie ocenic ustawienie kolan, lokci, rak i stop. Cyber Trener wykorzystuje komputerowa analize obrazu, aby wyswietlic komunikaty takie jak: **"Ugnij kolana"**, **"Wyprostuj lokcie"**, **"Zlacz dlonie"** lub **"Popraw rozstaw stop"**.

Zakres projektu obejmuje:

- detekcje sylwetki cwiczacego,
- detekcje pilki siatkowej,
- ocene pozycji ciala w czasie rzeczywistym,
- identyfikacje faz ruchu,
- tryb jednej kamery oraz opcjonalny tryb Dual-Cam,
- sterowanie glosowe i komunikaty TTS,
- zapis sesji treningowych w bazie Supabase,
- interfejs webowy z panelem analizy, historia i statystykami.

### 1.1. Przeglad istniejacych rozwiazan

**Trening z trenerem** - Najdokladniejsza forma nauki techniki, ale wymaga dostepnosci trenera, sali i czasu. Korekta jest bezposrednia, lecz zalezy od mozliwosci organizacyjnych.

**Analiza nagrania po treningu** - Pozwala obejrzec ruch po wykonaniu cwiczenia, ale nie daje natychmiastowej informacji zwrotnej. Zawodnik moze przez dluzszy czas utrwalac bledy, zanim zostana one omowione.

**Aplikacje fitness i sportowe** - Czesto skupiaja sie na ogolnej aktywnosci, liczbie powtorzen lub pulsie, rzadziej na precyzyjnej technice konkretnego elementu siatkarskiego.

**Systemy motion capture** - Sa dokladne, ale kosztowne i wymagaja specjalistycznego sprzetu, markerow lub dedykowanego studia pomiarowego.

Cyber Trener wypelnia luke pomiedzy prostym nagraniem wideo a profesjonalnym systemem motion capture. Wykorzystuje ogolnodostepny sprzet: laptop, kamere internetowa oraz opcjonalnie telefon jako druga kamere.

---

## 2. Przeglad literatury i technologii

### 2.1. Estymacja pozy czlowieka

Podstawa dzialania systemu jest estymacja pozy czlowieka, czyli wykrywanie charakterystycznych punktow ciala na obrazie. W projekcie wykorzystano **MediaPipe Pose**, ktore zwraca punkty takie jak barki, lokcie, nadgarstki, biodra, kolana i kostki. Na ich podstawie system oblicza katy stawowe oraz relacje przestrzenne potrzebne do oceny techniki.

W przeciwienstwie do klasycznej detekcji obiektow, estymacja pozy pozwala opisac uklad ciala jako zestaw punktow anatomicznych. Dzieki temu mozliwe jest sprawdzanie, czy kolana sa ugiete, lokcie sa odpowiednio ustawione, a platforma z przedramion znajduje sie przed cialem.

### 2.2. Detekcja pilki

Do wykrywania pilki wykorzystano model **YOLO** z biblioteki Ultralytics oraz dodatkowa detekcje kolorystyczna HSV. YOLO sluzy jako pierwszy sygnal wykrycia obiektu typu `sports ball`, natomiast detekcja kolorystyczna pomaga przy pilkach siatkarskich o charakterystycznych zolto-niebieskich panelach.

W projekcie ograniczono obszar poszukiwania pilki do strefy wokol dloni i przedramion cwiczacego. Zmniejsza to ryzyko falszywych detekcji, np. lamp, mebli lub innych okraglych obiektow w tle.

### 2.3. Biomechanika odbicia dolnego

Reguly oceny zostaly oparte na konsultacji merytorycznej opisanej w pliku `KONSULTACJA_TRENERA.md`. Najwazniejsze elementy techniczne to:

1. ugiecie kolan,
2. ustawienie lokci,
3. zlaczenie dloni i utworzenie platformy z przedramion,
4. stabilny rozstaw stop,
5. zaangazowanie pracy nog.

Na obecnym etapie projekt celowo nie ocenia pochylenia tulowia jako glownego kryterium. Zespol skupil sie na stabilniejszej detekcji elementow najwazniejszych dla podstawowego odbicia dolnego.

### 2.4. Architektura aplikacji webowej

System zostal zbudowany w architekturze klient-serwer:

- backend: **Python 3.11, FastAPI, Uvicorn, OpenCV, MediaPipe, Ultralytics YOLO**,
- frontend: **React 19, TypeScript, Vite, Tailwind CSS, Recharts**,
- komunikacja: **REST API, WebSocket, strumien MJPEG**,
- baza danych: **Supabase / PostgreSQL**,
- audio: **Vosk STT** do rozpoznawania komend oraz **Edge TTS / pyttsx3 / Amazon Polly** do komunikatow glosowych.

Backend odpowiada za przetwarzanie obrazu, wykrywanie pozy i pilki, obliczenia biomechaniczne oraz zapis sesji. Frontend prezentuje wynik analizy, kafelki gotowosci, licznik odbic, historie treningow i panel sterowania.

---

## 3. Materialy i metody

### 3.1. Dane wejsciowe i konfiguracja sprzetowa

System moze pracowac w kilku trybach:

1. **Pojedyncza kamera frontowa** - podstawowy tryb pracy. Kamera ustawiona przed cwiczacym analizuje sylwetke, rece, pilke i ogolna pozycje.
2. **Pojedyncza kamera boczna** - tryb pomocniczy, korzystny do analizy ugiecia kolan i pracy nog.
3. **Dual-Cam** - jednoczesne wykorzystanie kamery frontowej i bocznej. Kamera laptopa moze pelnic role widoku frontowego, a telefon podlaczony przez USB lub systemowy mechanizm kamery role widoku bocznego.
4. **Upload pliku wideo** - uzytkownik moze przeslac nagranie, ktore backend analizuje w tle, zapisujac przetworzone klatki i metryki.

Konfiguracja testowa wykorzystana w sprawozdaniu:

| Element | Wartosc |
|---------|---------|
| Laptop / komputer | [UZUPELNIC: model, CPU, RAM] |
| System operacyjny | [UZUPELNIC: Windows/macOS/Linux + wersja] |
| Kamera frontowa | [UZUPELNIC] |
| Kamera boczna / telefon | [UZUPELNIC lub "nie uzyto"] |
| Przegladarka | [UZUPELNIC] |
| Warunki oswietleniowe | [UZUPELNIC] |
| Liczba wykonanych prob | [UZUPELNIC] |

### 3.2. Struktura systemu

Najwazniejsze pliki i katalogi:

| Sciezka | Rola |
|---------|------|
| `server.py` | Punkt wejscia backendu FastAPI |
| `backend/app.py` | Konfiguracja aplikacji FastAPI i CORS |
| `backend/routes.py` | Endpointy REST, WebSockety, wybor zrodla obrazu |
| `backend/streams.py` | Petle analizy kamery, Dual-Cam i uploadowanych plikow |
| `backend/vision.py` | MediaPipe, detekcja pilki, budowanie punktow ciala |
| `logic/coach_engine.py` | Ocena postawy, katy stawow, EMA, histereza |
| `logic/biomechanics.py` | Analiza front/bok, fazy ruchu, stopy, fuzja kamer |
| `backend/training_session.py` | Logika sesji czasowej i podsumowan |
| `backend/supabase_client.py` | Zapis wynikow treningu do Supabase |
| `audio/speech_recognition.py` | Rozpoznawanie mowy z uzyciem Vosk |
| `audio/voice_control.py` | Komunikaty glosowe trenera |
| `frontend/src/pages/LiveAnalysis.tsx` | Glowny ekran analizy na zywo |
| `frontend/src/pages/Dashboard.tsx` | Panel statystyk |
| `frontend/src/pages/History.tsx` | Historia sesji treningowych |
| `frontend/src/pages/Warmup.tsx` | Modul rozgrzewki |

### 3.3. Przeplyw danych

Uproszczony przeplyw danych w systemie:

1. Kamera lub plik wideo dostarcza klatki obrazu.
2. Backend odczytuje klatke za pomoca OpenCV.
3. MediaPipe Pose wykrywa punkty ciala.
4. YOLO i/lub detekcja HSV wyszukuje pilke.
5. Moduly `coach_engine.py` i `biomechanics.py` obliczaja metryki:
   - katy kolan,
   - katy lokci,
   - odleglosc nadgarstkow,
   - rozstaw stop,
   - faze ruchu,
   - wynik techniki 0-100.
6. Backend aktualizuje globalny stan metryk.
7. Frontend odbiera metryki przez WebSocket `/ws/metrics`.
8. Obraz z naniesiona analiza jest wysylany do przegladarki jako strumien MJPEG.
9. Po sesji dane moga zostac zapisane w Supabase.

### 3.4. Analiza postawy

Modul `VolleyballPostureEvaluator` w pliku `logic/coach_engine.py` ocenia pozycje na podstawie punktow ciala. Wykorzystuje:

- funkcje `calculate_angle(a, b, c)` do obliczania katow,
- wykladnicza srednia kroczaca EMA do stabilizacji odczytow,
- histereze progow, aby komunikaty nie migotaly przy wartosciach granicznych,
- punktacje startujaca od 100 punktow i odejmowana za konkretne bledy.

Przykladowe kryteria:

| Element | Sposob oceny | Przykladowy komunikat |
|---------|--------------|-----------------------|
| Kolana | Kat biodro-kolano-kostka | "Ugnij kolana" |
| Lokcie | Kat ramie-lokiec-nadgarstek | "Wyprostuj lokcie" |
| Dlonie | Odleglosc nadgarstkow wzgledem barkow | "Zlacz dlonie" |
| Platforma | Polozenie nadgarstkow wzgledem lokci | "Ustaw przedramiona nizej" |

### 3.5. Analiza faz ruchu

W pliku `logic/biomechanics.py` zaimplementowano przejscia miedzy fazami:

```text
OCZEKIWANIE -> PRZYGOTOWANIE -> KONTAKT -> FOLLOW_THROUGH
```

Znaczenie faz:

- **OCZEKIWANIE** - zawodnik ustawia sie w kadrze i przyjmuje pozycje gotowosci,
- **PRZYGOTOWANIE** - pilka znajduje sie w ruchu, a system pokazuje gotowosc segmentow,
- **KONTAKT** - wykryto odbicie,
- **FOLLOW_THROUGH** - przez ok. 3 sekundy widoczne jest podsumowanie ostatniego odbicia.

Taki model jest zgodny z zalozeniem, ze cwiczacy nie musi patrzec na ekran w trakcie ruchu. Informacja zwrotna moze zostac odczytana po wykonaniu proby.

### 3.6. Tryb Dual-Cam i fuzja wynikow

Tryb Dual-Cam laczy informacje z dwoch kamer:

- kamera frontowa: rece, pilka, platforma, symetria,
- kamera boczna: ugiecie kolan, praca nog, trajektoria nadgarstkow.

Funkcja `fuzja_sensorow()` laczy wyniki w ocene 0-100. Przykladowe wagi:

| Kryterium | Waga |
|-----------|------|
| Kontakt z pilka potwierdzony przez kamere frontowa | 40 pkt |
| Kat kolanowy | 25 pkt |
| Zlaczone nadgarstki | 20 pkt |
| Wykryty zamach / praca nog | 15 pkt |

Dzieki temu system moze wykryc sytuacje, w ktorej zawodnik odbija pilke glownie rekami, bez odpowiedniego zaangazowania nog.

### 3.7. Sesje treningowe

Logika sesji znajduje sie w `backend/training_session.py`. Sesja sklada sie z etapow:

1. **setup** - uzytkownik ustawia postawe, az wszystkie segmenty gotowosci sa poprawne,
2. **prep** - odliczanie przed aktywna proba,
3. **active** - wlasciwy czas odbic,
4. **summary** - podsumowanie liczby odbic, sredniego wyniku i najlepszego wyniku.

Domyslny czas aktywnej proby wynosi 30 sekund, ale interfejs pozwala wybrac inna wartosc w dozwolonym zakresie.

### 3.8. Interfejs uzytkownika

Frontend zostal przygotowany w React i TypeScript. Najwazniejsze widoki:

- **Login / Register** - logowanie i rejestracja przez Supabase Auth,
- **Dashboard** - statystyki treningow,
- **Live Analysis** - analiza kamery, Dual-Cam lub pliku wideo,
- **History** - lista zapisanych sesji,
- **Warmup** - rozgrzewka przed treningiem,
- **Voice Commands** - panel komend glosowych.

Na ekranie analizy widoczne sa m.in.:

- podglad obrazu,
- wynik techniki,
- licznik odbic,
- kafelki gotowosci,
- faza ruchu,
- komunikaty trenera,
- przyciski wyboru zrodla obrazu.

**Rys. 1. Interfejs aplikacji Cyber Trener - ekran analizy na zywo.**

[UZUPELNIC: wstawic zrzut ekranu Live Analysis]

### 3.9. Sterowanie glosowe i TTS

Sterowanie glosowe wykorzystuje model Vosk i WebSocket `/ws/voice`. Parser komend rozpoznaje m.in.:

- "rozpocznij analize",
- "zatrzymaj analize",
- "panel glowny",
- "historia",
- "rozgrzewka",
- "analiza".

Komunikaty trenera moga byc odczytywane przez TTS. Jest to istotne, poniewaz podczas wykonywania odbicia zawodnik powinien skupic wzrok na pilce i ruchu, a nie na ekranie.

---

## 4. Algorytmika i pseudokod

### 4.1. Glowna petla analizy

```text
Algorytm AnalyzeFrame(frame):
1. Pobierz klatke z kamery lub pliku.
2. Zmniejsz rozdzielczosc robocza, jesli wymagaja tego ustawienia wydajnosci.
3. Wykryj sylwetke przez MediaPipe Pose.
4. Jesli sylwetka nie zostala wykryta:
   a. wyswietl komunikat "Szukam sylwetki w kadrze",
   b. zachowaj poprzednie metryki przez krotki czas stabilizacji.
5. Zbuduj slownik punktow ciala:
   barki, lokcie, nadgarstki, biodra, kolana, kostki, stopy.
6. Wykryj pilke:
   a. YOLO - obiekt "sports ball",
   b. HSV - kandydaci kolorystyczni w strefie przy rekach.
7. Oblicz metryki postawy:
   a. kat kolan,
   b. kat lokci,
   c. dystans nadgarstkow,
   d. rozstaw stop,
   e. polozenie platformy.
8. Okresl faze ruchu:
   OCZEKIWANIE / PRZYGOTOWANIE / KONTAKT / FOLLOW_THROUGH.
9. Jezeli wykryto nowe odbicie:
   a. zapisz rekord odbicia,
   b. zaktualizuj licznik,
   c. przygotuj feedback po odbiciu.
10. Zaktualizuj stan metryk wysylany przez WebSocket.
11. Nanies elementy graficzne na klatke.
12. Wyslij klatke do przegladarki jako MJPEG.
```

### 4.2. Pseudokod oceny postawy

```text
Algorytm EvaluatePosture(points):
1. Jesli brakuje punktow ciala -> zwroc "Nie wykryto sylwetki".
2. Oblicz katy:
   left_knee, right_knee,
   left_elbow, right_elbow.
3. Oblicz:
   hands_ratio = dystans_nadgarstkow / szerokosc_barkow,
   platform_drop = srednie_y_nadgarstkow - srednie_y_lokci.
4. Wygladz wartosci za pomoca EMA.
5. Zastosuj histereze:
   a. kolana zbyt proste,
   b. kolana zbyt nisko,
   c. dlonie za daleko,
   d. lokcie za bardzo ugiete,
   e. platforma za wysoko.
6. Zacznij od wyniku 100.
7. Za kazdy blad odejmij odpowiednia liczbe punktow.
8. Jesli nie ma bledow -> zwroc "Dobra platforma do odbicia dolnego".
9. W przeciwnym razie zwroc liste komunikatow i wynik.
```

---

## 5. Rezultaty i testy

Ta sekcja zostala przygotowana tak, aby mozna bylo uzupelnic konkretne wyniki po wykonaniu testow na docelowym sprzecie.

### 5.1. Test uruchomieniowy

| Element | Wynik | Uwagi |
|---------|-------|-------|
| Instalacja zaleznosci backendu | [UZUPELNIC: OK / blad] | [UZUPELNIC] |
| Start backendu na porcie 8000 | [UZUPELNIC] | [UZUPELNIC] |
| Instalacja zaleznosci frontendu | [UZUPELNIC] | [UZUPELNIC] |
| Start frontendu na porcie 5173 | [UZUPELNIC] | [UZUPELNIC] |
| Logowanie przez Supabase | [UZUPELNIC] | [UZUPELNIC] |
| Polaczenie WebSocket `/ws/metrics` | [UZUPELNIC] | [UZUPELNIC] |

Polecenia uruchomieniowe:

```bash
# Backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend
npm install
npm run dev
```

W repozytorium dostepne sa rowniez skrypty startowe dla Windows i macOS w katalogu `odpalanie/`.

### 5.2. Test analizy postawy

| Scenariusz | Oczekiwane zachowanie | Wynik |
|------------|-----------------------|-------|
| Osoba poza kadrem | Komunikat o braku sylwetki | [UZUPELNIC] |
| Prawidlowa pozycja gotowosci | Zielone kafelki gotowosci | [UZUPELNIC] |
| Zbyt proste kolana | Komunikat "Ugnij kolana" | [UZUPELNIC] |
| Rozlaczone dlonie | Komunikat "Zlacz dlonie" | [UZUPELNIC] |
| Nieprawidlowe lokcie | Komunikat "Wyprostuj lokcie" lub korekta lokci | [UZUPELNIC] |
| Brak widocznych stop | Komunikat o ustawieniu stop w kadrze | [UZUPELNIC] |

**Rys. 2. Przyklad wykrytej sylwetki i kafelkow gotowosci.**

[UZUPELNIC: wstawic zrzut ekranu poprawnej pozycji]

### 5.3. Test wykrywania pilki i kontaktu

| Proba | Liczba rzeczywistych odbic | Liczba odbic wykrytych | Uwagi |
|-------|----------------------------|-------------------------|-------|
| 1 | [UZUPELNIC] | [UZUPELNIC] | [UZUPELNIC] |
| 2 | [UZUPELNIC] | [UZUPELNIC] | [UZUPELNIC] |
| 3 | [UZUPELNIC] | [UZUPELNIC] | [UZUPELNIC] |
| Suma / srednia | [UZUPELNIC] | [UZUPELNIC] | [UZUPELNIC] |

Wnioski z testu kontaktu:

[UZUPELNIC: opisac, czy system poprawnie liczyl odbicia, w jakich sytuacjach pojawialy sie falszywe detekcje lub pominiecia]

### 5.4. Test trybu Dual-Cam

| Element | Wynik |
|---------|-------|
| Wykrycie dwoch kamer | [UZUPELNIC] |
| Poprawne przypisanie front/bok | [UZUPELNIC] |
| Dzialanie fuzji wynikow | [UZUPELNIC] |
| Ocena pracy nog | [UZUPELNIC] |
| Stabilnosc strumienia | [UZUPELNIC] |

**Rys. 3. Widok Dual-Cam z aktywna fuzja biomechaniczna.**

[UZUPELNIC: wstawic zrzut ekranu Dual-Cam albo opisac, ze tryb nie byl testowany]

### 5.5. Test wydajnosci

| Metryka | Wynik |
|---------|-------|
| Srednia liczba FPS strumienia | [UZUPELNIC] |
| Opoznienie obrazu | [UZUPELNIC] |
| Zuzycie CPU | [UZUPELNIC] |
| Zuzycie RAM | [UZUPELNIC] |
| Czas przygotowania pliku wideo | [UZUPELNIC] |

Metodologia pomiaru:

[UZUPELNIC: np. narzedzie systemowe, licznik FPS w aplikacji, pomiar czasu przetwarzania wideo]

### 5.6. Test sterowania glosowego

| Komenda | Oczekiwana akcja | Wynik |
|---------|------------------|-------|
| "rozpocznij analize" | Start analizy | [UZUPELNIC] |
| "zatrzymaj analize" | Stop analizy | [UZUPELNIC] |
| "historia" | Przejscie do historii | [UZUPELNIC] |
| "rozgrzewka" | Przejscie do rozgrzewki | [UZUPELNIC] |
| "panel glowny" | Przejscie do dashboardu | [UZUPELNIC] |

Uwagi:

[UZUPELNIC: skutecznosc rozpoznawania w pomieszczeniu, wplyw halasu, opoznienie]

### 5.7. Test zapisu sesji

| Element | Wynik |
|---------|-------|
| Logowanie uzytkownika | [UZUPELNIC] |
| Token sesji przekazany do backendu | [UZUPELNIC] |
| Zapis rekordu `trainings` | [UZUPELNIC] |
| Zapis rekordu `training_stats` | [UZUPELNIC] |
| Widocznosc danych w historii | [UZUPELNIC] |

Ze wzgledow bezpieczenstwa w sprawozdaniu nie nalezy wpisywac prywatnych kluczy ani tokenow Supabase.

---

## 6. Ograniczenia i wyzwania

1. **Jakosc obrazu** - MediaPipe i YOLO sa wrazliwe na slabe oswietlenie, rozmycie ruchu oraz czesciowe wyjscie zawodnika poza kadr.
2. **Widocznosc stop i kolan** - Ocena ugiecia kolan oraz rozstawu stop wymaga, aby cala sylwetka byla widoczna.
3. **Detekcja pilki** - Pilka moze byc trudna do wykrycia przy szybkim ruchu, niskiej rozdzielczosci lub podobnych kolorach tla.
4. **Pojedyncza kamera** - Jedna perspektywa ogranicza dokladnosc oceny glebokosci ruchu, dlatego tryb Dual-Cam daje pelniejsze dane.
5. **Opoznienie przetwarzania** - Analiza obrazu w czasie rzeczywistym wymaga kompromisu pomiedzy rozdzielczoscia, czestotliwoscia detekcji i plynnoscia strumienia.
6. **Warunki laboratoryjne** - Wyniki moga roznic sie w zaleznosci od sali, oswietlenia, ubrania cwiczacego i ustawienia kamery.
7. **Rozpoznawanie mowy** - Komendy glosowe moga dzialac gorzej w halasie lub przy niewyraznej wymowie.

---

## 7. Wnioski

Projekt Cyber Trener pokazuje, ze z uzyciem ogolnodostepnych technologii mozna stworzyc system wspierajacy nauke techniki sportowej. Aplikacja laczy analize obrazu, reguly biomechaniczne, interfejs webowy, sterowanie glosowe i zapis danych treningowych.

Najwazniejsze osiagniete efekty:

- dzialajaca detekcja sylwetki z wykorzystaniem MediaPipe Pose,
- wykrywanie pilki z uzyciem YOLO i detekcji kolorystycznej,
- ocena podstawowych elementow odbicia dolnego,
- kafelki gotowosci i feedback po odbiciu,
- tryb pojedynczej kamery, Dual-Cam i uploadu wideo,
- rozpoznawanie komend glosowych,
- zapis historii treningow do Supabase.

Na podstawie testow mozna stwierdzic, ze:

[UZUPELNIC: 2-4 zdania po wykonaniu testow, np. czy system dziala stabilnie, ktore elementy sa najtrafniej wykrywane, co wymaga poprawy]

Rekomendowane kierunki dalszego rozwoju:

1. kalibracja progow na wiekszej liczbie nagran z sali,
2. rozdzielenie oceny lokci i rak w osobnych metrykach statystycznych,
3. dokladniejsza ocena rownoleglosci stop,
4. zapis procentowej poprawnosci kazdego elementu techniki,
5. rozbudowa raportow treningowych,
6. dalsza optymalizacja detekcji pilki i wydajnosci live.

---

## 8. Literatura i zrodla

1. MediaPipe Pose - Google Developers: <https://developers.google.com/mediapipe/solutions/vision/pose_landmarker>
2. OpenCV - Open Source Computer Vision Library: <https://opencv.org/>
3. Ultralytics YOLO Documentation: <https://docs.ultralytics.com/>
4. FastAPI Documentation: <https://fastapi.tiangolo.com/>
5. React Documentation: <https://react.dev/>
6. Vite Documentation: <https://vite.dev/>
7. Supabase Documentation: <https://supabase.com/docs>
8. Vosk Speech Recognition Toolkit: <https://alphacephei.com/vosk/>
9. Dokumentacja projektu w repozytorium:
   - `README.md`,
   - `URUCHOMIENIE_I_SZKOLENIE.md`,
   - `KONSULTACJA_TRENERA.md`.

---

## 9. Lista miejsc do uzupelnienia przed oddaniem

- [ ] Data oddania i dane prowadzacego.
- [ ] Sprzet testowy i warunki testow.
- [ ] Zrzuty ekranu: Live Analysis, poprawna pozycja, blad techniczny, ewentualnie Dual-Cam.
- [ ] Wyniki testow uruchomieniowych.
- [ ] Wyniki wykrywania odbic i skutecznosci detekcji.
- [ ] Wyniki wydajnosci.
- [ ] Wnioski koncowe po realnych testach.
- [ ] Ewentualna korekta polskich znakow, jesli dokument bedzie przenoszony do edytora tekstu.
