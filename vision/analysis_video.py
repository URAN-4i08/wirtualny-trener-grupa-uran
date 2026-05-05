
import sys
import cv2
import os

# Bezpośrednie importy z MediaPipe, żeby ominąć Twój wcześniejszy błąd
from mediapipe.python.solutions import drawing_utils as mp_drawing
from mediapipe.python.solutions import pose as mp_pose
from ultralytics import YOLO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logic.coach_engine import check_volleyball_position

yolo_model = YOLO('yolov8s.pt')

VIDEO_PATH = "data/nagranie_testowe.mp4" 
video = cv2.VideoCapture(VIDEO_PATH)

if not video.isOpened():
    print(f"BŁĄD: Nie można otworzyć pliku {VIDEO_PATH}.")
    exit()

# Zmienne do zapamiętania ostatniej oceny, żeby nie zniknęła za szybko
ostatni_komunikat = "Czekam na odbicie..."
ostatni_kolor = (255, 255, 255)
ostatnie_punkty = 0
pokazuj_ocene_przez = 0  # Licznik klatek

with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
    print("Rozpoczynam analizę wideo... Naciśnij 'q' aby przerwać.")

    while video.isOpened():
        ret, frame = video.read()
        if not ret:
            break

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)
        
        punkty_ciala = {}
        moment_odbicia = False

        if results.pose_landmarks:
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            landmarks = results.pose_landmarks.landmark
            
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

        # Wykrywanie piłki za pomocą YOLO
        results_yolo = yolo_model(frame, conf=0.4)
        
        ball_detections = []
        for result in results_yolo:
            for box in result.boxes:
                cls = int(box.cls[0])
                if result.names[cls] == 'sports ball':
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    area = (x2 - x1) * (y2 - y1)
                    if area > 200:
                        ball_detections.append(box)
        
        ball_positions = []
        for box in ball_detections:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(frame, 'Pilka', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            ball_center = ((x1 + x2) // 2, (y1 + y2) // 2)
            ball_positions.append(ball_center)
        
        # Obliczanie odległości i wykrywanie MOMENTU ODBICIA
        if punkty_ciala and ball_positions:
            for ball_center in ball_positions:
                if 'lewy_nadgarstek' in punkty_ciala:
                    wrist_x = int(punkty_ciala['lewy_nadgarstek'].x * frame.shape[1])
                    wrist_y = int(punkty_ciala['lewy_nadgarstek'].y * frame.shape[0])
                    distance_left = ((ball_center[0] - wrist_x)**2 + (ball_center[1] - wrist_y)**2)**0.5
                    
                    if distance_left < 100:  # Piłka jest przy rękach!
                        cv2.line(frame, ball_center, (wrist_x, wrist_y), (0, 255, 255), 2)
                        moment_odbicia = True
                
                if 'prawy_nadgarstek' in punkty_ciala:
                    wrist_x = int(punkty_ciala['prawy_nadgarstek'].x * frame.shape[1])
                    wrist_y = int(punkty_ciala['prawy_nadgarstek'].y * frame.shape[0])
                    distance_right = ((ball_center[0] - wrist_x)**2 + (ball_center[1] - wrist_y)**2)**0.5
                    
                    if distance_right < 100:  # Piłka jest przy rękach!
                        cv2.line(frame, ball_center, (wrist_x, wrist_y), (0, 255, 255), 2)
                        moment_odbicia = True

        # ==============================================================
        # LOGIKA OCENIANIA (TYLKO PODCZAS ODBICIA)
        # ==============================================================
        if moment_odbicia:
            # Pobieramy punkty i oceny z coach_engine
            czy_poprawna, komunikat, punkty = check_volleyball_position(punkty_ciala)
            
            # Aktualizujemy to, co widać na ekranie
            ostatni_komunikat = f"PUNKTY: {punkty}/100 | {komunikat}"
            ostatni_kolor = (0, 255, 0) if czy_poprawna else (0, 0, 255)
            pokazuj_ocene_przez = 30  # Pokazuj ten komunikat przez kolejne 30 klatek wideo (ok. 1 sekunda)
            
        # Rysowanie tła pod tekst
        cv2.rectangle(frame, (0, 0), (800, 40), (0, 0, 0), -1)
        
        # Sprawdzamy co wyświetlić na górnym pasku
        if pokazuj_ocene_przez > 0:
            cv2.putText(frame, ostatni_komunikat, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, ostatni_kolor, 2, cv2.LINE_AA)
            pokazuj_ocene_przez -= 1
        else:
            cv2.putText(frame, "Czekam na odbicie...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        cv2.imshow('CyberTrener - Analiza Uderzenia', frame)

        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

video.release()
cv2.destroyAllWindows()