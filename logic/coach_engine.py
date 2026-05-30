# coach_engine.py
# Ten moduł zarządza logiką treningową, liczy kąty i ocenia poprawność ćwiczeń

import math

def calculate_angle(a, b, c):
    """Oblicza kąt między trzema punktami (w stopniach). Punkt 'b' to środek kąta."""
    radians = math.atan2(c.y - b.y, c.x - b.x) - math.atan2(a.y - b.y, a.x - b.x)
    angle = abs(radians * 180.0 / math.pi)

    if angle > 180.0:
        angle = 360 - angle

    return angle


class VolleyballPostureEvaluator:
    """
    Stabilniejsza ocena pozycji do odbicia dolnego.
    - stosuje EMA na kątach/dystansie
    - używa histerezy progów, żeby komunikaty nie "mrugały" co klatkę
    """

    def __init__(
        self,
        ema_alpha: float = 0.35,
        knee_straight_on: float = 172.0,   # Poszerzono margines (było 166)
        knee_straight_off: float = 165.0,  # Poszerzono margines (było 160)
        knee_low_on: float = 50.0,         # Poszerzono margines (było 62)
        knee_low_off: float = 60.0,        # Poszerzono margines (było 70)
        elbow_warn_on: float = 148.0,      # Pół-surowy wymóg wyprostowanych rąk
        elbow_warn_off: float = 154.0,     # Pół-surowy wymóg wyprostowanych rąk
        hands_warn_on: float = 0.30,       # Pół-surowy wymóg złączonych dłoni
        hands_warn_off: float = 0.25,      # Pół-surowy wymóg złączonych dłoni
        platform_warn_on: float = -0.05,
        platform_warn_off: float = 0.0,
    ):
        self.ema_alpha = float(ema_alpha)
        self.knee_straight_on = float(knee_straight_on)
        self.knee_straight_off = float(knee_straight_off)
        self.knee_low_on = float(knee_low_on)
        self.knee_low_off = float(knee_low_off)
        self.elbow_warn_on = float(elbow_warn_on)
        self.elbow_warn_off = float(elbow_warn_off)
        self.hands_warn_on = float(hands_warn_on)
        self.hands_warn_off = float(hands_warn_off)
        self.platform_warn_on = float(platform_warn_on)
        self.platform_warn_off = float(platform_warn_off)

        self._ema_left_knee = None
        self._ema_right_knee = None
        self._ema_left_elbow = None
        self._ema_right_elbow = None
        self._ema_hands_ratio = None
        self._ema_platform_drop = None

        self._warn_knees_straight = False
        self._warn_knees_low = False
        self._warn_elbows = False
        self._warn_hands = False
        self._warn_platform = False

    def _ema(self, prev, value):
        if prev is None:
            return float(value)
        a = self.ema_alpha
        return (a * float(value)) + ((1.0 - a) * float(prev))

    def evaluate(self, punkty_ciala):
        if not punkty_ciala:
            return False, "Nie wykryto sylwetki", 0

        try:
            l_biodro = punkty_ciala["lewe_biodro"]
            l_kolano = punkty_ciala["lewe_kolano"]
            l_kostka = punkty_ciala["lewa_kostka"]

            p_biodro = punkty_ciala["prawe_biodro"]
            p_kolano = punkty_ciala["prawe_kolano"]
            p_kostka = punkty_ciala["prawa_kostka"]

            l_nadgarstek = punkty_ciala["lewy_nadgarstek"]
            p_nadgarstek = punkty_ciala["prawy_nadgarstek"]

            l_lokiec = punkty_ciala["lewy_lokiec"]
            l_ramie = punkty_ciala["lewe_ramie"]
            p_lokiec = punkty_ciala["prawy_lokiec"]
            p_ramie = punkty_ciala["prawe_ramie"]
            l_bark = punkty_ciala["lewe_ramie"]
            p_bark = punkty_ciala["prawe_ramie"]
        except KeyError:
            return False, "Brak kluczowych punktów szkieletu", 0

        left_knee = calculate_angle(l_biodro, l_kolano, l_kostka)
        right_knee = calculate_angle(p_biodro, p_kolano, p_kostka)
        left_elbow = calculate_angle(l_ramie, l_lokiec, l_nadgarstek)
        right_elbow = calculate_angle(p_ramie, p_lokiec, p_nadgarstek)
        wrist_dist = math.dist((l_nadgarstek.x, l_nadgarstek.y), (p_nadgarstek.x, p_nadgarstek.y))
        shoulder_width = max(0.08, abs(l_bark.x - p_bark.x))
        hands_ratio = wrist_dist / shoulder_width
        avg_wrist_y = (l_nadgarstek.y + p_nadgarstek.y) / 2
        avg_elbow_y = (l_lokiec.y + p_lokiec.y) / 2
        platform_drop = avg_wrist_y - avg_elbow_y

        self._ema_left_knee = self._ema(self._ema_left_knee, left_knee)
        self._ema_right_knee = self._ema(self._ema_right_knee, right_knee)
        self._ema_left_elbow = self._ema(self._ema_left_elbow, left_elbow)
        self._ema_right_elbow = self._ema(self._ema_right_elbow, right_elbow)
        self._ema_hands_ratio = self._ema(self._ema_hands_ratio, hands_ratio)
        self._ema_platform_drop = self._ema(self._ema_platform_drop, platform_drop)

        knee_value = max(self._ema_left_knee, self._ema_right_knee)
        knee_low_value = min(self._ema_left_knee, self._ema_right_knee)
        elbow_value = min(self._ema_left_elbow, self._ema_right_elbow)
        hands_value = self._ema_hands_ratio
        platform_value = self._ema_platform_drop

        if not self._warn_knees_straight:
            self._warn_knees_straight = knee_value > self.knee_straight_on
        else:
            self._warn_knees_straight = knee_value > self.knee_straight_off

        if not self._warn_knees_low:
            self._warn_knees_low = knee_low_value < self.knee_low_on
        else:
            self._warn_knees_low = knee_low_value < self.knee_low_off

        if not self._warn_hands:
            self._warn_hands = hands_value > self.hands_warn_on
        else:
            self._warn_hands = hands_value > self.hands_warn_off

        if not self._warn_elbows:
            self._warn_elbows = elbow_value < self.elbow_warn_on
        else:
            self._warn_elbows = elbow_value < self.elbow_warn_off

        if not self._warn_platform:
            self._warn_platform = platform_value < self.platform_warn_on
        else:
            self._warn_platform = platform_value < self.platform_warn_off

        komunikaty = []
        punkty = 100

        if self._warn_knees_straight:
            komunikaty.append("Ugnij kolana")
            punkty -= 30

        if self._warn_knees_low:
            komunikaty.append("Wstan odrobine wyzej")
            punkty -= 15

        if self._warn_hands:
            komunikaty.append("Zlacz dlonie")
            punkty -= 25

        if self._warn_elbows:
            komunikaty.append("Wyprostuj lokcie")
            punkty -= 30

        if self._warn_platform:
            komunikaty.append("Ustaw przedramiona nizej")
            punkty -= 20

        pozycja_poprawna = len(komunikaty) == 0
        if pozycja_poprawna:
            return True, "Dobra platforma do odbicia dolnego", max(0, min(100, punkty))
        return False, " | ".join(komunikaty), max(0, min(100, punkty))

def check_volleyball_position(punkty_ciala):
    """
    Sprawdza, czy sylwetka znajduje się w poprawnej pozycji do odbicia dolnego.
    Zwraca krotkę: (True/False, "Komunikat zwrotny", Punkty)
    """
    if not punkty_ciala:
        return False, "Nie wykryto sylwetki", 0
    
    try:
        l_biodro = punkty_ciala["lewe_biodro"]
        l_kolano = punkty_ciala["lewe_kolano"]
        l_kostka = punkty_ciala["lewa_kostka"]
        
        p_biodro = punkty_ciala["prawe_biodro"]
        p_kolano = punkty_ciala["prawe_kolano"]
        p_kostka = punkty_ciala["prawa_kostka"]
        
        l_nadgarstek = punkty_ciala["lewy_nadgarstek"]
        p_nadgarstek = punkty_ciala["prawy_nadgarstek"]
        
        l_lokiec = punkty_ciala["lewy_lokiec"]
        l_ramie = punkty_ciala["lewe_ramie"]
        p_lokiec = punkty_ciala["prawy_lokiec"]
        p_ramie = punkty_ciala["prawe_ramie"]
        
    except KeyError:
        return False, "Brak kluczowych punktów szkieletu", 0

    kat_l_kolano = calculate_angle(l_biodro, l_kolano, l_kostka)
    kat_p_kolano = calculate_angle(p_biodro, p_kolano, p_kostka)
    
    kat_l_lokiec = calculate_angle(l_ramie, l_lokiec, l_nadgarstek)
    kat_p_lokiec = calculate_angle(p_ramie, p_lokiec, p_nadgarstek)
    
    dystans_nadgarstkow = abs(l_nadgarstek.x - p_nadgarstek.x)

    komunikaty = []
    pozycja_poprawna = True
    punkty = 100  # Startujemy z maksymalną notą

    # Sprawdzanie warunków i odejmowanie punktów za błędy
    if kat_l_kolano > 165 or kat_p_kolano > 165:
        komunikaty.append("Ugnij kolana!")
        pozycja_poprawna = False
        punkty -= 30
        
    if dystans_nadgarstkow > 0.07: 
        komunikaty.append("Zlacz dlonie!")
        pozycja_poprawna = False
        punkty -= 30
        
    if kat_l_lokiec < 152 or kat_p_lokiec < 152:
        komunikaty.append("Wyprostuj lokcie!")
        pozycja_poprawna = False
        punkty -= 40

    if pozycja_poprawna:
        return True, "IDEALNE ODBICIE!", punkty
    else:
        return False, " | ".join(komunikaty), punkty
