# Cyber Trener - szkolenie uruchomienia i testowania

Ten dokument prowadzi od zera do lokalnego testu aplikacji: backend analizuje obraz, frontend pokazuje stream, podpowiedzi postawy i ocenę odbicia.

## 1. Co jest potrzebne

Na komputerze powinny być:

- Node.js 24+ z npm.
- Python 3.11 64-bit.
- Kamera internetowa albo plik wideo z ćwiczeniem.
- Dostęp do internetu przy pierwszej instalacji paczek i pobraniu modelu YOLO.

W tym środowisku zostało już przygotowane:

- Python 3.11.9 dla użytkownika.
- Lokalne środowisko `.venv`.
- Paczki backendu z `requirements.txt`.
- Paczki frontendu przez `npm ci`.
- Model YOLO `yolov8s.pt` pobrany do katalogu projektu.

## 2. Najważniejsze foldery

- `frontend` - strona React/Vite.
- `server.py` - backend FastAPI łączący kamerę/wideo, MediaPipe, YOLO i logikę trenera.
- `logic/coach_engine.py` - reguły oceny pozycji: kolana, dłonie, łokcie.
- `vision/analysis_video.py` - starszy skrypt demonstracyjny OpenCV.
- `audio/voice_control.py` - miejsce na przyszłe sterowanie/komunikaty głosowe.

## 3. Uruchamianie lokalne

Otwórz dwa okna terminala w katalogu projektu:

```powershell
cd D:\STUDIA\wirtualny-trener-grupa-uran
```

W pierwszym oknie uruchom backend:

```powershell
.\start-backend.ps1
```

Backend powinien działać pod:

```text
http://localhost:8000
```

W drugim oknie uruchom frontend:

```powershell
.\start-frontend.ps1
```

Frontend powinien działać pod:

```text
http://localhost:5173
```

## 4. Test live view

1. Wejdź na `http://localhost:5173`.
2. Przejdź do `Live Analysis`.
3. Wybierz `Kamera` albo `Wideo z komputera`.
4. Przy pliku wideo poczekaj, aż pasek przygotowania dojdzie do 100%.
5. Kliknij `Rozpocznij`.
6. Obserwuj:
   - status analizy,
   - podpowiedź postawy,
   - ocenę odbicia,
   - kąt ugięcia kolan,
   - skuteczność pozycji.

## 5. Jak działa feedback

Aplikacja pokazuje dwa typy informacji:

- Podpowiedź postawy działa stale, gdy wykryto sylwetkę. Przykłady: `Ugnij kolana!`, `Zlacz dlonie!`, `Wyprostuj lokcie!`.
- Ocena odbicia pojawia się tylko wtedy, gdy YOLO wykryje piłkę blisko nadgarstków.

To odpowiada ustaleniu: stale pomagamy poprawiać postawę, ale samo odbicie oceniamy tylko w momencie kontaktu z piłką.

### Komunikaty głosowe (TTS)

Backend może czytać podpowiedzi na głos przez głośniki laptopa (np. gdy kamera stoi dalej od zawodnika).

Domyślnie działa polski głos neuralny (Edge TTS). Aby użyć głosów Ivona (Ewa, Maja, Jacek) przez Amazon Polly:

```bash
export VOICE_ENABLED=1
export TTS_ENGINE=polly
export TTS_VOICE=Ewa
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=eu-central-1
```

Opcjonalne zmienne:

```bash
export VOICE_COOLDOWN_SEC=5   # nie powtarzaj tej samej podpowiedzi częściej niż co 5 s
export TTS_ENGINE=edge        # domyślnie, bez kluczy AWS
export TTS_VOICE=pl-PL-ZofiaNeural
export VOICE_ENABLED=0        # wyłączenie mowy
```

Komunikaty są czytane przy zmianie podpowiedzi, np. `Ugnij kolana!`, `Złącz dłonie!`, `Wyprostuj łokcie!`.

### Sterowanie głosowe UI

**Brave:** wbudowane rozpoznawanie mowy przeglądarki nie działa (blokuje Google). Aplikacja używa lokalnego **Vosk** na backendzie — w sidebarze widać „Nasłuch (Vosk lokalny)”.

Przy pierwszym uruchomieniu backend pobierze model PL (~50 MB) do `data/models/`. Wymagany działający backend na porcie 8000.

| Komenda | Akcja |
|---------|--------|
| `rozpocznij` | Start analizy (na stronie Live Analysis) |
| `zatrzymaj` | Stop analizy |
| `panel` | Przejście do Dashboard (panel główny) |
| `analiza` | Przejście do Live Analysis |

W Brave: ikona lwa → ustawienia strony → **Mikrofon: Zezwól**. W panelu bocznym pojawi się „Słyszę: …” gdy fraza została rozpoznana.

## 5a. Dlaczego upload wideo startuje z opóźnieniem

Plik wideo jest najpierw analizowany w tle. Backend zapisuje gotowe klatki z narysowanym szkieletem, piłką i metrykami, a dopiero po zakończeniu przygotowania frontend pozwala kliknąć `Rozpocznij`.

Dzięki temu odtwarzanie gotowego pliku jest dużo płynniejsze, bo podczas oglądania backend nie musi już liczyć MediaPipe i YOLO dla każdej klatki na żywo.

## 6. Konfiguracja pod hosting

Frontend nie ma już wpisanego na stałe `localhost`. Do hostingu ustaw:

```env
VITE_API_BASE_URL=https://adres-twojego-backendu
VITE_WS_BASE_URL=wss://adres-twojego-backendu
```

Lokalny przykład jest w:

```text
frontend/.env.example
```

Backend ma dodatkowe zmienne:

```env
ALLOWED_ORIGINS=https://adres-twojego-frontendu
YOLO_MODEL_PATH=yolov8s.pt
```

Gdy będzie własny model, ustaw `YOLO_MODEL_PATH` na ścieżkę do pliku `.pt`.

## 7. Typowe problemy

### Kamera live laguje albo zatrzymuje obraz

Live camera działa w trybie wydajnościowym: obraz jest wysyłany płynniej, a ciężka analiza AI jest robiona co kilka klatek na zmniejszonej rozdzielczości.

Możesz dodatkowo obniżyć obciążenie przez zmienne środowiskowe przed startem backendu:

```powershell
$env:LIVE_STREAM_FPS="15"
$env:LIVE_STREAM_WIDTH="720"
$env:LIVE_ANALYSIS_WIDTH="480"
$env:LIVE_POSE_EVERY_N_FRAMES="4"
$env:LIVE_BALL_EVERY_N_FRAMES="8"
.\start-backend.ps1
```

Znaczenie:

- `LIVE_STREAM_FPS` - ile klatek na sekundę wysyła backend do strony.
- `LIVE_STREAM_WIDTH` - szerokość obrazu wysyłanego do UI.
- `LIVE_ANALYSIS_WIDTH` - szerokość obrazu używanego do MediaPipe/YOLO.
- `LIVE_POSE_EVERY_N_FRAMES` - co którą klatkę liczyć pozycję.
- `LIVE_BALL_EVERY_N_FRAMES` - co którą klatkę szukać piłki przez YOLO.

Niższe wartości rozdzielczości i rzadsza analiza dają płynniejszy obraz, ale feedback może być mniej częsty.

### Frontend się nie uruchamia

Wejdź do `frontend` i odtwórz paczki:

```powershell
cd frontend
npm ci
npm run dev
```

### Backend mówi, że nie widzi kamery

Sprawdź, czy kamera nie jest używana przez Teams/Zoom/Discord. Potem uruchom backend ponownie.

### Brak detekcji piłki

Model `yolov8s.pt` jest ogólny. Działa na klasie `sports ball`, ale dla siatkówki może wymagać dobrego światła i widocznej piłki. Docelowo warto dodać własny model YOLO i ustawić `YOLO_MODEL_PATH`.

### Komunikaty są zbyt czułe albo za rzadkie

Progi są w:

```text
logic/coach_engine.py
```

Moment odbicia jest w:

```text
server.py
```

Obecnie piłka jest uznawana za blisko nadgarstków, gdy odległość jest mniejsza niż `100` pikseli.

## 8. Co testować na prezentacji

Minimalny scenariusz:

1. Start backendu.
2. Start frontendu.
3. Wejście w `Live Analysis`.
4. Uruchomienie kamery albo wrzucenie pliku.
5. Pokazanie komunikatu `Nie wykryto sylwetki`, gdy nie ma osoby.
6. Pokazanie podpowiedzi postawy przy widocznej osobie.
7. Pokazanie oceny odbicia przy piłce blisko rąk.

## 9. Następne etapy projektu

- Sterowanie głosowe UI: komendy w przeglądarce (Chrome/Edge, `VoiceCommandProvider` w frontendzie).
- TTS podpowiedzi trenera: `audio/voice_control.py`.
- Dodać własny model YOLO dla piłki siatkowej.
- Dodać historię analiz i bazę SQLite.
- Dodać tryb dwóch kamer.
- Dopasować progi do realnych nagrań zespołu.
