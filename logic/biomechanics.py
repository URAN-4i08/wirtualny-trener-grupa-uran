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
PROG_PILKA_NADGARSTEK_PX = 240         # odległość px piłki od nadgarstka → kontakt / odbicie
PROG_PILKA_KONTAKT_PX = 240            # próg zapasowej detekcji odbicia (analizuj_front)
PROG_NADGARSTKI_ZLACZONE = 0.25        # znorm. odległość między nadgarstkami → "złączone" (live)
PROG_NADGARSTKI_SETUP = 0.30           # próg przed startem (blisko coach_engine 0.32)
PROG_LOKCI_SETUP_MIN = 55.0
PROG_LOKCI_SETUP_MAX = 158.0
PROG_LOKCI_SETUP_PROSTE = 168.0        # powyżej = wyprostowane ramiona
PROG_ODBICIE_GORNE_KAT_MIN = 70.0     # min kąt łokcia przy odbiciu górnym (poluzowano)
PROG_ODBICIE_GORNE_KAT_MAX = 140.0    # max kąt łokcia przy odbiciu górnym (poluzowano)

# Kamera boczna — kolana (bardzo wybaczające)
KAT_KOLANO_PRAWIDLOWY_MIN = 70.0      # dolna granica prawidłowego ugięcia
KAT_KOLANO_PRAWIDLOWY_MAX = 175.0     # górna granica — prawie stojąc uznaje za OK
KAT_KOLANO_ZA_WYSOKI = 178.0          # dopiero przy prawie wyprostowanych nogach
KAT_KOLANO_ZA_NISKI = 40.0            # dopiero przy bardzo głębokim kucnięciu

# Kamera boczna — zamach nadgarstka
ZAMACH_HISTORIA_KLATEK = 12           # długość bufora historii Y nadgarstka
ZAMACH_DELTA_Y_PROG = 0.04            # min zmiana Y (znorm.) uznana za gwałtowny ruch
ZAMACH_MIN_KLATEK = 4                 # ile klatek ruchu potrzeba do rejestracji zamachu

# Widoczność nóg w kadrze
MIN_NOGI_VISIBILITY = 0.32
MAX_NOGI_Y = 0.99

# Stopy — rozstaw względem bioder (szeroki zakres jak wcześniej przy barkach)
ROZSTAW_STOP_MIN = 0.65
ROZSTAW_STOP_MAX = 1.55

# Kolana — pozycja gotowości przed próbą (węższy zakres niż live)
KAT_KOLANO_GOTOWOSC_MIN = 88.0
KAT_KOLANO_GOTOWOSC_MAX = 178.0
KAT_KOLANO_SETUP_MIN = 88.0
KAT_KOLANO_SETUP_MAX = 173.0
KAT_KOLANO_SETUP_PROSTE = 177.0        # powyżej na wszystkich odczytach = stoisz zupełnie prosto

KOMUNIKAT_BRAK_NOG = "Nie widać nóg — ustaw się tak, by stopy były w kadrze"

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


def nogi_widoczne(punkty: dict) -> bool:
    """Czy kolana i kostki są widoczne w kadrze (wystarczająca pewność + nie ucięte na dole)."""
    if not punkty:
        return False

    for key in ("lewe_kolano", "prawe_kolano", "lewa_kostka", "prawa_kostka"):
        lm = punkty.get(key)
        if lm is None:
            return False
        if getattr(lm, "visibility", 0.0) < MIN_NOGI_VISIBILITY:
            return False
        if lm.y > MAX_NOGI_Y:
            return False
    return True


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
        "pilka_wykryta": False,
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
    min_dist_cy = 0
    for cx, cy in pilka:
        d_l = _odleglosc_px(cx, cy, l_nadgarstek, frame_shape)
        d_p = _odleglosc_px(cx, cy, p_nadgarstek, frame_shape)
        d = min(d_l, d_p)
        if min_dist is None or d < min_dist:
            min_dist = d
            min_dist_cy = cy

    wynik["dystans_pilka_px"] = round(min_dist, 1) if min_dist is not None else None
    wynik["pilka_wykryta"] = min_dist is not None and min_dist < PROG_PILKA_NADGARSTEK_PX

    # ── Detekcja ODBICIA DOLNEGO ─────────────────────────────────────────
    # Warunek: piłka blisko nadgarstków (złączone = bonus, nie wymag.)
    if min_dist is not None and min_dist < PROG_PILKA_NADGARSTEK_PX:
        # Piłka jest poniżej oczu → odbicie dolne
        srodek_nadg_y = (l_nadgarstek.y + p_nadgarstek.y) / 2
        linia_oczu_y = None
        if l_oko is not None and p_oko is not None:
            linia_oczu_y = (l_oko.y + p_oko.y) / 2
        # Piłka przy rękach poniżej oczu LUB nadgarstki złączone = DOLNE
        pilka_nisko = linia_oczu_y is None or (min_dist_cy / frame_shape[0]) > (linia_oczu_y - 0.05)
        if zlaczone or pilka_nisko:
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
        'rozstawienie_ok': False,
        'balans': 'BRAK',
        'nogi_widoczne': False,
        'komunikat_stop': KOMUNIKAT_BRAK_NOG,
    }
    if not punkty:
        return wynik

    wynik['nogi_widoczne'] = nogi_widoczne(punkty)
    if not wynik['nogi_widoczne']:
        return wynik

    wynik['komunikat_stop'] = None
    try:
        l_kostka = punkty['lewa_kostka']
        p_kostka = punkty['prawa_kostka']
        l_biodro = punkty['lewe_biodro']
        p_biodro = punkty['prawe_biodro']
    except KeyError:
        return wynik
        
    dystans_kostek = abs(l_kostka.x - p_kostka.x)
    szerokosc_bioder = max(0.08, abs(l_biodro.x - p_biodro.x))
    
    rozstawienie = dystans_kostek / szerokosc_bioder
    wynik['rozstawienie_stop'] = round(rozstawienie, 2)
    wynik['rozstawienie_ok'] = ROZSTAW_STOP_MIN <= rozstawienie <= ROZSTAW_STOP_MAX
    
    srodek_stop = (l_kostka.x + p_kostka.x) / 2
    srodek_bioder = (l_biodro.x + p_biodro.x) / 2
    
    balans_diff = srodek_bioder - srodek_stop
    if balans_diff > 0.25:
        wynik['balans'] = 'ZA_LEWO'
    elif balans_diff < -0.25:
        wynik['balans'] = 'ZA_PRAWO'
    else:
        wynik['balans'] = 'OK'
        
    return wynik


def _katy_kolan_setup(
    dane_bok: dict,
    kat_kolana_front: float | None,
    punkty: dict | None,
) -> list[float]:
    """Zbiera wszystkie dostępne odczyty kąta kolana (front + bok + per-noga)."""
    katy: list[float] = []
    kat_bok = dane_bok.get("kat_kolana") if dane_bok else None
    if kat_bok is not None:
        katy.append(float(kat_bok))
    if kat_kolana_front is not None:
        katy.append(float(kat_kolana_front))
    if punkty:
        for hip_k, kol_k, kost_k in (
            ("lewe_biodro", "lewe_kolano", "lewa_kostka"),
            ("prawe_biodro", "prawe_kolano", "prawa_kostka"),
        ):
            try:
                katy.append(_kat(punkty[hip_k], punkty[kol_k], punkty[kost_k]))
            except KeyError:
                pass
    return katy


def _kolana_setup_ok(
    dane_bok: dict,
    kat_kolana_front: float | None,
    punkty: dict | None,
) -> bool:
    """
    Kolana w pozycji gotowości — łączy kamerę boczną i frontową.
    Kamera frontowa z perspektywy zaniża ugięcie, więc używamy min(kątów)
    i heurystyki głębokości (kolana niżej niż biodra w kadrze).
    """
    katy = _katy_kolan_setup(dane_bok, kat_kolana_front, punkty)
    if not katy:
        return False

    min_kat = min(katy)
    if min_kat > KAT_KOLANO_SETUP_PROSTE:
        return False

    if any(KAT_KOLANO_SETUP_MIN <= k <= KAT_KOLANO_SETUP_MAX for k in katy):
        return True

    # Front / ukośny kadr: kolana wyraźnie poniżej bioder = ugięcie mimo wysokiego kąta
    if punkty and min_kat <= KAT_KOLANO_SETUP_PROSTE:
        try:
            hip_y = (punkty["lewe_biodro"].y + punkty["prawe_biodro"].y) / 2
            knee_y = (punkty["lewe_kolano"].y + punkty["prawe_kolano"].y) / 2
            if knee_y > hip_y + 0.035:
                return True
        except KeyError:
            pass

    return False


def _lokcie_ok(kat_l: float | None, kat_p: float | None) -> bool:
    if kat_l is None or kat_p is None:
        return False
    if kat_l > PROG_LOKCI_SETUP_PROSTE and kat_p > PROG_LOKCI_SETUP_PROSTE:
        return False
    if kat_l < 45 or kat_p < 45:
        return False
    strict = (
        PROG_LOKCI_SETUP_MIN <= kat_l <= PROG_LOKCI_SETUP_MAX
        and PROG_LOKCI_SETUP_MIN <= kat_p <= PROG_LOKCI_SETUP_MAX
    )
    relaxed = kat_l <= 168 and kat_p <= 168
    return strict or relaxed


def _platforma_setup(dane_front: dict, punkty: dict | None) -> bool:
    """Złączone dłonie na platformie przed ciałem — bez duplikowania testu łokci."""
    if not dane_front or not punkty:
        return False
    try:
        l_w = punkty["lewy_nadgarstek"]
        p_w = punkty["prawy_nadgarstek"]
        l_hip = punkty["lewe_biodro"]
        p_hip = punkty["prawe_biodro"]
        l_sh = punkty["lewe_ramie"]
        p_sh = punkty["prawe_ramie"]
    except (KeyError, TypeError):
        return False

    odl_nadgarstkow = math.dist((l_w.x, l_w.y), (p_w.x, p_w.y))
    zlaczone = odl_nadgarstkow < PROG_NADGARSTKI_SETUP or bool(
        dane_front.get("nadgarstki_zlaczone")
    )
    if not zlaczone:
        return False

    avg_wrist_y = (l_w.y + p_w.y) / 2
    avg_hip_y = (l_hip.y + p_hip.y) / 2
    avg_shoulder_y = (l_sh.y + p_sh.y) / 2
    # platforma dolna: dłonie przed ciałem — szeroki, wybaczający zakres wysokości
    height_ok = (avg_shoulder_y - 0.18) < avg_wrist_y < (avg_hip_y + 0.22)

    srodek_barkow = (l_sh.x + p_sh.x) / 2
    srodek_nadgarstkow = (l_w.x + p_w.x) / 2
    centered_ok = abs(srodek_nadgarstkow - srodek_barkow) <= 0.42

    return height_ok and centered_ok


def _gotowosc_setup(
    dane_front: dict,
    dane_bok: dict,
    dane_stopy: dict,
    kat_kolana_front: float | None,
    punkty: dict | None = None,
) -> dict:
    """Surowa checklist przed startem próby — bez domyślnego „OK”."""
    nogi_front = bool(dane_stopy.get("nogi_widoczne"))

    # Łagodnie: wystarczy że stopy są w kadrze i z grubsza rozstawione —
    # nie wymagamy idealnego balansu (początkujący przestępuje z nogi na nogę).
    stopa_ok = nogi_front and bool(dane_stopy.get("rozstawienie_ok"))

    kolana_ok = _kolana_setup_ok(dane_bok, kat_kolana_front, punkty)

    platforma_ok = _platforma_setup(dane_front, punkty)
    lokcie_ok = _lokcie_ok(
        dane_front.get("kat_lokcia_l") if dane_front else None,
        dane_front.get("kat_lokcia_p") if dane_front else None,
    )

    return {
        "stopa_ok": stopa_ok,
        "kolana_ok": kolana_ok,
        "platforma_ok": platforma_ok,
        "lokcie_ok": lokcie_ok,
        "ruch_ok": nogi_front,
    }


def _gotowosc_setup_prosta(
    punkty: dict | None,
    kat_kolana_front: float | None,
    camera_mode: str = "front",
) -> dict:
    """
    Checklist dla POJEDYNCZEJ kamery — te same 5 segmentów co w Dual-Cam, ale
    liczone wprost z punktów jednej kamery i DOPASOWANE do widoku:

      • front — widać rozstaw stóp, złączone dłonie, kąt łokci z przodu,
      • bok   — rozstawu/złączenia nie widać, więc liczymy ułożenie rąk z przodu
                i (dokładny z boku) kąt kolan.

    Progi są tak dobrane, by NIE zapaliły się od samego stania — trzeba realnie
    przyjąć pozycję gotowości (ugięte kolana, ręce złączone i wysunięte przed siebie).
    """
    puste = {
        "stopa_ok": False,
        "kolana_ok": False,
        "platforma_ok": False,
        "lokcie_ok": False,
        "ruch_ok": False,
    }
    if not punkty:
        return puste

    bok = camera_mode == "side"

    # ── Łokcie — przedramiona ułożone, nie zwisają prosto wzdłuż ciała ──────────
    lokcie_ok = False
    try:
        kl = _kat(punkty["lewe_ramie"], punkty["lewy_lokiec"], punkty["lewy_nadgarstek"])
        kp = _kat(punkty["prawe_ramie"], punkty["prawy_lokiec"], punkty["prawy_nadgarstek"])
        # 40–168°: odrzuca i ostro złożone ręce, i całkiem wyprostowane wzdłuż ciała
        lokcie_ok = 40.0 <= kl <= 168.0 and 40.0 <= kp <= 168.0
    except (KeyError, TypeError):
        pass

    # ── Ręce / platforma ───────────────────────────────────────────────────────
    platforma_ok = False
    try:
        lw = punkty["lewy_nadgarstek"]
        pw = punkty["prawy_nadgarstek"]
        ls = punkty["lewe_ramie"]
        ps = punkty["prawe_ramie"]
        lh = punkty["lewe_biodro"]
        ph = punkty["prawe_biodro"]
        avg_wrist_y = (lw.y + pw.y) / 2
        avg_shoulder_y = (ls.y + ps.y) / 2
        avg_hip_y = (lh.y + ph.y) / 2
        wysokosc_ok = (avg_shoulder_y - 0.05) < avg_wrist_y < (avg_hip_y + 0.10)
        if bok:
            # Z boku nadgarstki się nakładają — wymagamy RĄK WYSUNIĘTYCH PRZED SIEBIE.
            avg_wrist_x = (lw.x + pw.x) / 2
            avg_shoulder_x = (ls.x + ps.x) / 2
            rece_przed_soba = abs(avg_wrist_x - avg_shoulder_x) >= 0.07
            platforma_ok = rece_przed_soba and wysokosc_ok
        else:
            # Z przodu — dłonie wyraźnie złączone i na właściwej wysokości.
            zlaczone = math.dist((lw.x, lw.y), (pw.x, pw.y)) < 0.18
            platforma_ok = zlaczone and wysokosc_ok
    except (KeyError, TypeError):
        pass

    # ── Kolana — realne ugięcie (bez sztuczki „kolana niżej bioder") ────────────
    kolana_ok = kat_kolana_front is not None and 80.0 <= kat_kolana_front <= 168.0

    # ── Stopy ───────────────────────────────────────────────────────────────────
    stopa_ok = False
    if nogi_widoczne(punkty):
        if bok:
            # Z boku nie ocenimy rozstawu — wystarczy, że stopy są w kadrze.
            stopa_ok = True
        else:
            try:
                la = punkty["lewa_kostka"]
                pa = punkty["prawa_kostka"]
                lh = punkty["lewe_biodro"]
                ph = punkty["prawe_biodro"]
                rozstaw_bioder = abs(lh.x - ph.x)
                if rozstaw_bioder >= 0.04:
                    ratio = abs(la.x - pa.x) / rozstaw_bioder
                    stopa_ok = 0.85 <= ratio <= 2.40  # realnie rozstawione (≈ szer. bioder)
            except (KeyError, TypeError, ZeroDivisionError):
                pass

    # ── „W kadrze" — cała sylwetka widoczna (głowa + nogi) ──────────────────────
    w_kadrze = False
    try:
        nos_vis = getattr(punkty["nos"], "visibility", 1.0)
        w_kadrze = nos_vis >= 0.4 and nogi_widoczne(punkty)
    except (KeyError, TypeError):
        w_kadrze = nogi_widoczne(punkty)

    return {
        "stopa_ok": stopa_ok,
        "kolana_ok": kolana_ok,
        "platforma_ok": platforma_ok,
        "lokcie_ok": lokcie_ok,
        "ruch_ok": w_kadrze,
    }


def analizuj_faze(
    dane_front: dict,
    dane_bok: dict,
    dystans_pilka: float | None,
    kat_kolana_front: float | None = None,
    ostatnie_odbicie: dict | None = None,
    tryb_setup: bool = False,
    punkty: dict | None = None,
    camera_mode: str = "front",
) -> dict:
    """
    Analiza fazy ruchu z obsługą pamięci ostatniego odbicia.

    Parametry
    ----------
    dane_front         : wynik analizuj_front()
    dane_bok           : wynik analizuj_bok()
    dystans_pilka      : odległość piłki od rąk (px)
    kat_kolana_front   : kąt kolan z MediaPipe (działa na każdej kamerze)
    ostatnie_odbicie   : dict z pamięcią ostatniego odbicia z server.py:
                         {'typ': 'DOLNE', 'czas': float, 'gotowosc': {...}, 'feedback': str}
                         Jeśli minęło < FOLLOW_THROUGH_SEC → faza = FOLLOW_THROUGH
    """
    import time as _time

    FOLLOW_THROUGH_SEC = 3.0

    dane_stopy = dane_front.get('dane_stopy', {}) if dane_front else {}

    if tryb_setup:
        # Dual-Cam: pełna checklist z fuzją dwóch kamer.
        # Pojedyncza kamera: uproszczona, łatwa checklist z tych samych 5 segmentów.
        if camera_mode == "dual":
            gotowosc = _gotowosc_setup(
                dane_front, dane_bok, dane_stopy, kat_kolana_front, punkty=punkty,
            )
        else:
            gotowosc = _gotowosc_setup_prosta(punkty, kat_kolana_front, camera_mode=camera_mode)
        if not gotowosc["ruch_ok"]:
            feedback = 'Ustaw się tak, by widać było stopy w kadrze frontowej kamery'
        elif not gotowosc["lokcie_ok"]:
            feedback = 'Ustaw łokcie — przedramiona przed ciałem, kąt ok. 90°'
        elif not gotowosc["platforma_ok"]:
            feedback = 'Złącz dłonie — platforma przed ciałem'
        elif not gotowosc["kolana_ok"]:
            feedback = 'Ugnij kolana — pozycja gotowości siatkarskiej'
        elif not gotowosc["stopa_ok"]:
            feedback = 'Popraw rozstaw stóp (na szerokość bioder)'
        elif all(gotowosc.values()):
            feedback = 'Świetna pozycja wyjściowa! ✓'
        else:
            feedback = 'Przyjmij swobodną pozycję gotowości'
        return {
            'faza': 'OCZEKIWANIE',
            'gotowosc': gotowosc,
            'feedback_fazy': feedback,
        }

    nogi_w_kadrze = bool(dane_stopy.get('nogi_widoczne')) or bool(dane_bok.get('nogi_widoczne'))

    # ── Określ fazę ruchu ────────────────────────────────────────────────────
    faza = 'OCZEKIWANIE'

    # Priorytet 1: Czy mamy zapamiętane odbicie z ostatnich 3 sekund?
    if ostatnie_odbicie and (_time.time() - ostatnie_odbicie.get('czas', 0)) < FOLLOW_THROUGH_SEC:
        faza = 'FOLLOW_THROUGH'
    elif dane_front.get('pilka_wykryta'):
        if dystans_pilka is not None and dystans_pilka <= 200 and dane_front.get('typ_odbicia') is not None:
            faza = 'KONTAKT'
        elif dystans_pilka is None or dystans_pilka > 200:
            faza = 'PRZYGOTOWANIE'

    # ── Checklist gotowości ──────────────────────────────────────────────────
    kat_kolana = dane_bok.get('kat_kolana')
    stopa_ok = bool(dane_stopy.get('nogi_widoczne')) and bool(dane_stopy.get('rozstawienie_ok'))
    if not dane_stopy.get('nogi_widoczne') and nogi_w_kadrze:
        stopa_ok = False

    if kat_kolana is not None:
        kolana_ok = KAT_KOLANO_PRAWIDLOWY_MIN <= kat_kolana <= KAT_KOLANO_PRAWIDLOWY_MAX
    elif kat_kolana_front is not None:
        kolana_ok = KAT_KOLANO_GOTOWOSC_MIN <= kat_kolana_front <= KAT_KOLANO_GOTOWOSC_MAX
    else:
        kolana_ok = False

    lokcie_ok = _lokcie_ok(
        dane_front.get("kat_lokcia_l") if dane_front else None,
        dane_front.get("kat_lokcia_p") if dane_front else None,
    )
    platforma_ok = bool(dane_front.get("nadgarstki_zlaczone", False)) if dane_front else False
    if not platforma_ok and dane_front and lokcie_ok:
        platforma_ok = True
    if faza == 'KONTAKT':
        ruch_ok = bool(dane_bok.get('zamach_wykryty', False))
    else:
        ruch_ok = bool(dane_stopy.get('nogi_widoczne')) or nogi_w_kadrze

    gotowosc = {
        'stopa_ok': stopa_ok,
        'kolana_ok': kolana_ok,
        'platforma_ok': platforma_ok,
        'lokcie_ok': lokcie_ok,
        'ruch_ok': ruch_ok,
    }

    # ── Feedback dla każdej fazy ─────────────────────────────────────────────
    if faza == 'FOLLOW_THROUGH':
        # Użyj zapamiętanego feedbacku z momentu odbicia
        if ostatnie_odbicie:
            feedback = ostatnie_odbicie.get('feedback', 'Odbicie zarejestrowane ✓')
        else:
            feedback = 'Kontroluj pozycję po odbiciu'
        # Nadpisz gotowość danymi z momentu odbicia (jeśli dostępne)
        if ostatnie_odbicie and ostatnie_odbicie.get('gotowosc'):
            gotowosc = ostatnie_odbicie['gotowosc']

    elif faza == 'OCZEKIWANIE':
        if all(gotowosc.values()):
            feedback = 'Świetna pozycja wyjściowa! ✓'
        else:
            feedback = 'Przyjmij swobodną pozycję gotowości'

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
        # FOLLOW_THROUGH — podsumowanie po odbiciu
        # Bądź przychylny: pokaż zielono jeśli większość jest OK
        problemy = []
        if not stopa_ok:
            problemy.append('stopy za blisko')
        if not kolana_ok:
            problemy.append('popraw ugięcie kolan')
        if not platforma_ok:
            problemy.append('złącz dłonie mocniej')
        
        if not problemy:
            feedback = 'Poprawne odbicie! Świetna robota ✓'
        elif len(problemy) == 1:
            feedback = f"Dobre odbicie! Wskazówka: {problemy[0]}"
        else:
            feedback = f"Odbicie OK — popraw: {', '.join(problemy)}"

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
    if 110.0 <= kat <= 145.0:
        return 25
    if kat < 90.0 or kat > 170.0:
        return 3
    if kat < 110.0:
        return int(3 + 22 * (kat - 90.0) / 20.0)
    return int(3 + 22 * (170.0 - kat) / 25.0)


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
        # (ale nawet wtedy daj trochę punktów — gracz próbuje!)
        if kolana_proste:
            wynik["brak_pracy_nog"] = True
            wynik["komunikat_fuzji"] = "Odbicie OK! Spróbuj bardziej zaangażować nogi."
            wynik["ocena_fuzji"] = 42
            return wynik

        punkty = 0
        if kontakt_front:
            punkty += WAGA_KONTAKT_POTWIERDZONY
        punkty += _gradient_kolana(kat_kolana)

        if nadgarstki_zlaczone:
            punkty += WAGA_NADGARSTKI_ZLACZONE
        elif dane_front.get("kat_lokcia_l") is not None:
            punkty += 4

        if zamach_wykryty:
            punkty += WAGA_ZAMACH_WYKRYTY
        elif not kolana_proste:
            punkty += 4

        wynik["ocena_fuzji"] = min(100, punkty)

        # Bardzo pozytywne komunikaty — system chwali gracza
        if punkty >= 85:
            wynik["komunikat_fuzji"] = f"Doskonałe odbicie {typ_odbicia}! ✓ ({punkty}/100)"
        elif punkty >= 65:
            wynik["komunikat_fuzji"] = f"Poprawne odbicie {typ_odbicia} ✓ ({punkty}/100)"
        elif punkty >= 50:
            # Nawet przy średnim wyniku — głównie pozytywny feedback + delikatna wskazówka
            wskazowka = ""
            if not nadgarstki_zlaczone:
                wskazowka = " — spróbuj złączyć dłonie"
            elif not zamach_wykryty:
                wskazowka = " — więcej pracy nóg"
            wynik["komunikat_fuzji"] = f"Dobre odbicie {typ_odbicia}{wskazowka} ({punkty}/100)"
        else:
            wynik["komunikat_fuzji"] = f"Odbicie {typ_odbicia} — pracuj nad techniką ({punkty}/100)"

    else:
        # Piłka w kadrze, ale brak kontaktu — oceniaj pozycję oczekiwania (pozytywnie!)
        wynik["komunikat_fuzji"] = komunikat_kolana or "Dobra pozycja — piłka leci!"
        if kat_kolana is not None and KAT_KOLANO_PRAWIDLOWY_MIN <= kat_kolana <= KAT_KOLANO_PRAWIDLOWY_MAX:
            wynik["ocena_fuzji"] = 50
            wynik["komunikat_fuzji"] = "Świetna pozycja do odbicia! ✓"
        elif kat_kolana is not None and kat_kolana > KAT_KOLANO_ZA_WYSOKI:
            wynik["ocena_fuzji"] = 30
            wynik["komunikat_fuzji"] = "Spróbuj lekko ugiąć kolana"

    return wynik
