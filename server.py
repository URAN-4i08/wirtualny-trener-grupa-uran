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
import mediapipe as mp
from ultralytics import YOLO
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# Add the root directory to path to import logic modules.
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from logic.coach_engine import calculate_angle, check_volleyball_position
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
    "videoPath": None,
    "videoName": None,
    "jobId": 0,
    "userId": None,
    "accessToken": None,
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
}

yolo_model = YOLO(os.getenv("YOLO_MODEL_PATH", "yolov8n.pt"))
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
pose_tracker = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

LIVE_STREAM_FPS = int(os.getenv("LIVE_STREAM_FPS", "20"))
LIVE_STREAM_WIDTH = int(os.getenv("LIVE_STREAM_WIDTH", "960"))
LIVE_ANALYSIS_WIDTH = int(os.getenv("LIVE_ANALYSIS_WIDTH", "640"))
LIVE_POSE_EVERY_N_FRAMES = int(os.getenv("LIVE_POSE_EVERY_N_FRAMES", "3"))
LIVE_BALL_EVERY_N_FRAMES = int(os.getenv("LIVE_BALL_EVERY_N_FRAMES", "6"))
LIVE_NO_POSE_GRACE_FRAMES = int(os.getenv("LIVE_NO_POSE_GRACE_FRAMES", "4"))


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
                "accessToken": None,
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
    results_yolo = yolo_model(frame, conf=0.4, verbose=False)
    ball_positions = []

    for result in results_yolo:
        for box in result.boxes:
            cls = int(box.cls[0])
            if result.names[cls] != "sports ball":
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            area = (x2 - x1) * (y2 - y1)
            if area <= 200:
                continue

            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(frame, "Pilka", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            ball_positions.append(((x1 + x2) // 2, (y1 + y2) // 2))

    return ball_positions


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


def resize_to_width(frame, target_width):
    if target_width <= 0 or frame.shape[1] <= target_width:
        return frame

    scale = target_width / frame.shape[1]
    target_height = int(frame.shape[0] * scale)
    return cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)


def analyze_frame(frame, pose, detect_ball=True, source="file"):
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)

    body_points = {}
    contact_detected = False
    knee_angle = 120
    score = 0
    posture_warning = "Nie wykryto sylwetki"
    contact_warning = None
    contact_score = None

    if results.pose_landmarks:
        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        body_points = build_body_points(results.pose_landmarks.landmark)
        knee_angle = calculate_knee_angle_value(body_points)

    ball_positions = find_ball_positions(frame) if detect_ball else []

    if body_points and ball_positions:
        contact_detected = is_ball_close_to_wrists(frame, body_points, ball_positions)

    if body_points:
        is_correct, message, points = check_volleyball_position(body_points)
        score = points
        posture_warning = None if is_correct else message

        if contact_detected:
            contact_warning = message
            contact_score = points

    metrics = {
        "score": score,
        "kneeAngle": knee_angle,
        "warnings": posture_warning,
        "postureWarnings": posture_warning,
        "contactWarning": contact_warning,
        "contactScore": contact_score,
        "isContact": contact_detected,
        "hasPose": bool(body_points),
        "hasBall": bool(ball_positions),
        "source": source,
        "isAnalyzing": True,
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

            analyzed_frame, metrics = analyze_frame(frame, pose)
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
        status="Wideo gotowe do płynnego odtworzenia",
        isAnalyzing=False,
    )

    end_time = datetime.utcnow()
    # Obliczanie statystyk
    total_contacts = sum(1 for m in frame_metrics if m.get("isContact"))
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
    camera = cv2.VideoCapture(capture_source)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, LIVE_STREAM_WIDTH)

    if not camera.isOpened():
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
    last_metrics = None
    no_pose_streak = 0

    update_metrics(
        isAnalyzing=True,
        source="camera",
        status="Analiza kamery w toku",
        videoProcessingStatus="idle",
        videoProcessingProgress=0,
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
            break

        display_frame = resize_to_width(frame, LIVE_STREAM_WIDTH)
        should_analyze_pose = frame_counter % max(1, LIVE_POSE_EVERY_N_FRAMES) == 0
        should_detect_ball = frame_counter % max(1, LIVE_BALL_EVERY_N_FRAMES) == 0

        if should_analyze_pose:
            analysis_frame = resize_to_width(display_frame.copy(), LIVE_ANALYSIS_WIDTH)
            analyzed_frame, metrics = analyze_frame(
                analysis_frame,
                pose_tracker,
                detect_ball=should_detect_ball,
                source="camera",
            )
            display_frame = resize_to_width(analyzed_frame, LIVE_STREAM_WIDTH)

            metrics, no_pose_streak = stabilize_live_metrics(metrics, last_metrics, no_pose_streak)
            last_metrics = metrics

            update_metrics(
                **metrics,
                status=build_live_status(metrics),
                videoProcessingStatus="idle",
                videoProcessingProgress=0,
            )

            if metrics.get("hasPose"):
                stats["sum_knee"] += metrics.get("kneeAngle", 0)
                stats["count_pose"] += 1
                stats["sum_score"] += metrics.get("score", 0)
            if metrics.get("postureWarnings"):
                stats["warnings"] += 1
            if metrics.get("isContact"):
                stats["contacts"] += 1
                if metrics.get("contactScore") is not None:
                    stats["sum_contact_score"] += metrics.get("contactScore", 0)
                    stats["count_contact"] += 1

        ret, buffer = cv2.imencode(".jpg", display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
        if not ret:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )

        frame_counter += 1
        time.sleep(target_delay)

    camera.release()
    update_metrics(isAnalyzing=False, status="Analiza zatrzymana")

    end_time = datetime.utcnow()
    
    if stats["count_pose"] > 0:
        final_stats = {
            'total_contacts': stats["contacts"],
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

    yield from stream_camera_frames(capture_source, current_source)
    return

    camera = cv2.VideoCapture(capture_source)

    if not camera.isOpened():
        update_metrics(
            isAnalyzing=False,
            status="Nie można otworzyć źródła wideo",
            warnings="Nie można otworzyć kamery lub pliku wideo",
            postureWarnings="Nie można otworzyć kamery lub pliku wideo",
            source=current_source["mode"],
        )
        return

    contact_feedback_frames = 0

    while True:
        success, frame = camera.read()
        if not success:
            if current_source["mode"] == "file":
                camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            break

        update_metrics(isAnalyzing=True, status="Analiza w toku", source=current_source["mode"])

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose_tracker.process(image_rgb)

        body_points = {}
        contact_detected = False

        if results.pose_landmarks:
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            body_points = build_body_points(results.pose_landmarks.landmark)
            update_knee_angle(body_points)

        ball_positions = find_ball_positions(frame)
        update_metrics(hasPose=bool(body_points), hasBall=bool(ball_positions))

        if body_points and ball_positions:
            contact_detected = is_ball_close_to_wrists(frame, body_points, ball_positions)

        if body_points:
            is_correct, message, points = check_volleyball_position(body_points)
            posture_warning = None if is_correct else message
            update_metrics(
                score=points,
                warnings=posture_warning,
                postureWarnings=posture_warning,
                status="Wykryto sylwetkę. Analizuję pozycję.",
            )

            if contact_detected:
                update_metrics(
                    contactWarning=message,
                    contactScore=points,
                    isContact=True,
                    status="Wykryto moment odbicia",
                )
                contact_feedback_frames = 30
        else:
            update_metrics(
                warnings="Nie wykryto sylwetki",
                postureWarnings="Nie wykryto sylwetki",
                score=0,
                status="Czekam na wykrycie sylwetki",
            )

        if contact_feedback_frames > 0:
            contact_feedback_frames -= 1
        else:
            update_metrics(contactWarning=None, contactScore=None, isContact=False)

        ret, buffer = cv2.imencode(".jpg", frame)
        if not ret:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )

    camera.release()
    update_metrics(isAnalyzing=False, status="Analiza zatrzymana")

    end_time = datetime.utcnow()
    
    if stats["count_pose"] > 0:
        final_stats = {
            'total_contacts': stats["contacts"],
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


@app.get("/api/source")
def get_source():
    return {**snapshot_source(), "preprocessing": snapshot_preprocessed()}


@app.post("/api/analysis/stop")
def stop_analysis():
    stop_current_analysis()
    return {"ok": True}


@app.post("/api/source/camera")
def set_camera_source(camera_index: int = 0, user_id: str = None, authorization: str | None = Header(default=None)):
    access_token = authorization.removeprefix("Bearer ").strip() if authorization else None
    with state_lock:
        source_state.update(
            {
                "mode": "camera",
                "cameraIndex": camera_index,
                "videoPath": None,
                "videoName": None,
                "jobId": source_state["jobId"] + 1,
                "userId": user_id,
                "accessToken": access_token,
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
        status="Wybrano kamerę",
        contactWarning=None,
        contactScore=None,
        isContact=False,
        videoProcessingStatus="idle",
        videoProcessingProgress=0,
    )
    return {"ok": True, "source": "camera", "cameraIndex": camera_index}


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
