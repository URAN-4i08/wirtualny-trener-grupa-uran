import cv2
import mediapipe as mp

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


        # Wyświetlanie okna z nagraniem i narysowanym szkieletem
        cv2.imshow('Wykrywanie punktow - MediaPipe', frame)

        # Zamknij okno naciskając 'q'
        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

# Sprzątanie
video.release()
cv2.destroyAllWindows()