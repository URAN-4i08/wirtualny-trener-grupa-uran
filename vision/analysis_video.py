import cv2
import mediapipe as mp
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logic.coach_engine import check_volleyball_position

# Konfiguracja MediaPipe
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# Ścieżka do wideo
VIDEO_PATH = "data/nagranie_testowe.mp4" 
video = cv2.VideoCapture(VIDEO_PATH)

if not video.isOpened():
    print(f"BŁĄD: Nie można otworzyć pliku {VIDEO_PATH}.")
    exit()

# Inicjalizacja modelu Pose (wykrywanie szkieletu)
with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
    print("Rozpoczynam analizę wideo... Naciśnij 'q' aby przerwać.")

    while video.isOpened():
        ret, frame = video.read()
        if not ret:
            break

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 2. Przetwarzanie klatki - wykrywanie punktów
        results = pose.process(image_rgb)
        
        punkty_ciala = {}

        if results.pose_landmarks:
            # 3. Rysowanie kropek i połączeń (szkieletu) na oryginalnym obrazie
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            # 4. Przechwytywanie wszystkich punktów
            landmarks = results.pose_landmarks.landmark
            
            # 5. Wyciąganie i nazywanie kluczowych punktów (kropek)
            punkty_ciala = {
                "nos": landmarks[mp_pose.PoseLandmark.NOSE.value],
                "lewe_ramie": landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value],
                "prawe_ramie": landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value],
                "lewy_lokiec": landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value],
                "prawy_lokiec": landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value],
                "lewy_nadgarstek": landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value],
                "prawy_nadgarstek": landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value],
                "lewe_biodro": landmarks[mp_pose.PoseLandmark.LEFT_HIP.value],
                "prawe_biodro": landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value],
                "lewe_kolano": landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value],
                "prawe_kolano": landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value],
                "lewa_kostka": landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value],
                "prawa_kostka": landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value],
            }

        # ==============================================================
            # TESTOWANIE POZYCJI SIATKARSKIEJ
            # ==============================================================
            czy_poprawna, komunikat = check_volleyball_position(punkty_ciala)

            # Dobór koloru: Zielony jeśli dobrze, Czerwony jeśli są błędy
            kolor_tekstu = (0, 255, 0) if czy_poprawna else (0, 0, 255)

            # Rysowanie ramki w tle dla lepszej czytelności tekstu
            cv2.rectangle(frame, (0, 0), (800, 40), (0, 0, 0), -1)
            
            # Wyświetlanie komunikatu z coach_engine na ekranie
            cv2.putText(frame, komunikat, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, kolor_tekstu, 2, cv2.LINE_AA)


        # Wyświetlanie okna z nagraniem i narysowanym szkieletem
        cv2.imshow('Wykrywanie punktow - MediaPipe', frame)

        # Zamknij okno naciskając 'q'
        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

# Sprzątanie
video.release()
cv2.destroyAllWindows()