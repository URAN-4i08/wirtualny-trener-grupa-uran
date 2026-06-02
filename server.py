import asyncio
import os
import shutil
import sys
import threading
import time

import cv2
import requests
from fastapi import FastAPI, File, Header, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

# Wymuś CPU path dla MediaPipe na macOS, żeby uniknąć crashy GL.
os.environ.setdefault("MEDIAPIPE_DISABLE_GPU", "1")

import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2
from ultralytics import YOLO
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# Add the root directory to path to import logic modules.
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from logic.coach_engine import calculate_angle, check_volleyball_position, VolleyballPostureEvaluator
from logic.biomechanics import (
    analizuj_front,
    analizuj_bok,
    fuzja_sensorow,
    WristTrajectoryTracker,
    analizuj_stopy,
    analizuj_faze,
)
from audio.voice_control import get_announcer
from audio import speech_recognition as vosk_stt

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "data", "uploads")
CACHE_DIR = os.path.join(UPLOAD_DIR, "processed")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

load_dotenv(os.path.join(os.path.dirname(__file__), "frontend", ".env"))
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")
supabase_client: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Pomyślnie zainicjalizowano Supabase w backendzie.")
    except Exception as e:
        print(f"Błąd inicjalizacji Supabase: {e}")

def save_training_session(user_id, source, start_time, end_time, stats, access_token=None):
    if not SUPABASE_URL or not SUPABASE_KEY or not user_id:
        print("[supabase] Brak konfiguracji lub user_id, pomijam zapis treningu.")
        return

    if not access_token:
        print("[supabase] Brak tokenu sesji użytkownika, pomijam zapis treningu.")
        return

    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

        training_payload = {
            'user_id': user_id,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'source': source,
            'overall_score': stats.get('overall_score', 0),
            'status': 'completed'
        }

        training_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/trainings",
            headers=headers,
            json=training_payload,
            timeout=15,
        )
        if not training_response.ok:
            print(f"[supabase] Błąd zapisu treningu: {training_response.status_code} {training_response.text}")
            return

        training_data = training_response.json()
        if not training_data:
            print("[supabase] Baza nie zwróciła id treningu po zapisie.")
            return

        training_id = training_data[0]['id']

        stats_payload = {
            'training_id': training_id,
            'total_contacts': stats.get('total_contacts', 0),
            'avg_knee_angle': stats.get('avg_knee_angle', 0),
            'posture_warnings_count': stats.get('posture_warnings_count', 0),
            'avg_contact_score': stats.get('avg_contact_score', 0)
        }
        stats_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/training_stats",
            headers=headers,
            json=stats_payload,
            timeout=15,
        )
        if not stats_response.ok:
            print(f"[supabase] Błąd zapisu statystyk: {stats_response.status_code} {stats_response.text}")
            return

        print(f"Zapisano trening dla użytkownika {user_id}")
    except Exception as e:
        print(f"Błąd zapisu do Supabase: {e}")

state_lock = threading.Lock()

source_state = {
    "mode": "camera",
    "cameraIndex": 0,
    "cameraIndex2": None,
    "videoPath": None,
    "videoName": None,
    "jobId": 0,
    "userId": None,
    "accessToken": None,
    # Tryb kamery: "front" (kamera frontowa), "side" (kamera boczna), "dual" (obie)
    "cameraMode": "front",
}

preprocessed_state = {
    "jobId": 0,
    "status": "idle",
    "progress": 0,
    "framePaths": [],
    "metrics": [],
    "fps": 25,
    "error": None,
}

global_metrics = {
    "score": 0,
    "kneeAngle": 120,
    "totalContacts": 0,
    "warnings": None,
    "postureWarnings": None,
    "contactWarning": None,
    "contactScore": None,
    "isContact": False,
    "hasPose": False,
    "hasBall": False,
    "status": "Oczekiwanie na uruchomienie analizy",
    "source": "camera",
    "isAnalyzing": False,
    "videoProcessingStatus": "idle",
    "videoProcessingProgress": 0,
    # ── Pola biomechaniczne (nowe) ────────────────────────────────────────────
    # Aktualizowane przez analizuj_front / analizuj_bok / fuzja_sensorow
    "cameraMode": "front",          # "front" / "side" / "dual"
    "fuzjaOcena": 0,                # wynik fuzji 0-100 → ProgressBar
    "komunikatFuzji": None,         # komunikat tekstowy → pole GUI
    "brakPracyNog": False,          # alert krytyczny → czerwone pole GUI
    "typOdbicia": None,             # "DOLNE" / "GORNE" / None → etykieta GUI
    "komunikatKolana": None,        # komunikat boczny → pole GUI
    "katBiodra": None,              # kąt biodrowy (stopnie)
    "dystansPilkaRece": None,       # odległość piłki od rąk (px)
    "zamachWykryty": False,         # czy wykryto zamach
    "dynamikaZamachu": None,        # opis dynamiki zamachu
    # ── Pola analizy stóp i fazy ruchu ───────────────────────────────────────
    "fazaRuchu": "OCZEKIWANIE",
    "rozstawienieStop": None,
    "balansStop": None,
    "gotowoscPrzedOdbiciem": None,
    "feedbackFazy": None,
}

yolo_model = YOLO(os.getenv("YOLO_MODEL_PATH", "yolov8n.pt"))
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
pose_tracker = None

LIVE_STREAM_FPS = int(os.getenv("LIVE_STREAM_FPS", "20"))
LIVE_STREAM_WIDTH = int(os.getenv("LIVE_STREAM_WIDTH", "960"))
LIVE_ANALYSIS_WIDTH = int(os.getenv("LIVE_ANALYSIS_WIDTH", "640"))
LIVE_POSE_EVERY_N_FRAMES = int(os.getenv("LIVE_POSE_EVERY_N_FRAMES", "1"))
# Piłkę wykrywamy CO KLATKĘ — jest szybka, nie można jej przegapić
LIVE_BALL_EVERY_N_FRAMES = int(os.getenv("LIVE_BALL_EVERY_N_FRAMES", "1"))
LIVE_NO_POSE_GRACE_FRAMES = int(os.getenv("LIVE_NO_POSE_GRACE_FRAMES", "4"))
LIVE_POSE_HOLD_FRAMES = int(os.getenv("LIVE_POSE_HOLD_FRAMES", "10"))
LIVE_POSE_SMOOTH_ALPHA = float(os.getenv("LIVE_POSE_SMOOTH_ALPHA", "0.35"))
LIVE_MESSAGE_STABLE_FRAMES = int(os.getenv("LIVE_MESSAGE_STABLE_FRAMES", "8")) # ok. 0.4s stabilności - szybsza reakcja, ale wciąż bez migotania
LIVE_HINT_MIN_INTERVAL_SEC = float(os.getenv("LIVE_HINT_MIN_INTERVAL_SEC", "1.5")) # min. 1.5 sekundy między komunikatami - naturalniejsze tempo
# Ile klatek utrzymujemy stan "isContact" w GUI po wykryciu odbicia
LIVE_CONTACT_HOLD_FRAMES = int(os.getenv("LIVE_CONTACT_HOLD_FRAMES", "40"))

class PoseLandmarkStabilizer:
    def __init__(self, alpha=0.35, hold_frames=10, min_visibility=0.35):
        self.alpha = float(alpha)
        self.hold_frames = int(hold_frames)
        self.min_visibility = float(min_visibility)
        self._last_smoothed = None
        self._missing_streak = 0

    def _blend(self, prev, curr):
        a = self.alpha
        out = landmark_pb2.NormalizedLandmarkList()
        for p, c in zip(prev.landmark, curr.landmark):
            lm = out.landmark.add()
            lm.x = (1 - a) * p.x + a * c.x
            lm.y = (1 - a) * p.y + a * c.y
            lm.z = (1 - a) * p.z + a * c.z
            lm.visibility = (1 - a) * getattr(p, "visibility", 0.0) + a * getattr(c, "visibility", 0.0)
            if hasattr(c, "presence"):
                lm.presence = (1 - a) * getattr(p, "presence", 0.0) + a * getattr(c, "presence", 0.0)
        return out

    def update(self, pose_landmarks):
        """
        Zwraca landmarki do rysowania/analizy:
        - gdy detekcja jest -> wygładzone landmarki
        - gdy brak detekcji -> ostatnie landmarki (przez hold_frames)
        """
        if pose_landmarks and pose_landmarks.landmark:
            self._missing_streak = 0
            curr = landmark_pb2.NormalizedLandmarkList()
            curr.landmark.extend(pose_landmarks.landmark)

            if self._last_smoothed is None or len(self._last_smoothed.landmark) != len(curr.landmark):
                self._last_smoothed = curr
            else:
                self._last_smoothed = self._blend(self._last_smoothed, curr)
            return self._last_smoothed, True

        self._missing_streak += 1
        if self._last_smoothed is not None and self._missing_streak <= self.hold_frames:
            return self._last_smoothed, False
        return None, False

    def last_landmarks(self):
        return self._last_smoothed


class MessageDebouncer:
    def __init__(self, stable_frames=6):
        self.stable_frames = int(stable_frames)
        self._candidate = None
        self._count = 0
        self._current = None

    def update(self, message):
        if message == self._current:
            self._candidate = None
            self._count = 0
            return self._current

        if message != self._candidate:
            self._candidate = message
            self._count = 1
            return self._current

        self._count += 1
        if self._count >= self.stable_frames:
            self._current = self._candidate
            self._candidate = None
            self._count = 0
        return self._current


live_pose_stabilizer = PoseLandmarkStabilizer(
    alpha=LIVE_POSE_SMOOTH_ALPHA,
    hold_frames=LIVE_POSE_HOLD_FRAMES,
)
live_posture_evaluator = VolleyballPostureEvaluator()
live_posture_debouncer = MessageDebouncer(stable_frames=LIVE_MESSAGE_STABLE_FRAMES)
live_contact_debouncer = MessageDebouncer(stable_frames=max(3, LIVE_MESSAGE_STABLE_FRAMES // 2))


def get_pose_tracker():
    global pose_tracker
    if pose_tracker is not None:
        return pose_tracker
    pose_tracker = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    return pose_tracker


def build_live_status(metrics):
    if metrics.get("isContact"):
        return "Wykryto moment odbicia piłki"
    if metrics.get("hasPose"):
        if metrics.get("postureWarnings"):
            return "Wykryto błąd postawy — zobacz podpowiedź obok"
        return "Sylwetka w kadrze — pozycja wygląda dobrze"
    return "Szukam sylwetki w kadrze..."


def stabilize_live_metrics(current, previous, no_pose_streak):
    if not previous:
        return current, 0

    if current.get("hasPose"):
        return current, 0

    no_pose_streak += 1
    if no_pose_streak >= LIVE_NO_POSE_GRACE_FRAMES:
        return current, no_pose_streak

    stabilized = {**current}
    for key in (
        "postureWarnings",
        "warnings",
        "score",
        "kneeAngle",
        "totalContacts",
        "hasPose",
        "hasBall",
        "contactWarning",
        "contactScore",
        "isContact",
    ):
        if key in previous:
            stabilized[key] = previous[key]
    return stabilized, no_pose_streak


def update_metrics(**kwargs):
    kwargs.pop("_bodyPoints", None)
    kwargs.pop("_ballCenters", None)
    with state_lock:
        old_posture = global_metrics.get("postureWarnings")
        old_contact = global_metrics.get("contactWarning")
        is_analyzing = global_metrics.get("isAnalyzing")
        global_metrics.update(kwargs)
        new_posture = global_metrics.get("postureWarnings")
        new_contact = global_metrics.get("contactWarning")
        is_analyzing = global_metrics.get("isAnalyzing", is_analyzing)

    if "postureWarnings" in kwargs or "contactWarning" in kwargs:
        get_announcer().handle_metrics_change(
            old_posture,
            new_posture,
            old_contact,
            new_contact,
            bool(is_analyzing),
        )


def snapshot_metrics():
    with state_lock:
        return global_metrics.copy()


def snapshot_source():
    with state_lock:
        return source_state.copy()


def snapshot_preprocessed():
    with state_lock:
        return {
            **preprocessed_state,
            "framePaths": list(preprocessed_state["framePaths"]),
            "metrics": list(preprocessed_state["metrics"]),
        }


def get_capture_source():
    current_source = snapshot_source()

    if current_source["mode"] == "file" and current_source["videoPath"]:
        return current_source["videoPath"], current_source

    return int(current_source["cameraIndex"]), current_source


def stop_current_analysis(status="Analiza przerwana"):
    with state_lock:
        source_state.update(
            {
                "mode": "stopped",
                "videoPath": None,
                "videoName": None,
                "jobId": source_state["jobId"] + 1,
            }
        )
        preprocessed_state.update(
            {
                "jobId": source_state["jobId"],
                "status": "idle",
                "progress": 0,
                "framePaths": [],
                "metrics": [],
                "error": None,
            }
        )

    update_metrics(
        isAnalyzing=False,
        status=status,
        warnings=None,
        postureWarnings=None,
        contactWarning=None,
        contactScore=None,
        isContact=False,
        videoProcessingStatus="idle",
        videoProcessingProgress=0,
    )


def build_body_points(landmarks):
    return {
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
        # Punkty dodatkowe dla biomechanics.py (analizuj_front — detekcja odbicia górnego)
        "lewe_oko": landmarks[mp_pose.PoseLandmark.LEFT_EYE.value],
        "prawe_oko": landmarks[mp_pose.PoseLandmark.RIGHT_EYE.value],
        # Punkty stóp dla analizuj_stopy()
        "lewa_stopa": landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value],
        "prawa_stopa": landmarks[mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value],
        "lewa_pieta": landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value],
        "prawa_pieta": landmarks[mp_pose.PoseLandmark.RIGHT_HEEL.value],
    }


def update_knee_angle(body_points):
    left_angle = calculate_angle(
        body_points["lewe_biodro"],
        body_points["lewe_kolano"],
        body_points["lewa_kostka"],
    )
    right_angle = calculate_angle(
        body_points["prawe_biodro"],
        body_points["prawe_kolano"],
        body_points["prawa_kostka"],
    )
    update_metrics(kneeAngle=int((left_angle + right_angle) / 2))


def calculate_knee_angle_value(body_points):
    left_angle = calculate_angle(
        body_points["lewe_biodro"],
        body_points["lewe_kolano"],
        body_points["lewa_kostka"],
    )
    right_angle = calculate_angle(
        body_points["prawe_biodro"],
        body_points["prawe_kolano"],
        body_points["prawa_kostka"],
    )
    return int((left_angle + right_angle) / 2)


def find_ball_positions(frame):
    """
    Wykrywa piłkę przez YOLO i rysuje czysty bbox na klatce.
    NIE rysuje tekstu na klatce — etykieta trafi do HUD GUI przez WebSocket.
    Zwraca listę (cx, cy) środków.
    """
    # conf=0.25: niższy próg = więcej detekcji, mniej missów w ruchu
    results_yolo = yolo_model(frame, conf=0.25, verbose=False)
    ball_positions = []

    for result in results_yolo:
        for box in result.boxes:
            cls = int(box.cls[0])
            if result.names[cls] != "sports ball":
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            area = (x2 - x1) * (y2 - y1)
            # Zmniejszony minimalny obszar (80 px²) — piłka w ruchu może być mała
            if area <= 80:
                continue

            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            # Czysty, subtelny bbox — tylko ramka i wypełniony środek
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)
            # Mały środek piłki — białe koło
            cv2.circle(frame, (cx, cy), 5, (255, 255, 255), -1)

            ball_positions.append((cx, cy))

    return ball_positions



def point_to_segment_distance(point, start, end):
    px, py = point
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    length_squared = dx * dx + dy * dy

    if length_squared == 0:
        return ((px - sx) ** 2 + (py - sy) ** 2) ** 0.5

    t = max(0, min(1, ((px - sx) * dx + (py - sy) * dy) / length_squared))
    closest_x = sx + t * dx
    closest_y = sy + t * dy
    return ((px - closest_x) ** 2 + (py - closest_y) ** 2) ** 0.5


def body_point_to_pixel(frame, point):
    return int(point.x * frame.shape[1]), int(point.y * frame.shape[0])


def forearm_segments(frame, body_points):
    return [
        (
            body_point_to_pixel(frame, body_points["lewy_lokiec"]),
            body_point_to_pixel(frame, body_points["lewy_nadgarstek"]),
        ),
        (
            body_point_to_pixel(frame, body_points["prawy_lokiec"]),
            body_point_to_pixel(frame, body_points["prawy_nadgarstek"]),
        ),
    ]


def nearest_ball_to_forearms(frame, body_points, ball_positions):
    if not body_points or not ball_positions:
        return None, None

    segments = forearm_segments(frame, body_points)
    nearest_ball = None
    nearest_distance = None

    for ball_center in ball_positions:
        distance = min(point_to_segment_distance(ball_center, start, end) for start, end in segments)
        if nearest_distance is None or distance < nearest_distance:
            nearest_distance = distance
            nearest_ball = ball_center

    return nearest_ball, nearest_distance


def draw_forearm_contact(frame, body_points, ball_center, is_contact=False):
    """
    Rysuje linie przedramion.
    Podczas kontaktu z piłką — żółty akcent, bez kontaktu — prawie niewidoczne.
    """
    if is_contact:
        color = (0, 230, 255)  # żółty akcent przy odbiciu
        thickness = 3
    else:
        color = (80, 80, 80)   # ciemny szary — subtelny, nie przeszkadza
        thickness = 1
    for start, end in forearm_segments(frame, body_points):
        cv2.line(frame, start, end, color, thickness)
    if ball_center and is_contact:
        cv2.circle(frame, ball_center, 10, (0, 230, 255), 2)



def is_ball_close_to_forearms(frame, body_points, ball_positions):
    ball_center, distance = nearest_ball_to_forearms(frame, body_points, ball_positions)
    if ball_center is None or distance is None:
        return False

    # Zwiększony próg: 15% krótszego wymiaru klatki (było 11%)
    threshold = max(80, min(frame.shape[:2]) * 0.15)
    is_close = distance <= threshold
    draw_forearm_contact(frame, body_points, ball_center, is_close)
    return is_close


class BallContactTracker:
    def __init__(self, cooldown_frames=14):
        self.cooldown_frames = cooldown_frames
        self.contact_count = 0
        self.last_contact_frame = -10_000
        self.was_near_forearms = False
        self.last_ball_center = None
        # Ile klatek utrzymujemy flagę is_contact=True po wykryciu odbicia
        self.contact_hold_remaining = 0

    def update(self, frame, body_points, ball_positions, frame_index):
        ball_center, distance = nearest_ball_to_forearms(frame, body_points, ball_positions)

        # Zmniejszamy licznik podtrzymania kontaktu
        if self.contact_hold_remaining > 0:
            self.contact_hold_remaining -= 1

        if ball_center is None or distance is None:
            self.was_near_forearms = False
            self.last_ball_center = None
            # Jeśli jesteśmy w oknie podtrzymania — nadal raportuj kontakt
            return self.contact_hold_remaining > 0

        # Zwiększony próg kontaktu: 15% krótszego wymiaru klatki
        threshold = max(80, min(frame.shape[:2]) * 0.15)
        is_near = distance <= threshold
        enough_cooldown = frame_index - self.last_contact_frame >= self.cooldown_frames
        is_new_contact = is_near and not self.was_near_forearms and enough_cooldown

        if is_new_contact:
            self.contact_count += 1
            self.last_contact_frame = frame_index
            # Ustaw okno podtrzymania kontaktu
            self.contact_hold_remaining = LIVE_CONTACT_HOLD_FRAMES

        self.was_near_forearms = is_near
        self.last_ball_center = ball_center
        draw_forearm_contact(frame, body_points, ball_center, is_near)
        # Zwróć True jeśli jesteśmy przy piłce LUB w oknie podtrzymania
        return is_near or self.contact_hold_remaining > 0


def is_ball_close_to_wrists(frame, body_points, ball_positions):
    for ball_center in ball_positions:
        for side in ["lewy_nadgarstek", "prawy_nadgarstek"]:
            wrist_x = int(body_points[side].x * frame.shape[1])
            wrist_y = int(body_points[side].y * frame.shape[0])
            distance = ((ball_center[0] - wrist_x) ** 2 + (ball_center[1] - wrist_y) ** 2) ** 0.5

            if distance < 100:
                cv2.line(frame, ball_center, (wrist_x, wrist_y), (0, 255, 255), 2)
                return True

    return False


def draw_pose_skeleton(frame, landmarks):
    """
    Rysuje pełny szkielet MediaPipe Pose z czerwonymi markerami na wszystkich 33 punktach.

    Działanie:
      1. Linie połączeń (POSE_CONNECTIONS) — jasno-szare, subtelne
      2. Każdy punkt landmarku — czerwone wypełnione koło z białą obwiódką

    Minimalna widoczność landmarku: 0.4 (niskopewne punkty pomijane)
    """
    h, w = frame.shape[:2]
    MIN_VIS = 0.4

    # Rysuj linie połączeń jako pierwsze (pod punktami)
    for connection in mp_pose.POSE_CONNECTIONS:
        start_idx, end_idx = connection
        lm_s = landmarks[start_idx]
        lm_e = landmarks[end_idx]
        if getattr(lm_s, "visibility", 1.0) < MIN_VIS or getattr(lm_e, "visibility", 1.0) < MIN_VIS:
            continue
        x_s, y_s = int(lm_s.x * w), int(lm_s.y * h)
        x_e, y_e = int(lm_e.x * w), int(lm_e.y * h)
        cv2.line(frame, (x_s, y_s), (x_e, y_e), (180, 180, 180), 2, cv2.LINE_AA)

    # Rysuj czerwone markery na każdym punkcie landmarku
    for lm in landmarks:
        if getattr(lm, "visibility", 1.0) < MIN_VIS:
            continue
        x, y = int(lm.x * w), int(lm.y * h)
        # Biała obwódka
        cv2.circle(frame, (x, y), 6, (255, 255, 255), -1, cv2.LINE_AA)
        # Czerwone wypełnienie
        cv2.circle(frame, (x, y), 4, (0, 0, 220), -1, cv2.LINE_AA)


def resize_to_width(frame, target_width):
    if target_width <= 0 or frame.shape[1] <= target_width:
        return frame

    scale = target_width / frame.shape[1]
    target_height = int(frame.shape[0] * scale)
    return cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)


def analyze_frame(
    frame,
    pose,
    detect_ball=True,
    source="file",
    contact_tracker=None,
    frame_index=0,
    pose_stabilizer: PoseLandmarkStabilizer | None = None,
    posture_evaluator: VolleyballPostureEvaluator | None = None,
    posture_debouncer: MessageDebouncer | None = None,
    contact_debouncer: MessageDebouncer | None = None,
):
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)

    body_points = {}
    contact_detected = False
    knee_angle = 120
    score = 0
    posture_warning = "Nie wykryto sylwetki"
    contact_warning = None
    contact_score = None
    pose_landmarks_for_use = results.pose_landmarks
    has_pose_now = bool(results.pose_landmarks)

    if pose_stabilizer is not None:
        stabilized_landmarks, has_pose_now = pose_stabilizer.update(results.pose_landmarks)
        pose_landmarks_for_use = stabilized_landmarks

    if pose_landmarks_for_use:
        # Rysuj szkielet: czerwone markery + szare linie (zamiast domyślnych mp_drawing)
        draw_pose_skeleton(frame, pose_landmarks_for_use.landmark)
        body_points = build_body_points(pose_landmarks_for_use.landmark)
        draw_forearm_contact(frame, body_points, None, False)
        knee_angle = calculate_knee_angle_value(body_points)

    ball_positions = find_ball_positions(frame) if detect_ball else []

    if body_points and ball_positions:
        if contact_tracker:
            contact_detected = contact_tracker.update(frame, body_points, ball_positions, frame_index)
        else:
            contact_detected = is_ball_close_to_forearms(frame, body_points, ball_positions)

    if body_points:
        if posture_evaluator is not None:
            is_correct, message, points = posture_evaluator.evaluate(body_points)
        else:
            is_correct, message, points = check_volleyball_position(body_points)
        score = points
        posture_warning = None if is_correct else message
        if posture_debouncer is not None:
            stabilized_message = posture_debouncer.update(posture_warning)
            posture_warning = stabilized_message

        if contact_detected:
            contact_warning = message
            contact_score = points
            if contact_debouncer is not None:
                stabilized_contact = contact_debouncer.update(contact_warning)
                contact_warning = stabilized_contact

    metrics = {
        "score": score,
        "kneeAngle": knee_angle,
        "totalContacts": contact_tracker.contact_count if contact_tracker else (1 if contact_detected else 0),
        "warnings": posture_warning,
        "postureWarnings": posture_warning,
        "contactWarning": contact_warning,
        "contactScore": contact_score,
        "isContact": contact_detected,
        "hasPose": bool(pose_landmarks_for_use),
        "hasBall": bool(ball_positions),
        "source": source,
        "isAnalyzing": True,
        # Wewnętrzne — używane przez biomechanikę, NIE są wysyłane do GUI
        "_ballCenters": ball_positions,
        "_bodyPoints": body_points,
    }

    return frame, metrics


def preprocess_uploaded_video(video_path, job_id):
    output_dir = os.path.join(CACHE_DIR, str(job_id))
    shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir, exist_ok=True)

    frame_paths = []
    frame_metrics = []

    with state_lock:
        preprocessed_state.update(
            {
                "jobId": job_id,
                "status": "processing",
                "progress": 0,
                "framePaths": [],
                "metrics": [],
                "fps": 25,
                "error": None,
            }
        )

    update_metrics(
        videoProcessingStatus="processing",
        videoProcessingProgress=0,
        totalContacts=0,
        status="Przygotowuję analizę wideo w tle...",
        isAnalyzing=False,
        source="file",
    )

    start_time = datetime.utcnow()

    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        with state_lock:
            preprocessed_state.update({"status": "error", "error": "Nie można otworzyć pliku wideo"})
        update_metrics(
            videoProcessingStatus="error",
            status="Nie można otworzyć pliku wideo",
            postureWarnings="Nie można otworzyć pliku wideo",
        )
        return

    fps = capture.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    frame_index = 0
    contact_tracker = BallContactTracker(cooldown_frames=max(10, int(fps * 0.45)))
    pose_stabilizer = PoseLandmarkStabilizer(alpha=0.25, hold_frames=0)
    posture_evaluator = VolleyballPostureEvaluator()
    posture_debouncer = MessageDebouncer(stable_frames=3)
    contact_debouncer = MessageDebouncer(stable_frames=2)

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while True:
            current_source = snapshot_source()
            if current_source.get("jobId") != job_id:
                capture.release()
                update_metrics(
                    isAnalyzing=False,
                    status="Przerwano przygotowanie wideo",
                    videoProcessingStatus="idle",
                    videoProcessingProgress=0,
                )
                return

            success, frame = capture.read()
            if not success:
                break

            analyzed_frame, metrics = analyze_frame(
                frame,
                pose,
                contact_tracker=contact_tracker,
                frame_index=frame_index,
                pose_stabilizer=pose_stabilizer,
                posture_evaluator=posture_evaluator,
                posture_debouncer=posture_debouncer,
                contact_debouncer=contact_debouncer,
            )
            frame_path = os.path.join(output_dir, f"{frame_index:06d}.jpg")
            cv2.imwrite(frame_path, analyzed_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
            frame_paths.append(frame_path)
            frame_metrics.append(metrics)
            frame_index += 1

            if total_frames:
                progress = min(99, int((frame_index / total_frames) * 100))
                with state_lock:
                    preprocessed_state["progress"] = progress
                update_metrics(
                    videoProcessingProgress=progress,
                    status=f"Przygotowuję analizę wideo: {progress}%",
                )

    capture.release()

    if not frame_paths:
        with state_lock:
            preprocessed_state.update({"status": "error", "error": "Nie znaleziono klatek w pliku"})
        update_metrics(
            videoProcessingStatus="error",
            videoProcessingProgress=0,
            status="Nie znaleziono klatek w pliku wideo",
        )
        return

    with state_lock:
        preprocessed_state.update(
            {
                "jobId": job_id,
                "status": "ready",
                "progress": 100,
                "framePaths": frame_paths,
                "metrics": frame_metrics,
                "fps": fps,
                "error": None,
            }
        )

    update_metrics(
        videoProcessingStatus="ready",
        videoProcessingProgress=100,
        totalContacts=contact_tracker.contact_count,
        status="Wideo gotowe do płynnego odtworzenia",
        isAnalyzing=False,
    )

    end_time = datetime.utcnow()
    # Obliczanie statystyk
    total_contacts = contact_tracker.contact_count
    angles = [m.get("kneeAngle", 0) for m in frame_metrics if m.get("hasPose")]
    avg_knee_angle = sum(angles) // len(angles) if angles else 0
    warnings_count = sum(1 for m in frame_metrics if m.get("postureWarnings"))
    contact_scores = [m.get("contactScore", 0) for m in frame_metrics if m.get("contactScore") is not None]
    avg_contact_score = sum(contact_scores) // len(contact_scores) if contact_scores else 0
    
    # Obliczamy score dla całego treningu (bazując na średniej)
    all_scores = [m.get("score", 0) for m in frame_metrics if m.get("hasPose")]
    overall_score = sum(all_scores) // len(all_scores) if all_scores else 0
    
    stats = {
        'total_contacts': total_contacts,
        'avg_knee_angle': avg_knee_angle,
        'posture_warnings_count': warnings_count,
        'avg_contact_score': avg_contact_score,
        'overall_score': overall_score
    }
    
    current_source = snapshot_source()
    if current_source.get("userId"):
        save_training_session(
            current_source["userId"],
            "file",
            start_time,
            end_time,
            stats,
            current_source.get("accessToken"),
        )


def stream_preprocessed_frames():
    cached = snapshot_preprocessed()

    if cached["status"] != "ready" or not cached["framePaths"]:
        update_metrics(
            isAnalyzing=False,
            source="file",
            status="Czekam na zakończenie przygotowania wideo",
        )
        return

    delay = 1 / max(1, min(float(cached["fps"] or 25), 30))

    while True:
        current_source = snapshot_source()
        latest_cache = snapshot_preprocessed()
        if current_source["mode"] != "file" or latest_cache["jobId"] != cached["jobId"]:
            break

        for frame_path, metrics in zip(cached["framePaths"], cached["metrics"]):
            current_source = snapshot_source()
            latest_cache = snapshot_preprocessed()
            if current_source["mode"] != "file" or latest_cache["jobId"] != cached["jobId"]:
                return

            with open(frame_path, "rb") as frame_file:
                frame_bytes = frame_file.read()

            update_metrics(
                **metrics,
                status="Odtwarzam przygotowaną analizę wideo",
                videoProcessingStatus="ready",
                videoProcessingProgress=100,
            )

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
            time.sleep(delay)


def stream_camera_frames(capture_source, current_source):
    """
    Pętla wideo dla trybu jednej kamery (frontowej lub bocznej).

    Tryb kamery odczytywany z source_state["cameraMode"]:
      "front" → analizuj_front() + detekcja piłki (bbox "PIŁKA" na klatce)
      "side"  → analizuj_bok() + WristTrajectoryTracker (zamach)
    """
    try:
        live_pose_tracker = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    except Exception as error:
        update_metrics(
            isAnalyzing=False,
            status=f"Nie mozna uruchomic detekcji pozy: {error}",
            warnings="Blad inicjalizacji detekcji pozy",
            postureWarnings="Blad inicjalizacji detekcji pozy",
            source="camera",
        )
        return

    if isinstance(capture_source, int) and sys.platform == "darwin":
        camera = cv2.VideoCapture(capture_source, cv2.CAP_AVFOUNDATION)
    else:
        camera = cv2.VideoCapture(capture_source)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, LIVE_STREAM_WIDTH)
    camera.set(cv2.CAP_PROP_FPS, LIVE_STREAM_FPS)

    if not camera.isOpened():
        live_pose_tracker.close()
        update_metrics(
            isAnalyzing=False,
            status="Nie mozna otworzyc kamery",
            warnings="Nie mozna otworzyc kamery",
            postureWarnings="Nie mozna otworzyc kamery",
            source="camera",
        )
        return

    frame_counter = 0
    target_delay = 1 / max(1, LIVE_STREAM_FPS)
    next_due = time.time()
    last_metrics = None
    no_pose_streak = 0
    contact_tracker = BallContactTracker(cooldown_frames=max(10, int(LIVE_STREAM_FPS * 0.45)))
    pose_stabilizer = PoseLandmarkStabilizer(alpha=LIVE_POSE_SMOOTH_ALPHA, hold_frames=LIVE_POSE_HOLD_FRAMES)
    posture_evaluator = VolleyballPostureEvaluator()
    posture_debouncer = MessageDebouncer(stable_frames=LIVE_MESSAGE_STABLE_FRAMES)
    contact_debouncer = MessageDebouncer(stable_frames=max(3, LIVE_MESSAGE_STABLE_FRAMES // 2))
    last_hint_sent_at = 0.0
    last_posture_hint = None
    failed_reads = 0

    # ── Biomechanika: tryb kamery i tracker zamachu ──────────────────────────
    camera_mode = current_source.get("cameraMode", "front")
    wrist_tracker = WristTrajectoryTracker()  # do śledzenia zamachu (kamera boczna)

    update_metrics(
        isAnalyzing=True,
        source="camera",
        cameraMode=camera_mode,
        status=f"Analiza kamery {'frontowej' if camera_mode == 'front' else 'bocznej'} w toku",
        totalContacts=0,
        videoProcessingStatus="idle",
        videoProcessingProgress=0,
        brakPracyNog=False,
        typOdbicia=None,
        fuzjaOcena=0,
    )

    start_time = datetime.utcnow()

    stats = {
        "contacts": 0,
        "warnings": 0,
        "sum_knee": 0,
        "count_pose": 0,
        "sum_contact_score": 0,
        "sum_score": 0,
        "count_contact": 0
    }

    while True:
        latest_source = snapshot_source()
        if latest_source["mode"] != "camera" or latest_source["cameraIndex"] != current_source["cameraIndex"]:
            break

        success, frame = camera.read()
        if not success:
            failed_reads += 1
            if failed_reads >= 20:
                break
            time.sleep(0.03)
            continue
        failed_reads = 0

        display_frame = resize_to_width(frame, LIVE_STREAM_WIDTH)
        detect_ball = frame_counter % max(1, LIVE_BALL_EVERY_N_FRAMES) == 0
        try:
            analyzed_frame, metrics = analyze_frame(
                display_frame,
                live_pose_tracker,
                detect_ball=detect_ball,
                source="camera",
                contact_tracker=contact_tracker,
                frame_index=frame_counter,
                pose_stabilizer=pose_stabilizer,
                posture_evaluator=posture_evaluator,
                posture_debouncer=posture_debouncer,
                contact_debouncer=contact_debouncer,
            )
        except Exception as error:
            update_metrics(
                isAnalyzing=False,
                source="camera",
                status=f"Blad analizy obrazu: {error}",
                warnings="Blad analizy obrazu",
                postureWarnings="Blad analizy obrazu",
            )
            break

        metrics, no_pose_streak = stabilize_live_metrics(metrics, last_metrics, no_pose_streak)
        last_metrics = metrics

        # ── INTEGRACJA BIOMECHANIKI: kamera frontowa ─────────────────────────
        # Wywołaj analizuj_front() i przekaż wyniki do GUI przez update_metrics()
        bio_front = {}
        bio_bok = {}

        dane_stopy = {}
        if camera_mode == "front" and metrics.get("hasPose"):
            _bp = metrics.get("_bodyPoints", {})
            _ball_positions = metrics.get("_ballCenters", [])  # Z analyze_frame — BEZ drugiego YOLO
            if _bp:
                bio_front = analizuj_front(_bp, _ball_positions, analyzed_frame.shape)
                # Analiza stóp (kamera frontowa)
                dane_stopy = analizuj_stopy(_bp)
                bio_front['dane_stopy'] = dane_stopy

        # ── INTEGRACJA BIOMECHANIKI: kamera boczna ───────────────────────────
        elif camera_mode == "side" and metrics.get("hasPose"):
            _bp = metrics.get("_bodyPoints", {})
            if _bp:
                bio_bok = analizuj_bok(_bp, wrist_tracker)
                metrics["komunikatKolana"] = bio_bok.get("komunikat_kolana")
                metrics["postureWarnings"] = bio_bok.get("komunikat_kolana")

        # ── Analiza fazy ruchu ────────────────────────────────────────────────
        dystans = bio_front.get('dystans_pilka_px') if bio_front else None
        dane_fazy = analizuj_faze(bio_front or {}, bio_bok or {}, dystans)

        now = time.time()
        posture_warning = metrics.get("postureWarnings")
        if posture_warning != last_posture_hint and (now - last_hint_sent_at) >= LIVE_HINT_MIN_INTERVAL_SEC:
            last_posture_hint = posture_warning
            last_hint_sent_at = now

        published_metrics = {
            **metrics,
            "postureWarnings": last_posture_hint,
            "warnings": last_posture_hint,
        }

        # Dodaj pola biomechaniczne do metryki publikowanej do GUI
        if bio_front:
            published_metrics["typOdbicia"] = bio_front.get("typ_odbicia")
            published_metrics["dystansPilkaRece"] = bio_front.get("dystans_pilka_px")
            # Jeśli wykryto odbicie → zaktualizuj score i kontakt
            if bio_front.get("typ_odbicia"):
                published_metrics["isContact"] = True
        if bio_bok:
            published_metrics["komunikatKolana"] = bio_bok.get("komunikat_kolana")
            published_metrics["katBiodra"] = bio_bok.get("kat_biodra")
            published_metrics["zamachWykryty"] = bio_bok.get("zamach_wykryty", False)
            published_metrics["dynamikaZamachu"] = bio_bok.get("dynamika_zamachu")

        if dane_stopy:
            published_metrics['rozstawienieStop'] = dane_stopy.get('rozstawienie_stop')
            published_metrics['balansStop'] = dane_stopy.get('balans')
        if dane_fazy:
            published_metrics['fazaRuchu'] = dane_fazy.get('faza')
            published_metrics['gotowoscPrzedOdbiciem'] = dane_fazy.get('gotowosc')
            published_metrics['feedbackFazy'] = dane_fazy.get('feedback_fazy')

        published_metrics.pop("_bodyPoints", None)
        published_metrics.pop("_ballCenters", None)

        update_metrics(
            **published_metrics,
            status=build_live_status(published_metrics),
            videoProcessingStatus="idle",
            videoProcessingProgress=0,
        )

        if metrics.get("hasPose"):
            stats["sum_knee"] += metrics.get("kneeAngle", 0)
            stats["count_pose"] += 1
            stats["sum_score"] += metrics.get("score", 0)
        if published_metrics.get("postureWarnings"):
            stats["warnings"] += 1
        if metrics.get("isContact") and metrics.get("contactScore") is not None:
            stats["sum_contact_score"] += metrics.get("contactScore", 0)
            stats["count_contact"] += 1

        # ── Minimalny wskaźnik statusu (mały dot w rogu) — reszta trafia do GUI HUD ──
        # Zielony = sylwetka wykryta i pozycja OK
        # Żółty = sylwetka wykryta, ostrzegaź
        # Czerwony = brak sylwetki
        dot_color = (
            (0, 200, 0) if metrics.get("hasPose") and not last_posture_hint
            else (0, 200, 230) if metrics.get("hasPose")
            else (0, 0, 200)
        )
        cv2.circle(analyzed_frame, (analyzed_frame.shape[1] - 18, 18), 8, (0, 0, 0), -1)
        cv2.circle(analyzed_frame, (analyzed_frame.shape[1] - 18, 18), 6, dot_color, -1)

        # Jeśli wykryto odbicie — subtelny błysk na dole klatki (1 sekunda)
        if bio_front.get("typ_odbicia"):
            h_f = analyzed_frame.shape[0]
            w_f = analyzed_frame.shape[1]
            overlay = analyzed_frame.copy()
            cv2.rectangle(overlay, (0, h_f - 6), (w_f, h_f), (0, 220, 80), -1)
            cv2.addWeighted(overlay, 0.7, analyzed_frame, 0.3, 0, analyzed_frame)

        ret, buffer = cv2.imencode(".jpg", analyzed_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
        if not ret:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )

        frame_counter += 1
        next_due += target_delay
        sleep_for = next_due - time.time()
        if sleep_for > 0:
            time.sleep(sleep_for)
        else:
            next_due = time.time()

    camera.release()
    live_pose_tracker.close()
    update_metrics(isAnalyzing=False, status="Analiza zatrzymana")

    end_time = datetime.utcnow()

    if stats["count_pose"] > 0:
        final_stats = {
            'total_contacts': contact_tracker.contact_count,
            'avg_knee_angle': stats["sum_knee"] // stats["count_pose"],
            'posture_warnings_count': stats["warnings"],
            'avg_contact_score': stats["sum_contact_score"] // stats["count_contact"] if stats["count_contact"] else 0,
            'overall_score': stats["sum_score"] // stats["count_pose"]
        }

        current_src = snapshot_source()
        if current_src.get("userId"):
            save_training_session(
                current_src["userId"],
                "camera",
                start_time,
                end_time,
                final_stats,
                current_src.get("accessToken"),
            )


def generate_frames():
    capture_source, current_source = get_capture_source()
    if current_source["mode"] == "stopped":
        update_metrics(isAnalyzing=False, status="Analiza przerwana")
        return

    if current_source["mode"] == "file":
        yield from stream_preprocessed_frames()
        return

    if current_source["mode"] == "camera_dual":
        yield from stream_dual_camera_frames(current_source)
        return

    yield from stream_camera_frames(capture_source, current_source)
    return


# ─────────────────────────────────────────────────────────────────────────────
# Pomocnicze funkcje do integracji biomechanics.py
# ─────────────────────────────────────────────────────────────────────────────

def _extract_ball_centers(frame):
    """
    Uruchamia YOLO na klatce i zwraca listę (cx, cy) środków bbox piłek.
    Nie rysuje bbox — tylko wyciąga środki (rysowanie robi analyze_frame/find_ball_positions).
    Lekka wersja dla biomechaniki, nie duplikuje kosztownej inferencji.
    """
    # UWAGA: find_ball_positions() już narysowało bbox i zwróciło środki piłek
    # Tutaj używamy bezpośrednio kontaktu z YOLO tylko gdy potrzeba świeżych danych.
    # W praktyce, korzystamy z już policzonej listy przez analyze_frame,
    # dlatego ta funkcja jest minimalna — sprawdza jedynie ostatni wynik YOLO.
    results_yolo = yolo_model(frame, conf=0.4, verbose=False)
    centers = []
    for result in results_yolo:
        for box in result.boxes:
            cls = int(box.cls[0])
            if result.names[cls] != "sports ball":
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            area = (x2 - x1) * (y2 - y1)
            if area <= 200:
                continue
            centers.append(((x1 + x2) // 2, (y1 + y2) // 2))
    return centers


def _draw_ball_labels(frame, ball_centers):
    """
    Rysuje polskie etykiety "PIŁKA" nad każdym centrum piłki.
    Wywoływana po analyze_frame() — find_ball_positions już narysowała bbox.
    """
    for cx, cy in ball_centers:
        cv2.putText(
            frame, "PILKA",
            (cx - 25, max(cy - 15, 15)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2, cv2.LINE_AA,
        )


def stream_dual_camera_frames(current_source):
    """
    Pętla Dual-Cam z synchronizacją Queue i fuzją biomechaniczną.

    Architektura:
      Wątek A (kamera frontowa) → kolejka_front (maxsize=1) → środki piłek + szkielet
      Wątek B (kamera boczna)  → kolejka_bok  (maxsize=1) → kąty stawów + zamach
      Wątek główny (generator) → pobiera z obu kolejek → fuzja_sensorow() → GUI

    Queue(maxsize=1) + put_nowait() = szybsza kamera nie blokuje GUI —
    po prostu nadpisuje klatkę, wolniejsza blokuje z timeout=0.08s.
    """
    import queue as _queue

    cam_a = int(current_source.get("cameraIndex") or 0)
    cam_b = current_source.get("cameraIndex2")
    if cam_b is None:
        update_metrics(isAnalyzing=False, status="Brak drugiej kamery", warnings="Brak drugiej kamery", source="camera")
        return

    # ── Inicjalizacja kamer ──────────────────────────────────────────────────
    if sys.platform == "darwin":
        camera1 = cv2.VideoCapture(cam_a, cv2.CAP_AVFOUNDATION)
        camera2 = cv2.VideoCapture(int(cam_b), cv2.CAP_AVFOUNDATION)
    else:
        camera1 = cv2.VideoCapture(cam_a)
        camera2 = cv2.VideoCapture(int(cam_b))

    for cam in (camera1, camera2):
        cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, LIVE_STREAM_WIDTH)
        cam.set(cv2.CAP_PROP_FPS, LIVE_STREAM_FPS)

    if not camera1.isOpened() or not camera2.isOpened():
        update_metrics(
            isAnalyzing=False,
            status="Nie mozna otworzyc dwoch kamer",
            warnings="Nie mozna otworzyc dwoch kamer",
            postureWarnings="Nie mozna otworzyc dwoch kamer",
            source="camera",
        )
        camera1.release()
        camera2.release()
        return

    # ── Kolejki synchronizacji (maxsize=1 = nie blokuje GUI) ────────────────
    # Kamera A = frontowa, Kamera B = boczna
    kolejka_front: _queue.Queue = _queue.Queue(maxsize=1)
    kolejka_bok:   _queue.Queue = _queue.Queue(maxsize=1)
    stop_event = threading.Event()

    # ── Osobne trackery dla każdej kamery ───────────────────────────────────
    pose_tracker_front = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    pose_tracker_bok   = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    stabilizer_front = PoseLandmarkStabilizer(alpha=LIVE_POSE_SMOOTH_ALPHA, hold_frames=LIVE_POSE_HOLD_FRAMES)
    stabilizer_bok   = PoseLandmarkStabilizer(alpha=LIVE_POSE_SMOOTH_ALPHA, hold_frames=LIVE_POSE_HOLD_FRAMES)
    posture_eval_front = VolleyballPostureEvaluator()
    posture_eval_bok   = VolleyballPostureEvaluator()
    posture_deb_front  = MessageDebouncer(stable_frames=LIVE_MESSAGE_STABLE_FRAMES)
    posture_deb_bok    = MessageDebouncer(stable_frames=LIVE_MESSAGE_STABLE_FRAMES)
    contact_deb        = MessageDebouncer(stable_frames=max(3, LIVE_MESSAGE_STABLE_FRAMES // 2))
    contact_tracker    = BallContactTracker(cooldown_frames=max(10, int(LIVE_STREAM_FPS * 0.45)))
    wrist_tracker_bok  = WristTrajectoryTracker()

    frame_counter_front = [0]
    frame_counter_bok   = [0]

    # ── Wątek A: kamera frontowa ─────────────────────────────────────────────
    def grab_front():
        failed = 0
        while not stop_event.is_set():
            ok, raw = camera1.read()
            if not ok:
                failed += 1
                if failed >= 20:
                    break
                time.sleep(0.02)
                continue
            failed = 0
            frame = resize_to_width(raw, LIVE_STREAM_WIDTH)
            try:
                analyzed, m = analyze_frame(
                    frame, pose_tracker_front,
                    detect_ball=(frame_counter_front[0] % max(1, LIVE_BALL_EVERY_N_FRAMES) == 0),
                    source="camera",
                    contact_tracker=contact_tracker,
                    frame_index=frame_counter_front[0],
                    pose_stabilizer=stabilizer_front,
                    posture_evaluator=posture_eval_front,
                    posture_debouncer=posture_deb_front,
                    contact_debouncer=contact_deb,
                )
            except Exception:
                frame_counter_front[0] += 1
                continue
            frame_counter_front[0] += 1
            # Biomechanika frontowa — używamy body_points i ball_centers z analyze_frame
            # (NIE wołamy _extract_ball_centers ani YOLO po raz drugi!)
            bp_front = m.get("_bodyPoints", {})
            ball_centers = m.get("_ballCenters", [])
            dane_front = analizuj_front(bp_front, ball_centers, analyzed.shape)
            # Wynik do kolejki (nadpisuje jeśli pełna — drop old frame)
            try:
                kolejka_front.put_nowait((analyzed, m, dane_front))
            except _queue.Full:
                try:
                    kolejka_front.get_nowait()
                except _queue.Empty:
                    pass
                kolejka_front.put_nowait((analyzed, m, dane_front))


    # ── Wątek B: kamera boczna ───────────────────────────────────────────────
    def grab_bok():
        failed = 0
        while not stop_event.is_set():
            ok, raw = camera2.read()
            if not ok:
                failed += 1
                if failed >= 20:
                    break
                time.sleep(0.02)
                continue
            failed = 0
            frame = resize_to_width(raw, LIVE_STREAM_WIDTH)
            try:
                analyzed, m = analyze_frame(
                    frame, pose_tracker_bok,
                    detect_ball=False,  # kamera boczna nie śledzi piłki
                    source="camera",
                    contact_tracker=None,
                    frame_index=frame_counter_bok[0],
                    pose_stabilizer=stabilizer_bok,
                    posture_evaluator=posture_eval_bok,
                    posture_debouncer=posture_deb_bok,
                    contact_debouncer=None,
                )
            except Exception:
                frame_counter_bok[0] += 1
                continue
            frame_counter_bok[0] += 1
            bp_bok = None
            lms_bok = stabilizer_bok.last_landmarks()
            if lms_bok is not None:
                bp_bok = build_body_points(lms_bok.landmark)
            dane_bok = analizuj_bok(bp_bok or {}, wrist_tracker_bok)
            # Overlay kąta kolanowego na klatce bocznej
            if dane_bok.get("kat_kolana") is not None:
                kol_txt = f"Kolano: {dane_bok['kat_kolana']:.0f}deg"
                kol_kolor = (0, 220, 0) if "prawidlowa" in dane_bok.get("komunikat_kolana", "").lower() or "prawidłowa" in dane_bok.get("komunikat_kolana", "") else (0, 80, 255)
                cv2.putText(analyzed, kol_txt,
                    (10, analyzed.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, kol_kolor, 2, cv2.LINE_AA)
            try:
                kolejka_bok.put_nowait((analyzed, m, dane_bok))
            except _queue.Full:
                try:
                    kolejka_bok.get_nowait()
                except _queue.Empty:
                    pass
                kolejka_bok.put_nowait((analyzed, m, dane_bok))

    # ── Uruchom wątki grabberów ───────────────────────────────────────────────
    t_front = threading.Thread(target=grab_front, daemon=True)
    t_bok   = threading.Thread(target=grab_bok,   daemon=True)
    t_front.start()
    t_bok.start()

    update_metrics(
        isAnalyzing=True,
        source="camera",
        cameraMode="dual",
        status="Analiza z dwóch kamer — synchronizacja...",
        totalContacts=0,
        videoProcessingStatus="idle",
        videoProcessingProgress=0,
        brakPracyNog=False,
        typOdbicia=None,
        fuzjaOcena=0,
    )

    frame_counter = 0
    target_delay = 1 / max(1, LIVE_STREAM_FPS)
    next_due = time.time()
    last_metrics = None
    no_pose_streak = 0

    # ── Pętla główna generatora (synchronizacja klatek z obu wątków) ─────────
    while True:
        latest_source = snapshot_source()
        if latest_source["mode"] != "camera_dual":
            break

        try:
            # Blokujące pobieranie z timeoutem — "software lock-step"
            # Jeśli jedna kamera jest wolniejsza, czekamy max 80 ms
            frame_front, m_front, dane_front = kolejka_front.get(timeout=0.08)
            frame_bok,   m_bok,   dane_bok   = kolejka_bok.get(timeout=0.08)
        except Exception:
            # Jedna z kamer spóźniona — użyj ostatnich metryk i kontynuuj
            time.sleep(0.02)
            continue

        # ── FUZJA SENSORÓW ────────────────────────────────────────────────────
        # PUNKT INTEGRACJI: wywołaj fuzja_sensorow() dla obu kamer
        wynik_fuzji = fuzja_sensorow(dane_front, dane_bok)

        # ── Analiza stóp (z kamery frontowej) ────────────────────────────────
        bp_front_latest = m_front.get('_bodyPoints', {})
        dane_stopy = analizuj_stopy(bp_front_latest)

        # ── Analiza fazy ruchu ────────────────────────────────────────────────
        dystans = dane_front.get('dystans_pilka_px')
        dane_fazy = analizuj_faze(dane_front, dane_bok, dystans)

        # Wybierz bazowe metryki (z kamery frontowej — tam jest piłka)
        if m_front.get("hasPose") or not m_bok.get("hasPose"):
            metrics = m_front
        else:
            metrics = m_bok

        metrics, no_pose_streak = stabilize_live_metrics(metrics, last_metrics, no_pose_streak)
        last_metrics = metrics

        # ── Publikuj wyniki fuzji do GUI przez WebSocket ───────────────────────
        # Pola trafiają do: ProgressBar (fuzjaOcena=score), pól tekstowych,
        # etykiet, alertów — w zależności od implementacji frontendu.
        komunikat_kontaktu = None
        if wynik_fuzji.get("brak_pracy_nog"):
            # BŁĄD KRYTYCZNY: odbicie bez pracy nóg
            komunikat_kontaktu = "Odbicie wykonane samymi rękami! Brak pracy nóg!"

        metrics.pop("_bodyPoints", None)
        metrics.pop("_ballCenters", None)

        update_metrics(
            **metrics,
            # Biomechaniczne pola fuzji
            score=wynik_fuzji["ocena_fuzji"],           # → ProgressBar
            fuzjaOcena=wynik_fuzji["ocena_fuzji"],      # → ProgressBar (alias)
            postureWarnings=wynik_fuzji["komunikat_fuzji"],  # → pole tekstowe
            warnings=wynik_fuzji["komunikat_fuzji"],
            contactWarning=komunikat_kontaktu,           # → alert GUI
            brakPracyNog=wynik_fuzji["brak_pracy_nog"],  # → czerwony alert
            typOdbicia=wynik_fuzji["typ_odbicia"],       # → etykieta GUI
            komunikatKolana=dane_bok.get("komunikat_kolana"),
            katBiodra=dane_bok.get("kat_biodra"),
            zamachWykryty=dane_bok.get("zamach_wykryty", False),
            dynamikaZamachu=dane_bok.get("dynamika_zamachu"),
            dystansPilkaRece=dane_front.get("dystans_pilka_px"),
            isContact=bool(wynik_fuzji.get("typ_odbicia")),
            cameraMode="dual",
            status=wynik_fuzji["komunikat_fuzji"] or build_live_status(metrics),
            videoProcessingStatus="idle",
            videoProcessingProgress=0,
            rozstawienieStop=dane_stopy.get('rozstawienie_stop') if dane_stopy else None,
            balansStop=dane_stopy.get('balans') if dane_stopy else None,
            fazaRuchu=dane_fazy.get('faza', 'OCZEKIWANIE') if dane_fazy else 'OCZEKIWANIE',
            gotowoscPrzedOdbiciem=dane_fazy.get('gotowosc') if dane_fazy else None,
            feedbackFazy=dane_fazy.get('feedback_fazy') if dane_fazy else None,
        )

        # ── Minimalny overlay — reszta trafia do GUI HUD przez WebSocket ─────
        # Kamera frontowa: mały dot statusu w górnym rogu
        dot_f = (
            (0, 200, 0)   if m_front.get("hasPose") and not wynik_fuzji.get("brak_pracy_nog")
            else (0, 200, 230) if m_front.get("hasPose")
            else (0, 0, 200)
        )
        cv2.circle(frame_front, (frame_front.shape[1] - 18, 18), 8, (0, 0, 0), -1)
        cv2.circle(frame_front, (frame_front.shape[1] - 18, 18), 6, dot_f, -1)

        # Kamera boczna: mały dot statusu
        dot_b = (0, 200, 0) if m_bok.get("hasPose") else (0, 0, 200)
        cv2.circle(frame_bok, (frame_bok.shape[1] - 18, 18), 8, (0, 0, 0), -1)
        cv2.circle(frame_bok, (frame_bok.shape[1] - 18, 18), 6, dot_b, -1)

        # Subtelny błysk kontaktu: zielony pasek na dole klatki frontowej
        if wynik_fuzji.get("typ_odbicia"):
            h_f, w_f = frame_front.shape[:2]
            ov = frame_front.copy()
            cv2.rectangle(ov, (0, h_f - 6), (w_f, h_f), (0, 220, 80), -1)
            cv2.addWeighted(ov, 0.75, frame_front, 0.25, 0, frame_front)

        # Czerwona obwódka gdy błąd "brak pracy nóg"
        if wynik_fuzji.get("brak_pracy_nog"):
            cv2.rectangle(frame_front, (0, 0), (frame_front.shape[1] - 1, frame_front.shape[0] - 1),
                          (0, 0, 220), 4)

        # ── Etykiety kamer (małe, w rogu) ────────────────────────────────────
        # "FRONT" i "BOK" — tylko żeby użytkownik wiedział co to
        cv2.putText(frame_front, "FRONT", (8, 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.putText(frame_bok, "BOK", (8, 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, (200, 200, 200), 1, cv2.LINE_AA)

        # ── Scal klatki obok siebie ───────────────────────────────────────────
        h = min(frame_front.shape[0], frame_bok.shape[0])
        if frame_front.shape[0] != h:
            frame_front = cv2.resize(frame_front, (frame_front.shape[1], h), interpolation=cv2.INTER_AREA)
        if frame_bok.shape[0] != h:
            frame_bok = cv2.resize(frame_bok, (frame_bok.shape[1], h), interpolation=cv2.INTER_AREA)

        combined = cv2.hconcat([frame_front, frame_bok])

        ret, buffer = cv2.imencode(".jpg", combined, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
        if not ret:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )

        frame_counter += 1
        next_due += target_delay
        sleep_for = next_due - time.time()
        if sleep_for > 0:
            time.sleep(sleep_for)
        else:
            next_due = time.time()

    # ── Sprzątanie ────────────────────────────────────────────────────────────
    stop_event.set()
    t_front.join(timeout=1.0)
    t_bok.join(timeout=1.0)
    pose_tracker_front.close()
    pose_tracker_bok.close()
    camera1.release()
    camera2.release()
    update_metrics(isAnalyzing=False, status="Analiza zatrzymana", cameraMode="front")


@app.get("/api/source")
def get_source():
    return {**snapshot_source(), "preprocessing": snapshot_preprocessed()}


@app.post("/api/analysis/stop")
def stop_analysis():
    stop_current_analysis()
    return {"ok": True}


@app.post("/api/source/camera")
def set_camera_source(
    camera_index: int = 0,
    user_id: str = None,
    authorization: str | None = Header(default=None),
    camera_mode: str = "front",  # "front" lub "side"
):
    """
    Ustawia źródło na kamerę.
    camera_mode: "front" (kamera frontowa, analiza piłki + symetria)
                 "side"  (kamera boczna, analiza kolan + zamach)
    """
    access_token = authorization.removeprefix("Bearer ").strip() if authorization else None
    safe_mode = camera_mode if camera_mode in ("front", "side") else "front"
    with state_lock:
        source_state.update(
            {
                "mode": "camera",
                "cameraIndex": camera_index,
                "cameraIndex2": None,
                "videoPath": None,
                "videoName": None,
                "jobId": source_state["jobId"] + 1,
                "userId": user_id,
                "accessToken": access_token,
                "cameraMode": safe_mode,
            }
        )
        preprocessed_state.update(
            {
                "status": "idle",
                "progress": 0,
                "framePaths": [],
                "metrics": [],
                "error": None,
            }
        )

    mode_label = "frontową" if safe_mode == "front" else "boczną"
    update_metrics(
        source="camera",
        cameraMode=safe_mode,
        status=f"Wybrano kamerę {mode_label}",
        totalContacts=0,
        contactWarning=None,
        contactScore=None,
        isContact=False,
        typOdbicia=None,
        fuzjaOcena=0,
        brakPracyNog=False,
        videoProcessingStatus="idle",
        videoProcessingProgress=0,
    )
    return {"ok": True, "source": "camera", "cameraIndex": camera_index, "cameraMode": safe_mode}


@app.post("/api/source/camera-dual")
def set_dual_camera_source(
    camera_index_a: int = 0,
    camera_index_b: int = 1,
    user_id: str = None,
    authorization: str | None = Header(default=None),
):
    """
    Ustawia źródło na dwie kamery z fuzją biomechaniczną.
    camera_index_a = kamera frontowa (widzi piłkę i ręce)
    camera_index_b = kamera boczna (widzi kolana i zamach, pod kątem ~45°)
    """
    access_token = authorization.removeprefix("Bearer ").strip() if authorization else None
    with state_lock:
        source_state.update(
            {
                "mode": "camera_dual",
                "cameraIndex": camera_index_a,
                "cameraIndex2": camera_index_b,
                "videoPath": None,
                "videoName": None,
                "jobId": source_state["jobId"] + 1,
                "userId": user_id,
                "accessToken": access_token,
                "cameraMode": "dual",
            }
        )
        preprocessed_state.update(
            {
                "status": "idle",
                "progress": 0,
                "framePaths": [],
                "metrics": [],
                "error": None,
            }
        )

    update_metrics(
        source="camera",
        cameraMode="dual",
        status=f"Dual-Cam: frontowa ({camera_index_a}) + boczna ({camera_index_b}) | Fuzja biomechaniczna aktywna",
        totalContacts=0,
        contactWarning=None,
        contactScore=None,
        isContact=False,
        typOdbicia=None,
        fuzjaOcena=0,
        brakPracyNog=False,
        videoProcessingStatus="idle",
        videoProcessingProgress=0,
    )
    return {
        "ok": True,
        "source": "camera_dual",
        "cameraIndex": camera_index_a,
        "cameraIndex2": camera_index_b,
        "cameraMode": "dual",
    }


@app.post("/api/source/upload")
async def upload_video(
    file: UploadFile = File(...),
    user_id: str = None,
    authorization: str | None = Header(default=None),
):
    access_token = authorization.removeprefix("Bearer ").strip() if authorization else None
    allowed_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    _, extension = os.path.splitext(file.filename or "")
    extension = extension.lower()

    if extension not in allowed_extensions:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Obsługiwane formaty: mp4, mov, avi, mkv, webm"},
        )

    with state_lock:
        job_id = source_state["jobId"] + 1

    target_path = os.path.join(UPLOAD_DIR, f"upload_{job_id}{extension}")
    with open(target_path, "wb") as target:
        shutil.copyfileobj(file.file, target)

    with state_lock:
        source_state.update(
            {
                "mode": "file",
                "cameraIndex": 0,
                "videoPath": target_path,
                "videoName": file.filename,
                "jobId": job_id,
                "userId": user_id,
                "accessToken": access_token,
            }
        )

    update_metrics(
        source="file",
        status=f"Wgrano plik: {file.filename}. Przygotowuję analizę...",
        totalContacts=0,
        contactWarning=None,
        contactScore=None,
        isContact=False,
        videoProcessingStatus="processing",
        videoProcessingProgress=0,
    )

    threading.Thread(target=preprocess_uploaded_video, args=(target_path, job_id), daemon=True).start()

    return {"ok": True, "source": "file", "videoName": file.filename, "jobId": job_id}


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/api/voice/status")
def voice_status():
    return {
        "ready": vosk_stt.model_is_ready(),
        "engine": "vosk",
        "model": vosk_stt.MODEL_DIR_NAME,
        "sampleRate": vosk_stt.SAMPLE_RATE,
    }


@app.post("/api/voice/prepare")
def voice_prepare():
    try:
        vosk_stt.download_model()
        return {"ok": True, "ready": True}
    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "ready": False, "error": str(error)},
        )


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()

    try:
        recognizer = vosk_stt.create_recognizer()
    except FileNotFoundError:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Brak modelu Vosk. Uruchom: POST /api/voice/prepare lub poczekaj na pobranie modelu.",
            }
        )
        await websocket.close()
        return
    except Exception as error:
        error_text = str(error).encode("ascii", errors="ignore").decode("ascii") or "nieznany blad"
        await websocket.send_json(
            {"type": "error", "message": f"Nie mozna uruchomic rozpoznawania mowy: {error_text}"}
        )
        await websocket.close()
        return

    await websocket.send_json({"type": "ready"})

    try:
        while True:
            message = await websocket.receive()
            chunk = message.get("bytes")
            if not chunk:
                continue

            if recognizer.AcceptWaveform(chunk):
                text = vosk_stt.parse_result(recognizer.Result(), "text")
                if text:
                    await websocket.send_json({"type": "final", "text": text})
            else:
                partial = vosk_stt.parse_result(recognizer.PartialResult(), "partial")
                if partial:
                    await websocket.send_json({"type": "partial", "text": partial})
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/metrics")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(snapshot_metrics())
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print("Client disconnected")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
