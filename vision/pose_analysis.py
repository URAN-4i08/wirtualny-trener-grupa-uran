# pose_analysis.py
# ModuĹ‚ do analizy pozy i szkieletu za pomocÄ… MediaPipe

import mediapipe as mp
import numpy as np

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose


class PoseAnalyzer:
    """Analizator pozy ciaĹ‚a za pomocÄ… MediaPipe"""

    def __init__(self, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        """
        Inicjalizacja analyzera pozy

        Args:
            min_detection_confidence: PrĂłg confidence dla detekcji
            min_tracking_confidence: PrĂłg confidence dla trackingu
        """
        self.pose = mp_pose.Pose(
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.last_landmarks = None

    def analyze_frame(self, image_rgb):
        """
        Analizuje klatkÄ™ i zwraca punkty ciaĹ‚a

        Args:
            image_rgb: Obraz w formacie RGB

        Returns:
            dict: SĹ‚ownik z punktami ciaĹ‚a lub None jeĹ›li nie wykryto
        """
        results = self.pose.process(image_rgb)

        if not results.pose_landmarks:
            return None

        self.last_landmarks = results.pose_landmarks

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

        return punkty_ciala

    def draw_landmarks(self, frame, image_landmarks):
        """
        Rysuje punkty i poĹ‚Ä…czenia na klatce

        Args:
            frame: Obraz do narysowania
            image_landmarks: Punkty do narysowania
        """
        mp_drawing.draw_landmarks(frame, image_landmarks, mp_pose.POSE_CONNECTIONS)

    def convert_to_pixel_coords(self, landmarks, frame_width, frame_height):
        """
        Konwertuje znormalizowane wspĂłĹ‚rzÄ™dne na piksele

        Args:
            landmarks: SĹ‚ownik znormalizowanych wspĂłĹ‚rzÄ™dnych
            frame_width: SzerokoĹ›Ä‡ klatki
            frame_height: WysokoĹ›Ä‡ klatki

        Returns:
            dict: SĹ‚ownik wspĂłĹ‚rzÄ™dnych w pikselach
        """
        pixel_coords = {}
        for name, landmark in landmarks.items():
            pixel_coords[name] = (
                int(landmark.x * frame_width),
                int(landmark.y * frame_height)
            )
        return pixel_coords

    def close(self):
        """Zamyka detektor pozy"""
        self.pose.close()
