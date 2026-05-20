# Cyber Trener - AI Volleyball Coach (Odbicie Dolne)

**Cyber Trener** to system analizy ćwiczenia skupiony na nauce i doskonaleniu odbicia piłki sposobem dolnym w siatkówce. Dzięki wykorzystaniu kamer zewnętrznych oraz algorytmów analizujących ruch system ocenia technikę zawodnika w czasie rzeczywistym.

## Zespół projektowy

* **Szymon Zamachowski (255735)**
* **Piotr Michalak (255654)**
* **Krzysztof Olbiński (255667)**
* **Dominik Kwintal (255647)**

## Stos technologiczny

* **Język:** Python 3.11+
* **Interfejs:** React + CSS
* **Backend:** FastAPI + WebSocket
* **Wizja komputerowa:**
  * **MediaPipe:** śledzenie szkieletu i analiza kątów stawowych, głównie kolan i łokci.
  * **YOLO / Ultralytics:** detekcja piłki i wykrywanie momentu odbicia.
* **Audio i głos:**
  * **Vosk:** lokalne rozpoznawanie komend głosowych.
  * **pyttsx3:** offline'owy system komunikatów głosowych trenera.
* **Baza danych:** SQLite do archiwizacji progresu, sesji treningowych i błędów.

## Tryb analizy live

Aktualna implementacja zakłada:

* kamera `0` jako obowiązkowa kamera boczna ustawiona pod kątem 45°,
* kamera `1` jako opcjonalna kamera frontowa,
* analizę pozycji przed przyjęciem i w trakcie przyjęcia,
* ocenę słabych punktów wykonania ćwiczenia,
* wykrywanie momentu odbicia piłki przez YOLO na podstawie odległości piłki od nadgarstków,
* analizę ciała przez MediaPipe,
* tryb testowy UI pozostawiony jako mock, bez wymuszania podpięcia backendu.

## Struktura folderów

* `frontend/` - interfejs React.
* `server.py` - backend FastAPI dla strumieni kamer i metryk live.
* `vision/` - moduły MediaPipe, YOLO i obsługi kamer.
* `logic/` - logika oceny techniki odbicia dolnego.
* `audio/` - moduły audio.
* `data/` - dane i modele.
