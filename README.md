# 🏐 Cyber Trener - AI Volleyball Coach (Odbicie Dolne)

**Cyber Trener** to system analizy cwiczenia skupiony na nauce i doskonaleniu **odbicia piłki sposobem dolnym** w siatkówce.
 Dzięki wykorzystaniu dwóch zewnętrznych (smartfony) podłączonych przewodowo oraz algorytmów analizujacych ruch, system analizuje technikę zawodnika w czasie rzeczywistym.

---

## 👥 Zespół projektowy
* **Szymon Zamachowski (255735)** 
* **Piotr Michalak (255654)** 
* **Krzysztof Olbiński (255667)**
* **Dominik Kwintal (255647)** 

---

## 🛠 Stos technologiczny
* **Język:** Python 3.11+
* **Interfejs (GUI):** React + CSS 
* **Wizja komputerowa:** * **MediaPipe:** Śledzenie szkieletu i analiza kątów stawowych (kolana, łokcie).
  * **YOLO v11:** Błyskawiczna detekcja piłki i inicjacja algorytmów śledzenia.
* **Audio & Głos:**
  * **Vosk:** Lekkie, lokalne rozpoznawanie komend głosowych (STT).
  * **pyttsx3:** System komunikatów głosowych trenera (TTS) działający offline.
* **Baza danych:** SQLite (archiwizacja progresu, sesji treningowych i błędów).
* **Wizualizacja:** Matplotlib (generowanie wykresów radarowych i kołowych skuteczności).

---

## 📁 Struktura folderów
