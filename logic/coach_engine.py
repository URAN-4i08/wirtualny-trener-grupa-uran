# coach_engine.py
# Ten moduł zarządza logiką treningową, liczy kąty i ocenia poprawność ćwiczeń

import numpy as np

def calculate_angle(a, b, c):
    """Oblicza kąt między trzema punktami (w stopniach). Punkt 'b' to środek kąta."""
    a = np.array([a.x, a.y])
    b = np.array([b.x, b.y])
    c = np.array([c.x, c.y])
    
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)
    
    if angle > 180.0:
        angle = 360 - angle
        
    return angle

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
        
    if dystans_nadgarstkow > 0.08: 
        komunikaty.append("Zlacz dlonie!")
        pozycja_poprawna = False
        punkty -= 30
        
    if kat_l_lokiec < 155 or kat_p_lokiec < 155:
        komunikaty.append("Wyprostuj lokcie!")
        pozycja_poprawna = False
        punkty -= 40

    if pozycja_poprawna:
        return True, "IDEALNE ODBICIE!", punkty
    else:
        return False, " | ".join(komunikaty), punkty


def evaluate_live_reception_position(punkty_45, punkty_front=None):
    """
    Ocenia pozycję do odbicia dolnego w trybie live.
    Kamera 45° jest obowiązkowa i daje ocenę nóg oraz bazową ocenę rąk.
    Kamera frontowa jest opcjonalna i, jeśli działa, daje dokładniejszą ocenę dłoni i łokci.
    """
    if not punkty_45:
        return {
            "is_correct": False,
            "message": "Nie wykryto sylwetki w kamerze 45°",
            "score": 0,
            "weak_points": ["Brak sylwetki w kamerze 45°"],
            "knee_angle": 0,
            "elbow_angle": 0,
        }

    points_for_arms = punkty_front or punkty_45
    weak_points = []
    score = 100
    knee_angle = 0
    elbow_angle = 0

    try:
        left_knee = calculate_angle(
            punkty_45["lewe_biodro"],
            punkty_45["lewe_kolano"],
            punkty_45["lewa_kostka"],
        )
        right_knee = calculate_angle(
            punkty_45["prawe_biodro"],
            punkty_45["prawe_kolano"],
            punkty_45["prawa_kostka"],
        )
        knee_angle = int((left_knee + right_knee) / 2)

        left_elbow = calculate_angle(
            points_for_arms["lewe_ramie"],
            points_for_arms["lewy_lokiec"],
            points_for_arms["lewy_nadgarstek"],
        )
        right_elbow = calculate_angle(
            points_for_arms["prawe_ramie"],
            points_for_arms["prawy_lokiec"],
            points_for_arms["prawy_nadgarstek"],
        )
        elbow_angle = int((left_elbow + right_elbow) / 2)
        wrist_distance = abs(
            points_for_arms["lewy_nadgarstek"].x - points_for_arms["prawy_nadgarstek"].x
        )
    except KeyError:
        return {
            "is_correct": False,
            "message": "Brak kluczowych punktów szkieletu",
            "score": 0,
            "weak_points": ["MediaPipe zgubił część punktów ciała"],
            "knee_angle": knee_angle,
            "elbow_angle": elbow_angle,
        }

    if knee_angle > 165:
        weak_points.append("Ugnij mocniej kolana przed przyjęciem")
        score -= 30
    elif knee_angle < 90:
        weak_points.append("Pozycja jest zbyt niska")
        score -= 15

    if wrist_distance > 0.08:
        weak_points.append("Złącz dłonie i ustabilizuj platformę")
        score -= 25

    if elbow_angle < 155:
        weak_points.append("Wyprostuj łokcie w momencie przyjęcia")
        score -= 30

    if punkty_front is None:
        weak_points.append("Dodaj kamerę frontową, aby dokładniej ocenić ręce")
        score -= 5

    score = max(0, score)
    is_correct = not weak_points or (len(weak_points) == 1 and punkty_front is None)
    message = "Pozycja gotowa do odbicia" if is_correct else " | ".join(weak_points)

    return {
        "is_correct": is_correct,
        "message": message,
        "score": score,
        "weak_points": weak_points,
        "knee_angle": knee_angle,
        "elbow_angle": elbow_angle,
    }
