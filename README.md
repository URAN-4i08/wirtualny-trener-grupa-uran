# Cyber Trener — wirtualny trener odbicia dolnego w siatkówce

**Cyber Trener** to stacjonarny system wspomagający naukę **odbicia piłki sposobem dolnym** w siatkówce. Aplikacja analizuje postawę i moment kontaktu z piłką za pomocą kamery, daje podpowiedzi na żywo oraz krótkie podsumowanie po każdym odbiciu — tak, aby ćwiczący mógł skupić się na ruchu, a nie na patrzeniu w ekran.

Projekt realizowany w ramach przedmiotu KCK (*Cyber trener*) — Politechnika Łódzka / grupa URAN.

---

## Zespół projektowy

| Imię i nazwisko | Nr albumu |
|-----------------|-----------|
| Szymon Zamachowski | 255735 |
| Piotr Michalak | 255654 |
| Krzysztof Olbiński | 255667 |
| Dominik Kwintal | 255647 |

---

## Co robi aplikacja

1. **Wykrywa sylwetkę** (MediaPipe Pose) i **piłkę** (YOLO).
2. **Ocenia postawę na bieżąco** — kolana, łokcie, złączone dłonie, stopy.
3. **Wykrywa moment odbicia** — gdy piłka zbliża się do przedramion.
4. **Pokazuje kafelki gotowości** (zielone / czerwone) przed kontaktem.
5. **Przez 3 sekundy po odbiciu** wyświetla podsumowanie fazy `FOLLOW_THROUGH`.
6. **Obsługuje komendy głosowe** — „rozpocznij”, „zatrzymaj”, nawigacja po panelach.
7. **Opcjonalnie czyta podpowiedzi na głos** (TTS).
8. **Zapisuje sesje** do bazy Supabase (historia, dashboard).

Szczegóły merytoryczne i ustalenia z konsultacji trenera: **[KONSULTACJA_TRENERA.md](./KONSULTACJA_TRENERA.md)**.

Instrukcja uruchomienia krok po kroku: **[URUCHOMIENIE_I_SZKOLENIE.md](./URUCHOMIENIE_I_SZKOLENIE.md)**.

Dokumentacja adaptacji na przedmiot **Podstawy Inżynierii Oprogramowania**:
**[wymagania](./docs/pio/wymagania.md)**,
**[backlog i sprinty](./docs/pio/backlog.md)**,
**[diagramy UML](./docs/pio/uml.md)**.

---

## Stos technologiczny

| Warstwa | Technologie |
|---------|-------------|
| Backend | Python 3.11, FastAPI, Uvicorn, OpenCV |
| Wizja komputerowa | MediaPipe Pose, Ultralytics YOLO (`yolov8n.pt` / `yolov8s.pt`) |
| Logika trenera | `logic/coach_engine.py`, `logic/biomechanics.py` |
| Audio | Vosk (STT), Edge TTS / pyttsx3 / Amazon Polly (TTS) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Recharts |
| Baza danych | Supabase (PostgreSQL) — auth + sesje treningowe |
| Komunikacja | REST API, WebSocket (`/ws/metrics`, `/ws/voice`), strumień MJPEG |

Projekt jest przeznaczony do **pracy offline w sali** (laptop + kamera). Hosting w chmurze nie jest wymagany do prezentacji.

---

## Architektura (skrót)

```
Ćwiczący + piłka
       │
       ▼
  Kamera / plik wideo
       │
       ▼
  server.py  ──► MediaPipe (poza) + YOLO (piłka)
       │              │
       │              ▼
       │     coach_engine.py  — ocena live (EMA, histereza)
       │     biomechanics.py  — fazy, stopy, dual-cam, fuzja
       │
       ├──► WebSocket /ws/metrics  ──► React (Live Analysis)
       ├──► GET /video_feed        ──► podgląd wideo z szkieletem
       ├──► Vosk /ws/voice         ──► komendy głosowe
       └──► Supabase               ──► zapis sesji
```

---

## Struktura repozytorium

```
wirtualny-trener-grupa-uran/
├── server.py                 # Backend: CV, API, WebSocket, zapis sesji
├── logic/
│   ├── coach_engine.py       # Kąty stawów, VolleyballPostureEvaluator
│   └── biomechanics.py       # Analiza front/bok, fazy, stopy, fuzja 2 kamer
├── audio/
│   ├── voice_control.py      # TTS — komunikaty trenera
│   └── speech_recognition.py # Vosk STT
├── frontend/                 # Aplikacja React
│   └── src/
│       ├── pages/            # Dashboard, LiveAnalysis, History, Warmup, Login
│       ├── context/          # Auth, VoiceCommand
│       └── voice/            # Parser komend, capture mikrofonu
├── data/
│   ├── models/               # Model Vosk PL (pobierany przy pierwszym użyciu)
│   └── uploads/              # Wgrane wideo + przetworzone klatki
├── odpalanie/
│   ├── windows/              # Skrypty PowerShell (.ps1)
│   └── macos/                # Skrypty bash (.sh)
├── KONSULTACJA_TRENERA.md    # Ustalenia merytoryczne z trenerem
└── URUCHOMIENIE_I_SZKOLENIE.md
```

---

## Szybki start

Wymagania: Python 3.11, Node.js 20+, kamera lub plik wideo, plik `.env` z kluczami Supabase (patrz [URUCHOMIENIE_I_SZKOLENIE.md](./URUCHOMIENIE_I_SZKOLENIE.md)).

**Windows (PowerShell):**

```powershell
# Terminal 1 — backend
.\odpalanie\windows\start-backend.ps1

# Terminal 2 — frontend
.\odpalanie\windows\start-frontend.ps1
```

**macOS (Terminal):**

```bash
chmod +x odpalanie/macos/*.sh   # tylko przy pierwszym uruchomieniu

./odpalanie/macos/start-backend.sh   # terminal 1
./odpalanie/macos/start-frontend.sh  # terminal 2
```

Aplikacja: **http://localhost:5173**  
API: **http://localhost:8000**

Więcej: [odpalanie/README.md](./odpalanie/README.md)

---

## Główne funkcje interfejsu

| Strona | Opis |
|--------|------|
| **Live Analysis** | Analiza na żywo — kamera, Dual-Cam, upload wideo, kafelki gotowości |
| **Dashboard** | Statystyki zapisanych treningów |
| **Historia** | Lista sesji, szczegóły, usuwanie |
| **Rozgrzewka** | Timer ćwiczeń przed treningiem |
| **Panel głosowy** | Sidebar — nasłuch Vosk, komendy nawigacyjne |

---

## Tryby kamery

| Tryb | Opis |
|------|------|
| Kamera 1 / 2 | Pojedynczy strumień (indeks urządzenia OpenCV) |
| **Dual-Cam** | Laptop (front) + telefon USB (bok) — lepsza ocena kolan i fuzja wyników |

---

## Zmienne środowiskowe (najważniejsze)

Plik `.env` w katalogu głównym (backend) i/lub `frontend/.env`:

```env
# Supabase (auth + zapis treningów)
VITE_SUPABASE_URL=https://twoj-projekt.supabase.co
VITE_SUPABASE_ANON_KEY=twoj-klucz-anon

# Opcjonalnie — gdy frontend i backend na różnych hostach
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_WS_BASE_URL=ws://127.0.0.1:8000

# Backend — model YOLO, TTS, wydajność live
YOLO_MODEL_PATH=yolov8n.pt
VOICE_ENABLED=1
TTS_ENGINE=edge
```

Pełna lista i troubleshooting: [URUCHOMIENIE_I_SZKOLENIE.md](./URUCHOMIENIE_I_SZKOLENIE.md).

---

## Kryteria oceny techniki (skrót)

Ustalone z trenerem — szczegóły w [KONSULTACJA_TRENERA.md](./KONSULTACJA_TRENERA.md):

1. Ugięcie kolan (priorytet)
2. Wyprost łokci
3. Złączone dłonie / platforma dolna
4. Prawidłowe ustawienie stóp

---

## Licencja i repozytorium

Kod projektu studenckiego — grupa URAN, 2025/2026.
