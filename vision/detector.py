# detector.py
# ModuĹ‚ do detekcji obiektĂłw za pomocÄ… YOLO

from ultralytics import YOLO
import cv2
import numpy as np


class BallDetector:
    """Detektor piĹ‚ki za pomocÄ… YOLO"""

    def __init__(self, model_path="yolov8s.pt", conf_threshold=0.4):
        """
        Inicjalizacja detektora piĹ‚ki

        Args:
            model_path: ĹšcieĹĽka do modelu YOLO
            conf_threshold: PrĂłg confidence dla detekcji
        """
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.min_area = 200  # Minimalna powierzchnia piĹ‚ki w pikselach

    def detect_ball(self, frame):
        """
        Wykrywa piĹ‚kÄ™ na klatce

        Args:
            frame: Obraz do analizy

        Returns:
            list: Lista pozycji piĹ‚ek
        """
        results = self.model(frame, conf=self.conf_threshold, verbose=False)

        ball_detections = []

        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                if result.names[cls] == 'sports ball':
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    area = (x2 - x1) * (y2 - y1)

                    if area > self.min_area:
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        ball_detections.append({
                            'bbox': (x1, y1, x2, y2),
                            'center': (center_x, center_y),
                            'area': area,
                            'confidence': float(box.conf[0])
                        })

        return ball_detections

    def draw_detections(self, frame, detections, color=(255, 0, 0)):
        """
        Rysuje wykrycia piĹ‚ek na klatce

        Args:
            frame: Obraz do narysowania
            detections: Lista detekcji
            color: Kolor do rysowania (BGR)
        """
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            center_x, center_y = detection['center']

            # ProstokÄ…t wokĂłĹ‚ piĹ‚ki
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Ĺšrodek piĹ‚ki
            cv2.circle(frame, (center_x, center_y), 4, color, -1)

            # Etykieta
            cv2.putText(
                frame,
                f"Pilka ({detection['confidence']:.2f})",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )

    def is_ball_near_point(self, ball_center, point, distance_threshold=100):
        """
        Sprawdza czy piĹ‚ka jest blisko punktu

        Args:
            ball_center: Ĺšrodek piĹ‚ki (x, y)
            point: Punkt referencyjny (x, y)
            distance_threshold: OdlegĹ‚oĹ›Ä‡ progowa w pikselach

        Returns:
            bool: True jeĹ›li piĹ‚ka jest blisko punktu
        """
        distance = ((ball_center[0] - point[0])**2 + (ball_center[1] - point[1])**2)**0.5
        return distance < distance_threshold
