# Prompt do generowania UI — Cyber-Trener Siatkarz

Skopiuj całą sekcję **„PROMPT (kopia do narzędzia)”** poniżej do narzędzia generującego UI (v0, Galileo, Figma AI itd.).  
Po wygenerowaniu screenów wróć do implementacji w stacku: **React 19 + TypeScript + Vite + Tailwind CSS**.

> Stary folder `ui_design/` jest **nieaktualny** — projektuj od zera według tego dokumentu.

---

## PROMPT (kopia do narzędzia)

```
Zaprojektuj kompletny, spójny interfejs aplikacji webowej „Cyber-Trener Siatkarz” — stacjonarny wirtualny trener do nauki odbicia dolnego w siatkówce. Aplikacja działa na laptopie (MacBook Air, ~1440–2560px szerokości) w sali treningowej. Ćwiczący NIE patrzy na ekran podczas odbicia — podchodzi po 3 sekundach, żeby sprawdzić feedback. UI musi być SCHLUDNE, czytelne, bez przeładowania — łatwa nawigacja ważniejsza niż efektowność.

### Stack implementacyjny (projektuj pod to)
- React 19 + TypeScript + Vite + Tailwind CSS
- Ciemny motyw, glassmorphism lekki (nie przesadzony)
- Ikony: lucide-react
- Wykresy: recharts (słupki, donut — czytelne, nie ozdobne)
- Język UI: WYŁĄCZNIE polski

### Tożsamość marki
- Nazwa produktu: **Cyber-Trener Siatkarz**
- Podtytuł (opcjonalnie): „Wirtualny trener odbicia dolnego”
- Logo: NIE generuj nowego logo. Użyj istniejącego favicon — geometryczna fioletowa gwiazda/błyskawica (plik favicon.svg w projekcie, akcent #863bff). W sidebarze i loginie: mała ikona favicon + wordmark tekstowy.
- Styl: sportowy ale CZYSTY — paleta **granat + pomarańcz** (nie neon cyberpunk)
  - Tło główne: granat głęboki #0B1426 lub #0F1B33
  - Powierzchnie kart: #152238 / #1A2A45 z przezroczystością, blur 12px, obramowanie white/10%
  - Akcent primary (CTA, aktywne): pomarańcz #F97316 / #FB923C
  - Akcent secondary (informacje, linki): jasny błękit #38BDF8 lub fiolet favicon #863bff oszczędnie
  - Sukces: zielony #22C55E | Błąd: czerwony #EF4444 | Ostrzeżenie: bursztyn #F59E0B
- Typografia: nagłówki Space Grotesk, treść Inter
- Zaokrąglenia: karty rounded-2xl, przyciski rounded-xl
- Stopka na każdym ekranie aplikacji (mały tekst): „Grupa Uran — Szymon Zamachowski 255735 · Piotr Michalak 255654 · Krzysztof Olbiński 255667 · Dominik Kwintal 255647”

### Layout globalny
- Sidebar: zwijany + hamburger. Domyślnie widoczny na Dashboard, Historia, Rozgrzewka. Na Live Analysis i Login — sidebar UKRYTY (więcej miejsca na wideo).
- Sidebar zawiera: logo + nazwa, nawigacja (Panel, Rozgrzewka, Analiza, Historia), przycisk głosu (Włącz/Wyłącz) + status nasłuchu, link „Komendy głosowe”, na DOLE sekcja profilu (avatar inicjał, imię, wyloguj).
- Główna treść: padding 24px, max-width tam gdzie sensowne (dashboard), Live Analysis — pełna szerokość.

---

## EKRANY DO ZAPROJEKTOWANIA (wszystkie)

### 1. Login
- Split layout: lewa połowa — grafika siatkówki (abstrakcyjna, granat+pomarańcz, bez stockowych zdjęć ludzi); prawa — formularz
- Pola: Email, Hasło, przycisk „Zaloguj się”, link „Załóż konto”
- Favicon + „Cyber-Trener Siatkarz”
- Styl spójny z aplikacją (NIE osobny zinc/gray theme)
- Stan błędu: komunikat pod formularzem

### 2. Register
- Jak Login, pola: Imię, Nazwisko, Email, Hasło, „Zarejestruj się”

### 3. Dashboard (Panel główny)
Cel: szybki przegląd postępu. SCHLUDNIE — 4 KPI u góry, potem wykresy.

**KPI cards (rząd 4):**
- Liczba treningów
- Średni wynik (%)
- Najlepszy wynik (%)
- Łączna liczba odbić

**Sekcja główna (2 kolumny):**
- LEWO: Wykres słupkowy „Poprawność elementów techniki” — 5 słupków: Kolana, Łokcie, Ręce, Stopy, Nogi (%). Kolory: zielony/pomarańcz/czerwony wg wartości. Pod wykresem krótka legenda.
- PRAWO: Donut „Średnia skuteczność serii” + duża liczba % w środku

**Dół:**
- Karta „Ostatni trening” — data, źródło (kamera/plik), czas, wynik, odbicia
- Karta „Do poprawy” — trenerowy komunikat np. „Najczęściej: ugięcie kolan” + liczba ostrzeżeń
- Przycisk CTA pomarańcz: „Przejdź do analizy”

Dane przykładowe w mockupie: średni 72%, kolana 65%, łokcie 80%, ręce 78%, stopy 70%, nogi 85%.

### 4. Historia treningów
- Nagłówek + opis
- TABELA (zostaje tabela, nie karty): kolumny Data | Źródło | Czas | Wynik | Odbicia | Problem | Akcje
- Wiersz zaznaczony — podświetlenie pomarańcz/granat
- Prawy panel „Podsumowanie serii” (sticky): po wyborze wiersza — wynik, odbicia, kąt kolan, ostrzeżenia, mini słupki 5 elementów (%), główny problem
- Przycisk usuń (ikona kosza)
- Stan pusty: ilustracja + „Brak zapisanych treningów”

### 5. Rozgrzewka
- Wybór planu: Krótka / Standardowa / Mocna (3 karty)
- Aktywne ćwiczenie: DUŻA ilustracja ćwiczenia (line-art siatkówka, granat+pomarańcz) + nazwa + instrukcja PL
- Timer odliczający (duży, centralny) — MUSI zostać
- Pasek postępu serii, przyciski Pauza / Reset / Dalej
- Po zakończeniu: „Przejdź do analizy” (CTA)
- Ćwiczenia przykładowe: Krążenia ramion, Przysiady techniczne, Lekkie odbicia

### 6. Komendy głosowe (podstrona)
- Prosta strona referencyjna — tabela komend PL → akcja
- Komendy: „rozpocznij analizę”, „zatrzymaj analizę”, „panel”, „analiza”, „historia”, „rozgrzewka”
- Krótka instrukcja: mikrofon laptopa, Brave + Vosk
- Link powrotu

### 7–15. Live Analysis — EKRAN KLUCZOWY (wiele stanów)

**Layout stały:**
- Górny pasek: hamburger, tytuł „Analiza na żywo”, status połączenia, timer sesji (opcjonalnie)
- GŁÓWNY OBSZAR: wideo zajmuje ~70–75% szerokości (lewa/strona główna)
- PRAWY PANEL (~25%): statystyki — zwarty, przewijalny
- Banery/podpowiedzi NA WIDEO ale NIE zasłaniające całości:
  - Górny lewy: badge LIVE (czerwona kropka pulsująca) + faza ruchu
  - Górny prawy lub dolny środek: baner trenerowy (pomarańczowy/obramowanie) — np. „Ugnij kolana!” — DUŻY, czytelny z 2m
  - Stepper faz poziomy (nad wideo lub pod nagłówkiem wideo): Oczekiwanie → Przygotowanie → Kontakt → Podsumowanie

**Kontrolki nad wideo (pod nagłówkiem):**
- Przyciski źródła: Kamera (front — telefon) | Kamera (bok — laptop) | Dual-Cam | Wideo z pliku
- PRZED startem analizy: żółty/info baner „Podłącz telefon i wybierz Dual-Cam dla dokładniejszej oceny kolan” — ZNIKA po kliknięciu „Rozpocznij”
- Przycisk główny pomarańcz: „Rozpocznij” / czerwony „Przerwij analizę”

**Prawy panel — stałe widżety:**
1. **5 kafelków gotowości** (siatka, nie 4): Stopy | Kolana | Łokcie | Ręce | Nogi — ✓ zielony / ✗ czerwony, etykieta pod spodem
2. **Skuteczność** — mały donut + % 
3. **Kolana** — duży kąt np. 142° + pasek
4. **Odbicia** — licznik
5. **Rozstaw stóp** — poziomy pasek z markerem (foot spread bar)
6. Dual-Cam only: pasek „Fuzja kamer” 0–100

**Mapowanie danych (pod implementację):**
- postureWarnings → baner na wideo
- gotowoscPrzedOdbiciem: stopa_ok, kolana_ok, lokcie_ok (nowe), platforma_ok (Ręce), ruch_ok (Nogi)
- kneeAngle, score, totalContacts, fazaRuchu, feedbackFazy, rozstawienieStop
- fuzjaOcena (dual), komunikatKolana, typOdbicia

#### Stan 7a: Standby
- Placeholder wideo (ikona kamery), tekst „Wybierz kamerę i rozpocznij analizę”
- Baner sugestii Dual-Cam widoczny

#### Stan 7b: Analiza — dobra postawa
- Wideo z nałożonym szkieletem (symuluj półprzezroczyste linie)
- Wszystkie 5 kafelków zielone
- Baner: „Pozycja wygląda dobrze” (zielony)
- Faza: OCZEKIWANIE lub PRZYGOTOWANIE

#### Stan 7c: Analiza — błędy postawy
- Baner trenerowy: „Ugnij kolana! | Wyprostuj łokcie!” (pomarańcz/czerwony)
- Kafelki Kolana i Łokcie czerwone, reszta zielona

#### Stan 7d: Przygotowanie (piłka w locie)
- Faza PRZYGOTOWANIE podświetlona w stepperze (pomarańcz)
- Baner: „Piłka leci! Kolana OK, złącz dłonie”

#### Stan 7e: Kontakt
- Faza KONTAKT — zielony puls w stepperze
- Krótki flash na wideo

#### Stan 7f: FOLLOW_THROUGH (po odbiciu) — WAŻNY
- Wideo WYSZARZONE (overlay czarny 60%)
- KARTA NA ŚRODKU wideo (duża, rounded-2xl):
  - Nagłówek: „Podsumowanie odbicia”
  - Trenerowy feedback: „Dobre odbicie! Wskazówka: popraw ugięcie kolan”
  - 5 kafelków stanu w momencie odbicia
  - WYNIK: 78/100
  - **Odliczanie 3… 2… 1** (duże cyfry, pomarańcz) — „Podejdź do ekranu”
- Prawy panel zsynchronizowany z kartą

#### Stan 7g: Brak sylwetki
- Baner: „Stań w kadrze kamery”
- Kafelki wyszarzone / „—”

#### Stan 7h: Przetwarzanie wideo
- Pasek postępu „Przygotowuję analizę… 67%”
- Bez wideo

#### Stan 7i: Dual-Cam aktywny
- Dwa obrazy OBOK SIEBIE (50/50) w obszarze wideo: „Front” | „Bok”
- Pasek fuzji w panelu

#### Stan 7j: Błąd połączenia
- Czerwony alert u góry: „Brak połączenia z serwerem analizy”

### 16. Modal po „Przerwij analizę” (opcjonalny)
- Podsumowanie sesji: czas, odbicia, % per element (słupki), przyciski „Panel” / „Historia” / „Nowa analiza”

---

## Zasady UX (obowiązkowe)

1. **Schludność** — max 1 baner trenerowy na wideo, panel boczny bez duplikacji tego samego tekstu
2. **Czytelność z dystansu** — feedback po odbiciu: min. 24–32px body, nagłówek 36–48px
3. **Ton trenerowy** — krótko, imperatyw: „Ugnij kolana!”, „Złącz dłonie!”, „Wyprostuj łokcie!”, „Popraw stopy!”
4. **Semantyka kolorów** — zielony OK, czerwony błąd, bursztyn ostrzeżenie/info (baner Dual-Cam przed startem)
5. **Łokcie ≠ Ręce** — osobne kafelki; Ręce = platforma/złączone dłonie, Łokcie = kąt łokcia
6. **BEZ pochylenia tułowia** — nie projektuj kafelka „Postawa” / „Pochylenie”
7. **Nie przeładowuj** — whitespace, jasna hierarchia, jeden primary CTA na sekcję
8. **Dane realistyczne** w mockupach — kąty, %, liczniki (nie Lorem ipsum)

---

## Czego NIE projektować
- Pochylenie / kąt tułowia do przodu
- Nowe logo (tylko favicon)
- Aplikacja mobilna / smartwatch UI
- Stary niebieski neon z poprzedniego design systemu jako dominanta
- Stock photos

---

## Deliverable
Dla każdego ekranu/stanu: desktop 1440×900 (MacBook Air), dark mode, komponenty gotowe do przepisania na Tailwind. Podaj nazwy warstw/komponentów po polsku lub angielsku (ButtonPrimary, ReadinessTile, PhaseStepper, CoachBanner, FollowThroughModal).
```

---

## Mapowanie po implementacji (dla developera)

Gdy dostaniesz screeny z narzędzia, implementuj w:

| Plik | Zakres |
|------|--------|
| `frontend/src/index.css` | Nowe tokeny, animacje faz, foot-spread |
| `frontend/tailwind.config.js` | Kolory granat + pomarańcz |
| `frontend/src/components/Sidebar.tsx` | Zwijany, profil na dole, link komend |
| `frontend/src/pages/LiveAnalysis.tsx` | Layout wideo + panel, wszystkie stany |
| `frontend/src/pages/Dashboard.tsx` | Słupki 5 elementów + donut |
| `frontend/src/pages/History.tsx` | Tabela + panel z mini słupkami |
| `frontend/src/pages/Warmup.tsx` | Ilustracje ćwiczeń |
| `frontend/src/pages/Login.tsx`, `Register.tsx` | Nowy styl |
| `frontend/src/pages/VoiceCommands.tsx` | **Nowa strona** — komendy głosowe |
| `logic/biomechanics.py` + `server.py` | Dodać `lokcie_ok` do `gotowosc` (backend) |

### Pola WebSocket do podpięcia (`/ws/metrics`)

```typescript
score, kneeAngle, totalContacts, postureWarnings, contactWarning, contactScore,
isContact, hasPose, hasBall, status, source, isAnalyzing,
fazaRuchu, gotowoscPrzedOdbiciem, feedbackFazy, rozstawienieStop, balansStop,
fuzjaOcena, komunikatFuzji, typOdbicia, komunikatKolana, zamachWykryty,
katBiodra, dystansPilkaRece, brakPracyNog, cameraMode
```

---

*Przygotowano na podstawie konsultacji: [KONSULTACJA_TRENERA.md](./KONSULTACJA_TRENERA.md)*
