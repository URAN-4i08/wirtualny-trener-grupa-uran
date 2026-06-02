"""
biomechanics.py — Moduł biomechanicznej analizy siatkarskiego odbicia dolnego
Wirtualny Trener - Grupa Uran

Zawiera trzy czyste funkcje analityczne:
  - analizuj_front(punkty, pilka, frame_shape)  → dane z kamery frontowej
  - analizuj_bok(punkty, historia_nadgarstkow)  → dane z kamery bocznej
  - fuzja_sensorow(dane_front, dane_bok)        → ocena techniki 0–100

Funkcje NIE modyfikują GUI. Wyniki trafiają do update_metrics() w server.py,
który przez WebSocket /ws/metrics aktualizuje wszystkie widżety frontendowe.
"""

import math
from collections import deque
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Konfiguracja progów (wszystko w jednym miejscu, łatwe do strojenia)
# ─────────────────────────────────────────────────────────────────────────────

# Kamera frontowa
PROG_PILKA_NADGARSTEK_PX = 110         # odległość px piłki od nadgarstka → odbicie (poluzowano)
PROG_NADGARSTKI_ZLACZONE = 0.20        # znorm. odległość między nadgarstkami → "złączone" (poluzowano)
PROG_ODBICIE_GORNE_KAT_MIN = 70.0     # min kąt łokcia przy odbiciu górnym (poluzowano)
PROG_ODBICIE_GORNE_KAT_MAX = 140.0    # max kąt łokcia przy odbiciu górnym (poluzowano)

# Kamera boczna — kolana
KAT_KOLANO_PRAWIDLOWY_MIN = 80.0      # dolna granica prawidłowego ugięcia (poluzowano)
KAT_KOLANO_PRAWIDLOWY_MAX = 160.0     # górna granica prawidłowego ugięcia (poluzowano)
KAT_KOLANO_ZA_WYSOKI = 170.0          # powyżej → "Zbyt wysoka pozycja!" (poluzowano)
KAT_KOLANO_ZA_NISKI = 50.0            # poniżej → "Zbyt głęboka pozycja!" (poluzowano)

# Kamera boczna — zamach nadgarstka
ZAMACH_HISTORIA_KLATEK = 12           # długość bufora historii Y nadgarstka
ZAMACH_DELTA_Y_PROG = 0.04            # min zmiana Y (znorm.) uznana za gwałtowny ruch
ZAMACH_MIN_KLATEK = 4                 # ile klatek ruchu potrzeba do rejestracji zamachu

# Fuzja — wagi oceny (suma = 100)
WAGA_KONTAKT_POTWIERDZONY = 40        # obie kamery potwierdziły kontakt
WAGA_KAT_KOLANOWY = 25               # prawidłowe ugięcie kolan w momencie odbicia
WAGA_NADGARSTKI_ZLACZONE = 20        # nadgarstki złączone → platforma dolna
WAGA_ZAMACH_WYKRYTY = 15             # aktywacja nóg przed kontaktem (praca nóg)


# ─────────────────────────────────────────────────────────────────────────────
# Pomocnicza funkcja kąta (identyczna logika co calculate_angle w coach_engine)
# ─────────────────────────────────────────────────────────────────────────────

def _kat(a, b, c) -> float:
    """
    Oblicza kąt w stopniach w punkcie 'b' (środek kąta).
    Akceptuje obiekty MediaPipe Landmark z atrybutami .x, .y
    """
    radians = math.atan2(c.y - b.y, c.x - b.x) - math.atan2(a.y - b.y, a.x - b.x)
    angle = abs(radians * 180.0 / math.pi)
    if angle > 180.0:
        angle = 360.0 - angle
    return angle


def _odleglosc_px(cx: int, cy: int, lm, frame_shape: tuple) -> float:
    """Odległość euklidesowa w pikselach między centrum (cx,cy) a punktem MediaPipe."""
    h, w = frame_shape[:2]
    lm_x = int(lm.x * w)
    lm_y = int(lm.y * h)
    return math.hypot(cx - lm_x, cy - lm_y)


# ─────────────────────────────────────────────────────────────────────────────
# 1. ANALIZA KAMERY FRONTOWEJ
# ─────────────────────────────────────────────────────────────────────────────

def analizuj_front(punkty: dict, pilka: list, frame_shape: tuple) -> dict:
    """
    Analiza z kamery frontowej (stojącej wprost przed zawodnikiem).

    Parametry
    ----------
    punkty      : dict — słownik punktów ciała z build_body_points() (server.py ~linia 388)
                  np. {"lewy_nadgarstek": lm, "prawy_nadgarstek": lm, ...}
    pilka       : list — lista (cx, cy) środków bbox piłek z YOLO (może być pusta)
    frame_shape : tuple — (wysokość, szerokość, ...) klatki OpenCV

    Zwraca
    ------
    dict z kluczami:
      typ_odbicia       : str|None  — "DOLNE" / "GORNE" / None
      dystans_pilka_px  : float|None — najmniejsza odl. piłki od nadgarstka w px
      nadgarstki_zlaczone : bool
      kat_lokcia_l      : float|None
      kat_lokcia_p      : float|None
      symetria_rece     : float|None — |lewy_y - prawy_y| znorm. (im mniejsze, tym lepiej)
      pilka_wykryta     : bool
    """
    wynik = {
        "typ_odbicia": None,
        "dystans_pilka_px": None,
        "nadgarstki_zlaczone": False,
        "kat_lokcia_l": None,
        "kat_lokcia_p": None,
        "symetria_rece": None,
        "pilka_wykryta": bool(pilka),
    }

    if not punkty:
        return wynik

    try:
        l_nadgarstek = punkty["lewy_nadgarstek"]
        p_nadgarstek = punkty["prawy_nadgarstek"]
        l_lokiec = punkty["lewy_lokiec"]
        p_lokiec = punkty["prawy_lokiec"]
        l_ramie = punkty["lewe_ramie"]
        p_ramie = punkty["prawe_ramie"]
        l_oko = punkty.get("lewe_oko")
        p_oko = punkty.get("prawe_oko")
    except KeyError:
        return wynik

    # ── Kąty łokci ──────────────────────────────────────────────────────────
    kat_l = _kat(l_ramie, l_lokiec, l_nadgarstek)
    kat_p = _kat(p_ramie, p_lokiec, p_nadgarstek)
    wynik["kat_lokcia_l"] = round(kat_l, 1)
    wynik["kat_lokcia_p"] = round(kat_p, 1)

    # ── Złączenie nadgarstków ────────────────────────────────────────────────
    odl_nadgarstkow = math.dist(
        (l_nadgarstek.x, l_nadgarstek.y),
        (p_nadgarstek.x, p_nadgarstek.y)
    )
    zlaczone = odl_nadgarstkow < PROG_NADGARSTKI_ZLACZONE
    wynik["nadgarstki_zlaczone"] = zlaczone

    # ── Symetria rąk (różnica Y nadgarstków, znormalizowana) ─────────────────
    wynik["symetria_rece"] = round(abs(l_nadgarstek.y - p_nadgarstek.y), 3)

    # ── Analiza z piłką ──────────────────────────────────────────────────────
    if not pilka:
        return wynik

    # Znajdź piłkę najbliżej rąk
    min_dist = None
    for cx, cy in pilka:
        d_l = _odleglosc_px(cx, cy, l_nadgarstek, frame_shape)
        d_p = _odleglosc_px(cx, cy, p_nadgarstek, frame_shape)
        d = min(d_l, d_p)
        if min_dist is None or d < min_dist:
            min_dist = d

    wynik["dystans_pilka_px"] = round(min_dist, 1) if min_dist is not None else None

    # ── Detekcja ODBICIA DOLNEGO ─────────────────────────────────────────────
    # Warunek: piłka blisko nadgarstków ORAZ nadgarstki złączone
    if min_dist is not None and min_dist < PROG_PILKA_NADGARSTEK_PX and zlaczone:
        wynik["typ_odbicia"] = "DOLNE"
        return wynik

    # ── Detekcja ODBICIA GÓRNEGO ─────────────────────────────────────────────
    # Warunek: piłka powyżej oczu + bliskość nadgarstków + kąt łokcia 90–120°
    if l_oko is not None and p_oko is not None and min_dist is not None:
        linia_oczu_y = (l_oko.y + p_oko.y) / 2  # znormalizowana (0=góra, 1=dół)
        # Piłka jest "powyżej oczu" gdy jej Y (px) < linia_oczu_y * h
        h = frame_shape[0]
        for cx, cy in pilka:
            pilka_y_norm = cy / h
            if pilka_y_norm < linia_oczu_y:  # piłka wyżej niż oczy
                katy_lokci_ok = (
                    PROG_ODBICIE_GORNE_KAT_MIN <= kat_l <= PROG_ODBICIE_GORNE_KAT_MAX
                    and PROG_ODBICIE_GORNE_KAT_MIN <= kat_p <= PROG_ODBICIE_GORNE_KAT_MAX
                )
                dist_gora = min(
                    _odleglosc_px(cx, cy, l_nadgarstek, frame_shape),
                    _odleglosc_px(cx, cy, p_nadgarstek, frame_shape)
                )
                if katy_lokci_ok and dist_gora < PROG_PILKA_NADGARSTEK_PX * 1.5:
                    wynik["typ_odbicia"] = "GORNE"
                    return wynik

    return wynik


def analizuj_stopy(punkty: dict) -> dict:
    wynik = {
        'rozstawienie_stop': None,
        'rozstawienie_ok': True,
        'balans': 'OK',
        'komunikat_stop': 'Oczekuję na stopy w kadrze'
    }
    if not punkty:
        return wynik
    try:
        l_kostka = punkty['lewa_kostka']
        p_kostka = punkty['prawa_kostka']
        l_ramie = punkty['lewe_ramie']
        p_ramie = punkty['prawe_ramie']
        l_biodro = punkty['lewe_biodro']
        p_biodro = punkty['prawe_biodro']
    except KeyError:
        return wynik
        
    dystans_kostek = abs(l_kostka.x - p_kostka.x)
    szerokosc_barkow = max(0.08, abs(l_ramie.x - p_ramie.x))
    
    rozstawienie = dystans_kostek / szerokosc_barkow
    wynik['rozstawienie_stop'] = rozstawienie
    # Znacznie poluzowane zasady dla stóp
    wynik['rozstawienie_ok'] = 0.6 <= rozstawienie <= 1.6
    
    srodek_stop = (l_kostka.x + p_kostka.x) / 2
    srodek_bioder = (l_biodro.x + p_biodro.x) / 2
    
    balans_diff = srodek_bioder - srodek_stop
    # Poluzowane zasady dla balansu ciężaru
    if balans_diff > 0.25:
        wynik['balans'] = 'ZA_LEWO'
    elif balans_diff < -0.25:
        wynik['balans'] = 'ZA_PRAWO'
    else:
        wynik['balans'] = 'OK'
        
    return wynik


def analizuj_faze(dane_front: dict, dane_bok: dict, dystans_pilka: float | None) -> dict:
    faza = 'OCZEKIWANIE'
    if dane_front.get('pilka_wykryta'):
        if dystans_pilka is not None and dystans_pilka <= 200 and dane_front.get('typ_odbicia') is not None:
            faza = 'KONTAKT'
        elif dane_front.get('typ_odbicia') is not None and dystans_pilka is not None and dystans_pilka > PROG_PILKA_NADGARSTEK_PX:
            faza = 'FOLLOW_THROUGH'
        elif dystans_pilka is None or dystans_pilka > 200:
            faza = 'PRZYGOTOWANIE'
            
    stopa_ok = dane_front.get('dane_stopy', {}).get('rozstawienie_ok', True) if dane_front else True
    
    kat_kolana = dane_bok.get('kat_kolana')
    kolana_ok = True if kat_kolana is not None and KAT_KOLANO_PRAWIDLOWY_MIN <= kat_kolana <= KAT_KOLANO_PRAWIDLOWY_MAX else False
    
    platforma_ok = dane_front.get('nadgarstki_zlaczone', False) if dane_front else False
    ruch_ok = dane_bok.get('zamach_wykryty', False) if faza == 'KONTAKT' else True

    gotowosc = {
        'stopa_ok': stopa_ok,
        'kolana_ok': kolana_ok,
        'platforma_ok': platforma_ok,
        'ruch_ok': ruch_ok
    }
    
    if faza == 'OCZEKIWANIE':
        feedback = 'Świetna pozycja wyjściowa! ✓' if all(gotowosc.values()) else 'Przyjmij swobodną pozycję gotowości'
    elif faza == 'PRZYGOTOWANIE':
        bledy = []
        dobre = []
        if not stopa_ok:
            bledy.append('Popraw stopy')
        else:
            dobre.append('Stopy OK')
            
        if not kolana_ok:
            bledy.append('Ugnij kolana')
        else:
            dobre.append('Kolana OK')
            
        if not platforma_ok:
            bledy.append('Złącz dłonie')
        
        if not bledy:
            feedback = 'Piłka w drodze — piękna pozycja! ✓'
        else:
            pozytyw = dobre[0] + ' ✓, ' if dobre else ''
            feedback = f"Piłka leci! {pozytyw}{', '.join(bledy)}."
    elif faza == 'KONTAKT':
        feedback = 'Prawidłowe odbicie! ✓' if all(gotowosc.values()) else 'Odbicie!'
    else:
        feedback = 'Dobra robota! Wróć do pozycji ✓' if all(gotowosc.values()) else 'Kontroluj pozycję po odbiciu'

    return {
        'faza': faza,
        'gotowosc': gotowosc,
        'feedback_fazy': feedback
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. ANALIZA KAMERY BOCZNEJ
# ─────────────────────────────────────────────────────────────────────────────

class WristTrajectoryTracker:
    """
    Śledzi trajektorię nadgarstka (oś Y) w oknie N klatek.
    Wykrywa gwałtowny ruch dół→góra charakterystyczny dla zamachu.

    Użycie w server.py:
        wrist_tracker = WristTrajectoryTracker()          # raz przy inicjalizacji
        ... w pętli klatek:
        wrist_tracker.update(punkty)
    """

    def __init__(self, historia: int = ZAMACH_HISTORIA_KLATEK):
        self._buf: deque = deque(maxlen=historia)

    def update(self, punkty: dict) -> None:
        """Dodaje bieżącą pozycję Y nadgarstka do bufora."""
        if not punkty:
            return
        try:
            y_l = punkty["lewy_nadgarstek"].y
            y_p = punkty["prawy_nadgarstek"].y
            # Używamy śr. niższego (niżej = wyższy Y w ukł. ekranu) nadgarstka
            self._buf.append(min(y_l, y_p))
        except KeyError:
            pass

    def wykryj_zamach(self) -> tuple[bool, str]:
        """
        Zwraca (zamach_wykryty: bool, opis: str).
        Zamach dolny: Y rośnie (nadgarstek idzie w dół), potem maleje (nadgarstek idzie w górę).
        """
        if len(self._buf) < ZAMACH_MIN_KLATEK + 2:
            return False, "Brak danych zamachu"

        historia = list(self._buf)
        # Szukamy punktu zwrotnego: minimum Y (najwyżej) po fazie opadania
        delty = [historia[i+1] - historia[i] for i in range(len(historia)-1)]

        faza_dol = sum(1 for d in delty[:len(delty)//2] if d > ZAMACH_DELTA_Y_PROG)
        faza_gora = sum(1 for d in delty[len(delty)//2:] if d < -ZAMACH_DELTA_Y_PROG)

        if faza_dol >= ZAMACH_MIN_KLATEK // 2 and faza_gora >= ZAMACH_MIN_KLATEK // 2:
            # Oblicz amplitudę zamachu
            amp = max(historia) - min(historia)
            if amp > ZAMACH_DELTA_Y_PROG * 2:
                dynamika = "Silny zamach" if amp > 0.12 else "Umiarkowany zamach"
                return True, dynamika

        return False, "Brak wyraźnego zamachu"

    def reset(self) -> None:
        self._buf.clear()


def analizuj_bok(punkty: dict, wrist_tracker: Optional["WristTrajectoryTracker"] = None) -> dict:
    """
    Analiza z kamery bocznej (telefon pod ~45° względem osi strzału).

    Parametry
    ----------
    punkty        : dict — słownik punktów ciała z build_body_points()
    wrist_tracker : WristTrajectoryTracker — instancja śledzenia zamachu (lub None)

    Zwraca
    ------
    dict z kluczami:
      kat_kolana       : float|None  — średni kąt HIP-KNEE-ANKLE
      kat_biodra       : float|None  — średni kąt SHOULDER-HIP-KNEE
      komunikat_kolana : str         — komunikat do GUI
      kolana_proste    : bool        — True jeśli kąt > KAT_KOLANO_ZA_WYSOKI
      zamach_wykryty   : bool
      dynamika_zamachu : str         — opis dynamiki ruchu
    """
    wynik = {
        "kat_kolana": None,
        "kat_biodra": None,
        "komunikat_kolana": "Brak danych z kamery bocznej",
        "kolana_proste": False,
        "zamach_wykryty": False,
        "dynamika_zamachu": "Brak danych zamachu",
    }

    if not punkty:
        return wynik

    try:
        l_ramie = punkty["lewe_ramie"]
        p_ramie = punkty["prawe_ramie"]
        l_biodro = punkty["lewe_biodro"]
        p_biodro = punkty["prawe_biodro"]
        l_kolano = punkty["lewe_kolano"]
        p_kolano = punkty["prawe_kolano"]
        l_kostka = punkty["lewa_kostka"]
        p_kostka = punkty["prawa_kostka"]
    except KeyError:
        return wynik

    # ── Kąt kolanowy (HIP-KNEE-ANKLE) ───────────────────────────────────────
    kat_l_kolano = _kat(l_biodro, l_kolano, l_kostka)
    kat_p_kolano = _kat(p_biodro, p_kolano, p_kostka)
    kat_sredni = (kat_l_kolano + kat_p_kolano) / 2
    wynik["kat_kolana"] = round(kat_sredni, 1)

    # ── Kąt biodrowy (SHOULDER-HIP-KNEE) ────────────────────────────────────
    kat_l_biodro = _kat(l_ramie, l_biodro, l_kolano)
    kat_p_biodro = _kat(p_ramie, p_biodro, p_kolano)
    wynik["kat_biodra"] = round((kat_l_biodro + kat_p_biodro) / 2, 1)

    # ── Ocena pozycji kolanowej ──────────────────────────────────────────────
    kolana_proste = kat_sredni > KAT_KOLANO_ZA_WYSOKI
    wynik["kolana_proste"] = kolana_proste

    if KAT_KOLANO_PRAWIDLOWY_MIN <= kat_sredni <= KAT_KOLANO_PRAWIDLOWY_MAX:
        wynik["komunikat_kolana"] = "Pozycja niska, prawidłowa ✓"
    elif kat_sredni > KAT_KOLANO_ZA_WYSOKI:
        wynik["komunikat_kolana"] = "Zbyt wysoka pozycja! Ugnij kolana!"
    elif kat_sredni < KAT_KOLANO_ZA_NISKI:
        wynik["komunikat_kolana"] = "Zbyt głęboka pozycja! Wstań odrobinę wyżej!"
    else:
        wynik["komunikat_kolana"] = f"Kolana: {kat_sredni:.0f}° — korekta pozycji"

    # ── Zamach nadgarstka ────────────────────────────────────────────────────
    if wrist_tracker is not None:
        wrist_tracker.update(punkty)
        zamach, dynamika = wrist_tracker.wykryj_zamach()
        wynik["zamach_wykryty"] = zamach
        wynik["dynamika_zamachu"] = dynamika

    return wynik


# ─────────────────────────────────────────────────────────────────────────────
# 3. FUZJA SENSORÓW (Dual-Cam) — pomocnicze funkcje gradientowe
# ─────────────────────────────────────────────────────────────────────────────

def _gradient_kolana(kat: float) -> int:
    """Gradientowa ocena kąta kolanowego: 0–25 pkt."""
    if kat is None:
        return 0
    if 100.0 <= kat <= 140.0:
        return 25  # optymalny zakres = pełne punkty
    if kat < 80.0 or kat > 170.0:
        return 0  # poza dopuszczalnym zakresem
    if kat < 100.0:
        return int(25 * (kat - 80.0) / 20.0)  # gradient 80→100
    return int(25 * (170.0 - kat) / 30.0)  # gradient 140→170


# ─────────────────────────────────────────────────────────────────────────────

def fuzja_sensorow(dane_front: dict, dane_bok: dict) -> dict:
    """
    Łączy dane z kamery frontowej i bocznej w ostateczną ocenę techniki.

    ZASADA: Odbicie uznane za prawidłowe TYLKO gdy:
      1. Kamera frontowa potwierdza blizkość piłki do rąk (kontakt)
      2. Kamera boczna potwierdza zwiększenie kąta kolanowego (prostowanie nóg)

    Parametry
    ----------
    dane_front : dict — wynik analizuj_front()
    dane_bok   : dict — wynik analizuj_bok()

    Zwraca
    ------
    dict z kluczami:
      ocena_fuzji      : int   — wynik techniki 0–100 (→ ProgressBar w GUI)
      komunikat_fuzji  : str   — główny komunikat tekstowy (→ pole tekstowe GUI)
      brak_pracy_nog   : bool  — True → alert "Odbicie samymi rękami!"
      typ_odbicia      : str|None — "DOLNE" / "GORNE" / None
    """
    wynik = {
        "ocena_fuzji": 0,
        "komunikat_fuzji": "Oczekiwanie na analizę...",
        "brak_pracy_nog": False,
        "typ_odbicia": None,
    }

    typ_odbicia = dane_front.get("typ_odbicia")
    kontakt_front = typ_odbicia is not None  # front widzi odbicie
    pilka_wykryta = dane_front.get("pilka_wykryta", False)
    kolana_proste = dane_bok.get("kolana_proste", False)
    kat_kolana = dane_bok.get("kat_kolana")
    nadgarstki_zlaczone = dane_front.get("nadgarstki_zlaczone", False)
    zamach_wykryty = dane_bok.get("zamach_wykryty", False)
    komunikat_kolana = dane_bok.get("komunikat_kolana", "")

    wynik["typ_odbicia"] = typ_odbicia

    # ── Brak piłki w kadrze ───────────────────────────────────────────────────
    if not pilka_wykryta:
        wynik["komunikat_fuzji"] = komunikat_kolana or "Ustaw się w pozycji do odbicia"
        # Daj częściową ocenę za samą pozycję
        if kat_kolana is not None and KAT_KOLANO_PRAWIDLOWY_MIN <= kat_kolana <= KAT_KOLANO_PRAWIDLOWY_MAX:
            wynik["ocena_fuzji"] = 30  # za poprawną pozycję oczekiwania
            wynik["komunikat_fuzji"] = f"Dobra pozycja wyjściowa | {komunikat_kolana}"
        return wynik

    # ── Ocena gdy jest kontakt z piłką ───────────────────────────────────────
    if kontakt_front:
        # Sprawdź błąd krytyczny: odbicie bez pracy nóg
        if kolana_proste:
            wynik["brak_pracy_nog"] = True
            wynik["komunikat_fuzji"] = "Odbicie wykonane samymi rękami! Brak pracy nóg!"
            wynik["ocena_fuzji"] = max(0, 100 - WAGA_ZAMACH_WYKRYTY - WAGA_KAT_KOLANOWY)
            return wynik

        # Normalne odbicie — sumuj punkty
        punkty = 0

        # +40 pkt: obie kamery potwierdziły kontakt (front + bok widzi ugięte kolana)
        punkty += WAGA_KONTAKT_POTWIERDZONY

        # +0-25 pkt: gradient kąta kolanowego
        punkty += _gradient_kolana(kat_kolana)

        # +20 pkt: złączone nadgarstki (platforma dolna)
        if nadgarstki_zlaczone:
            punkty += WAGA_NADGARSTKI_ZLACZONE

        # +5-15 pkt: praca nóg (częściowe punkty nawet bez pełnego zamachu)
        if zamach_wykryty:
            punkty += WAGA_ZAMACH_WYKRYTY
        else:
            punkty += 5  # częściowe punkty za pozycję

        wynik["ocena_fuzji"] = min(100, punkty)

        if punkty >= 90:
            wynik["komunikat_fuzji"] = f"Doskonałe odbicie {typ_odbicia}! ({punkty}/100)"
        elif punkty >= 70:
            wynik["komunikat_fuzji"] = f"Dobre odbicie {typ_odbicia} ({punkty}/100)"
        else:
            problemy = []
            if kat_kolana is None or not (KAT_KOLANO_PRAWIDLOWY_MIN <= kat_kolana <= KAT_KOLANO_PRAWIDLOWY_MAX):
                problemy.append(komunikat_kolana)
            if not nadgarstki_zlaczone:
                problemy.append("Złącz dłonie!")
            if not zamach_wykryty:
                problemy.append("Więcej pracy nóg!")
            wynik["komunikat_fuzji"] = " | ".join(problemy) if problemy else f"Odbicie {typ_odbicia} ({punkty}/100)"

    else:
        # Piłka w kadrze, ale brak kontaktu — oceniaj pozycję oczekiwania
        wynik["komunikat_fuzji"] = komunikat_kolana or "Przygotuj się do odbicia"
        if kat_kolana is not None and KAT_KOLANO_PRAWIDLOWY_MIN <= kat_kolana <= KAT_KOLANO_PRAWIDLOWY_MAX:
            wynik["ocena_fuzji"] = 40
        elif kat_kolana is not None and kat_kolana > KAT_KOLANO_ZA_WYSOKI:
            wynik["ocena_fuzji"] = 20
            wynik["komunikat_fuzji"] = "Zbyt wysoka pozycja! Ugnij kolana!"

    return wynik
