# Cyber Trener — uruchomienie i szkolenie

Przewodnik od instalacji do testu w sali: backend analizuje obraz, frontend pokazuje stream, kafelki gotowości, fazy ruchu i podsumowanie po odbiciu.

Ustalenia merytoryczne (konsultacja trenera): **[KONSULTACJA_TRENERA.md](./KONSULTACJA_TRENERA.md)**.

---

## 1. Wymagania

| Składnik | Wersja / uwagi |
|----------|----------------|
| Python | 3.11 (64-bit) |
| Node.js | 20+ z npm |
| System | Windows (skrypty `.ps1`) lub ręcznie na macOS/Linux |
| Kamera | Wbudowana w laptop lub telefon podłączony kablem USB |
| Internet | Tylko przy pierwszej instalacji (paczki, model YOLO, opcjonalnie Vosk PL) |
| Konto Supabase | Do logowania i zapisu historii treningów |

Projekt jest zaprojektowany do **pracy offline w sali** po wstępnej konfiguracji. Prezentacja odbywa się lokalnie na laptopie (opcjonalnie z rzutorem).

---

## 2. Konfiguracja środowiska

### 2.1 Plik `.env`

Utwórz plik `.env` w **katalogu głównym** projektu:

```env
VITE_SUPABASE_URL=https://twoj-projekt.supabase.co
VITE_SUPABASE_ANON_KEY=twoj-klucz-anon-publiczny
```

Skopiuj te same zmienne do `frontend/.env` (Vite czyta je przy starcie frontendu). Backend (`server.py`) również używa `VITE_SUPABASE_*` do zapisu sesji z tokenem użytkownika.

Opcjonalnie — gdy API nie jest na localhost:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_WS_BASE_URL=ws://127.0.0.1:8000
```

### 2.2 Backend — pierwsze uruchomienie

```powershell
cd D:\STUDIA\wirtualny-trener-grupa-uran
.\start-backend.ps1
```

Skrypt:
- tworzy `.venv`, jeśli go nie ma,
- instaluje `requirements.txt`,
- uruchamia Uvicorn na porcie **8000**.

Przy pierwszym uruchomieniu Ultralytics może pobrać model YOLO (domyślnie `yolov8n.pt`).

### 2.3 Frontend

```powershell
.\start-frontend.ps1
```

Aplikacja: **http://localhost:5173**

---

## 3. Struktura projektu (dla developera)

| Ścieżka | Rola |
|---------|------|
| `server.py` | FastAPI: kamera, wideo, WebSocket, MJPEG, zapis Supabase |
| `logic/coach_engine.py` | `VolleyballPostureEvaluator` — kolana, łokcie, dłonie (EMA + histereza) |
| `logic/biomechanics.py` | Fazy ruchu, stopy, analiza front/bok, fuzja Dual-Cam |
| `audio/voice_control.py` | TTS — odczyt podpowiedzi na głos |
| `audio/speech_recognition.py` | Vosk — rozpoznawanie komend |
| `frontend/src/pages/LiveAnalysis.tsx` | Główny ekran analizy |
| `frontend/src/voice/commandParser.ts` | Mapowanie fraz na akcje |

---

## 4. Pierwsze logowanie i test

1. Otwórz **http://localhost:5173**.
2. Zarejestruj konto lub zaloguj się (Supabase Auth).
3. Przejdź do **Live Analysis**.
4. Wybierz źródło:
   - **Kamera 1 / 2** — pojedyncza kamera,
   - **Dual-Cam** — laptop + telefon (indeksy domyślnie: A=1, B=0 — sprawdź na swoim Macu),
   - **Wideo z komputera** — upload pliku MP4/MOV.
5. Kliknij **Rozpocznij** (lub powiedz „rozpocznij analizę” z włączonym głosem w sidebarze).
6. Obserwuj panel po prawej:
   - kafelki **Stopy / Kolana / Ręce / Nogi**,
   - kąt kolan i licznik odbić,
   - po odbiciu — blok podsumowania (faza `FOLLOW_THROUGH`, ~3 s).

---

## 5. Jak działa feedback

### Dwa poziomy informacji

| Typ | Kiedy | Przykłady |
|-----|-------|-----------|
| **Postawa (ciągła)** | Sylwetka w kadrze | „Ugnij kolana”, „Wyprostuj łokcie”, „Złącz dłonie” |
| **Odbicie (moment kontaktu)** | Piłka blisko przedramion | Ocena techniki, aktualizacja licznika, snapshot do fazy FOLLOW_THROUGH |

### Fazy ruchu (`biomechanics.analizuj_faze`)

```
OCZEKIWANIE → PRZYGOTOWANIE → KONTAKT → FOLLOW_THROUGH (3 s)
```

- **OCZEKIWANIE** — ćwiczący w pozycji, piłka poza strefą kontaktu.
- **PRZYGOTOWANIE** — piłka w locie, kafelki pokazują gotowość.
- **KONTAKT** — wykryto odbicie.
- **FOLLOW_THROUGH** — przez 3 s wyświetlane podsumowanie; ćwiczący może podejść do ekranu po powtórzeniu.

### Kafelki gotowości

| Kafelek | Kryterium (skrót) |
|---------|-------------------|
| Stopy | Rozstawienie względem szerokości barków |
| Kolana | Kąt biodro–kolano–kostka (priorytet z konsultacji) |
| Ręce | Złączone nadgarstki / platforma |
| Nogi | Praca nóg / zamach (pełniej przy Dual-Cam) |

Szczegóły progów: [KONSULTACJA_TRENERA.md](./KONSULTACJA_TRENERA.md).

---

## 6. Komunikaty głosowe (TTS)

Backend może czytać podpowiedzi przez głośniki laptopa — ważne na prezentacji w sali, gdy ćwiczący nie patrzy na ekran.

### Włączenie (zalecane na demo)

Przed startem backendu (PowerShell):

```powershell
$env:VOICE_ENABLED="1"
$env:TTS_ENGINE="edge"
$env:TTS_VOICE="pl-PL-ZofiaNeural"
.\start-backend.ps1
```

Lub dodaj `VOICE_ENABLED=1` do pliku `.env`.

### Opcjonalnie — Amazon Polly (głosy Ivona)

```powershell
$env:VOICE_ENABLED="1"
$env:TTS_ENGINE="polly"
$env:TTS_VOICE="Ewa"
$env:AWS_ACCESS_KEY_ID="..."
$env:AWS_SECRET_ACCESS_KEY="..."
$env:AWS_DEFAULT_REGION="eu-central-1"
```

| Zmienna | Domyślnie | Opis |
|---------|-----------|------|
| `VOICE_ENABLED` | `0` | `1` = włącz TTS |
| `TTS_ENGINE` | `edge` | `edge`, `polly`, `pyttsx3` |
| `VOICE_COOLDOWN_SEC` | `5` | Min. odstęp między tym samym komunikatem |

---

## 7. Sterowanie głosowe (Vosk)

W sidebarze: **Włącz nasłuch**. Przy pierwszym użyciu backend pobierze model polski Vosk (~50 MB) do `data/models/`.

**Brave:** wbudowane Web Speech API nie działa — aplikacja używa Vosk z backendu. Zezwól na mikrofon w ustawieniach strony.

| Komenda | Akcja |
|---------|--------|
| „rozpocznij analizę” / „zacznij trening” | Start analizy (Live Analysis) |
| „zatrzymaj analizę” / „koniec analizy” | Stop analizy |
| „panel” / „strona główna” | Dashboard |
| „analiza” | Live Analysis |
| „historia” | Historia treningów |
| „rozgrzewka” | Rozgrzewka |

---

## 8. Tryb Dual-Cam (laptop + telefon)

1. Podłącz telefon kablem USB (macOS: Continuity Camera / aplikacja typu Camo / DroidCam — zależnie od setupu).
2. W Live Analysis kliknij **Dual-Cam**.
3. Backend uruchamia dwa strumienie i **fuzję** wyników (`fuzja_sensorow`).
4. Pasek „Fuzja obu kamer” pojawia się w panelu bocznym.

Jeśli indeksy kamer są zamienione, edytuj parametry w `LiveAnalysis.tsx` lub endpoint `/api/source/camera-dual` w `server.py`.

Druga kamera jest **opcjonalna** — bez niej system ocenia kolana z widoku frontowego (mniej precyzyjnie).

---

## 9. Upload wideo — dlaczego jest opóźnienie

Plik wideo jest **najpierw analizowany w tle**. Backend zapisuje klatki z nałożonym szkieletem i metrykami do `data/uploads/processed/`. Dopiero po 100% postępu można kliknąć **Rozpocznij** — odtwarzanie jest wtedy płynne, bez obciążania CPU MediaPipe/YOLO w czasie rzeczywistym.

---

## 10. Wydajność kamery live

Live działa w trybie oszczędnym: analiza co N klatek, obniżona rozdzielczość dla AI.

Jeśli obraz laguje, przed startem backendu:

```powershell
$env:LIVE_STREAM_FPS="15"
$env:LIVE_STREAM_WIDTH="720"
$env:LIVE_ANALYSIS_WIDTH="480"
$env:LIVE_POSE_EVERY_N_FRAMES="4"
$env:LIVE_BALL_EVERY_N_FRAMES="8"
.\start-backend.ps1
```

| Zmienna | Znaczenie |
|---------|-----------|
| `LIVE_STREAM_FPS` | Klatki wysyłane do przeglądarki |
| `LIVE_STREAM_WIDTH` | Szerokość obrazu w UI |
| `LIVE_ANALYSIS_WIDTH` | Szerokość dla MediaPipe/YOLO |
| `LIVE_POSE_EVERY_N_FRAMES` | Co którą klatkę liczyć pozę |
| `LIVE_BALL_EVERY_N_FRAMES` | Co którą klatkę szukać piłki |

---

## 11. Typowe problemy

### Backend nie startuje

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend — błąd paczek

```powershell
cd frontend
npm install
npm run dev
```

### Brak zapisu treningu

- Sprawdź `.env` — `VITE_SUPABASE_URL` i `VITE_SUPABASE_ANON_KEY`.
- Musisz być **zalogowany** — backend potrzebuje tokenu sesji użytkownika.

### Kamera zajęta

Zamknij Teams, Zoom, Discord. Uruchom backend ponownie.

### „Nie wykryto sylwetki”

- Osoba poza kadrem, zbyt słabe światło lub zasłonięte kolana / ręce.
- Stały kadr — unikaj nagłań z szybko zmieniającym się kątem kamery.

### Brak detekcji piłki

Model YOLO (`sports ball`) wymaga widocznej piłki i dobrego oświetlenia. Ustaw `YOLO_MODEL_PATH` na lokalny plik `.pt`, jeśli używasz innej wersji modelu.

### Komunikaty zbyt czułe / za rzadkie

Progi live (wygładzone): `logic/coach_engine.py` — klasa `VolleyballPostureEvaluator`.

Progi faz i stóp: `logic/biomechanics.py` — sekcja konfiguracji na górze pliku.

Moment odbicia: `server.py` — klasa `BallContactTracker`.

### macOS — indeksy kamer

Sprawdź, który indeks to telefon, który laptop:

```python
import cv2
for i in range(4):
    cap = cv2.VideoCapture(i)
    print(i, cap.isOpened())
    cap.release()
```

---

## 12. Scenariusz prezentacji w sali (~2 min)

1. Laptop podłączony do rzutnika (opcjonalnie).
2. Start backendu z `VOICE_ENABLED=1`.
3. Start frontendu, logowanie.
4. Live Analysis → Kamera lub Dual-Cam.
5. Sidebar → włącz nasłuch głosowy.
6. Ćwiczący mówi: **„Rozpocznij analizę”**.
7. Podrzuca piłkę, odbija — **nie patrzy na ekran** podczas ruchu.
8. Po odbiciu — 3 s podsumowania na ekranie / głos TTS.
9. Ćwiczący podchodzi, sprawdza kafelki, wraca na kolejną próbę.
10. **„Zatrzymaj analizę”** → Dashboard / Historia.

---

## 13. Dopracowanie logiki (bieżące prace zespołu)

Zgodnie z [KONSULTACJA_TRENERA.md](./KONSULTACJA_TRENERA.md) — bez pochylenia tułowia na tym etapie:

- [ ] Kalibracja progów kolan i łokci na nagraniach z sali
- [ ] Osobne kafelki Łokcie / Ręce w UI
- [ ] Lepsza ocena równoległości stóp
- [ ] % poprawności per element w statystykach sesji
- [ ] Wskaźnik fazy ruchu w interfejsie (style CSS już w `index.css`)
- [ ] Baner zachęty do Dual-Cam przy jednej kamerze

---

## 14. macOS / Linux (bez skryptów .ps1)

**Backend:**

```bash
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**

```bash
cd frontend && npm install && npm run dev
```

---

*Ostatnia aktualizacja: czerwiec 2026 — Grupa Uran*
