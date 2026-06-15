# Cyber Trener - wysokopoziomowe diagramy UML

Diagramy zapisano w formacie Mermaid, aby mozna je bylo wyswietlic bezposrednio w GitHubie albo skopiowac do narzedzia generujacego obrazki do prezentacji.

## 1. Diagram komponentow

```mermaid
flowchart LR
    User["Cwiczacy"] --> Camera["Kamera / plik wideo"]
    User --> Microphone["Mikrofon"]

    Camera --> Backend["Backend FastAPI"]
    Microphone --> VoiceWs["WebSocket /ws/voice"]
    VoiceWs --> Backend

    Backend --> Vision["backend/vision.py<br/>MediaPipe + YOLO"]
    Vision --> Coach["logic/coach_engine.py<br/>ocena postawy"]
    Vision --> Biomechanics["logic/biomechanics.py<br/>fazy + Dual-Cam"]
    Coach --> Metrics["Stan metryk live"]
    Biomechanics --> Metrics

    Metrics --> MetricsWs["WebSocket /ws/metrics"]
    Backend --> VideoFeed["MJPEG /video_feed"]
    Backend --> RestApi["REST API /api/*"]

    MetricsWs --> Frontend["Frontend React"]
    VideoFeed --> Frontend
    RestApi --> Frontend

    Frontend --> SupabaseAuth["Supabase Auth"]
    Backend --> SupabaseDb["Supabase PostgreSQL<br/>trainings, training_stats"]
    SupabaseAuth --> Frontend
```

## 2. Diagram klas domeny i logiki

```mermaid
classDiagram
    class VolleyballPostureEvaluator {
        -float ema_alpha
        -bool _warn_knees_straight
        -bool _warn_knees_low
        -bool _warn_elbows
        -bool _warn_hands
        -bool _warn_platform
        +evaluate(punkty_ciala) tuple
        -_ema(prev, value) float
    }

    class CoachEngine {
        +calculate_angle(a, b, c) float
        +check_volleyball_position(punkty_ciala) tuple
    }

    class Biomechanics {
        +analizuj_front(punkty, pilka, frame_shape) dict
        +analizuj_bok(punkty, wrist_tracker) dict
        +analizuj_stopy(punkty) dict
        +analizuj_faze(dane_front, dane_bok, dystans_pilka) dict
        +fuzja_sensorow(dane_front, dane_bok) dict
    }

    class WristTrajectoryTracker {
        -deque _buf
        +update(punkty) void
        +wykryj_zamach() tuple
        +reset() void
    }

    class TrainingSession {
        +start()
        +stop()
        +record_contact()
        +summary()
    }

    class SupabaseTrainingRepository {
        +save_training_session(user_id, source, start_time, end_time, stats, access_token)
    }

    CoachEngine --> VolleyballPostureEvaluator
    Biomechanics --> WristTrajectoryTracker
    TrainingSession --> Biomechanics
    TrainingSession --> VolleyballPostureEvaluator
    TrainingSession --> SupabaseTrainingRepository
```

## 3. Diagram sekwencji - analiza jednego odbicia

```mermaid
sequenceDiagram
    participant U as Cwiczacy
    participant F as Frontend React
    participant B as Backend FastAPI
    participant V as Vision Pipeline
    participant L as Logika domenowa
    participant S as Supabase

    U->>F: Klik "Rozpocznij" lub komenda glosowa
    F->>B: POST /api/session/start
    B-->>F: Sesja aktywna

    loop Co klatke
        B->>V: Klatka z kamery / wideo
        V->>L: Punkty ciala + pozycja pilki
        L-->>B: Faza, gotowosc, wynik, feedback
        B-->>F: /ws/metrics
        B-->>F: /video_feed
    end

    U->>F: Stop analizy
    F->>B: POST /api/session/stop
    B->>S: Zapis trainings + training_stats
    S-->>B: Potwierdzenie zapisu
    B-->>F: Podsumowanie sesji
```

## 4. Diagram modelu danych Supabase

```mermaid
erDiagram
    auth_users ||--o{ trainings : owns
    trainings ||--o| training_stats : has

    auth_users {
        uuid id PK
        string email
    }

    trainings {
        uuid id PK
        uuid user_id FK
        timestamptz start_time
        timestamptz end_time
        text source
        numeric overall_score
        text status
    }

    training_stats {
        uuid id PK
        uuid training_id FK
        integer total_contacts
        numeric avg_knee_angle
        integer posture_warnings_count
        numeric avg_contact_score
    }
```

## 5. Mapowanie diagramow na pliki projektu

| Element diagramu | Pliki w repozytorium |
| --- | --- |
| Backend FastAPI | `server.py`, `backend/app.py`, `backend/routes.py` |
| Vision Pipeline | `backend/vision.py`, `backend/streams.py` |
| Logika domenowa | `logic/coach_engine.py`, `logic/biomechanics.py` |
| Sesja treningowa | `backend/training_session.py`, `backend/state.py` |
| Frontend React | `frontend/src/pages/LiveAnalysis.tsx`, `frontend/src/components/live/*` |
| Sterowanie glosowe | `audio/speech_recognition.py`, `frontend/src/voice/*` |
| Supabase | `backend/supabase_client.py`, `frontend/src/lib/trainingData.ts` |

