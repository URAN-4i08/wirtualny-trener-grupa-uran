# coach_engine.py
# Ten moduł będzie zarządzał logiką treningową, liczył kąty i oceniał poprawność ćwiczeń

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
    Zwraca krotkę: (True/False, "Komunikat zwrotny")
    """
    if not punkty_ciala:
        return False, "Nie wykryto sylwetki"
    
    try:
        # Pobieranie potrzebnych punktów
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
        return False, "Brak kluczowych punktów szkieletu"

    # 1. Obliczanie kątów kolan
    kat_l_kolano = calculate_angle(l_biodro, l_kolano, l_kostka)
    kat_p_kolano = calculate_angle(p_biodro, p_kolano, p_kostka)
    
    # 2. Obliczanie kątów łokci
    kat_l_lokiec = calculate_angle(l_ramie, l_lokiec, l_nadgarstek)
    kat_p_lokiec = calculate_angle(p_ramie, p_lokiec, p_nadgarstek)
    
    # 3. Odległość nadgarstków od siebie (w osi X) - używamy znormalizowanych wartości MediaPipe
    dystans_nadgarstkow = abs(l_nadgarstek.x - p_nadgarstek.x)

    komunikaty = []
    pozycja_poprawna = True

    # Sprawdzanie warunków z pewną tolerancją błędów
    if kat_l_kolano > 165 or kat_p_kolano > 165:
        komunikaty.append("Ugnij kolana!")
        pozycja_poprawna = False
        
    if dystans_nadgarstkow > 0.08: # Jeśli dłonie są zbyt daleko od siebie
        komunikaty.append("Zlacz dlonie!")
        pozycja_poprawna = False
        
    if kat_l_lokiec < 155 or kat_p_lokiec < 155:
        komunikaty.append("Wyprostuj lokcie!")
        pozycja_poprawna = False

    if pozycja_poprawna:
        return True, "POZYCJA IDEALNA!"
    else:
        # Zwracamy połączone komunikaty, jeśli jest więcej błędów
        return False, " | ".join(komunikaty)