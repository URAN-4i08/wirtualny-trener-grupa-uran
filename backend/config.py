import os
import sys

from dotenv import load_dotenv
from ultralytics import YOLO

# Wymuś CPU path dla MediaPipe na macOS, żeby uniknąć crashy GL.
os.environ.setdefault("MEDIAPIPE_DISABLE_GPU", "1")

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

load_dotenv(os.path.join(ROOT_DIR, "frontend", ".env"))

UPLOAD_DIR = os.path.join(ROOT_DIR, "data", "uploads")
CACHE_DIR = os.path.join(UPLOAD_DIR, "processed")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

LIVE_STREAM_FPS = int(os.getenv("LIVE_STREAM_FPS", "25"))
LIVE_STREAM_WIDTH = int(os.getenv("LIVE_STREAM_WIDTH", "640"))
LIVE_ANALYSIS_WIDTH = int(os.getenv("LIVE_ANALYSIS_WIDTH", "480"))
LIVE_POSE_EVERY_N_FRAMES = int(os.getenv("LIVE_POSE_EVERY_N_FRAMES", "1"))
LIVE_BALL_EVERY_N_FRAMES = int(os.getenv("LIVE_BALL_EVERY_N_FRAMES", "2"))
LIVE_BALL_HOLD_FRAMES = int(os.getenv("LIVE_BALL_HOLD_FRAMES", "10"))
LIVE_BALL_CONF = float(os.getenv("LIVE_BALL_CONF", "0.15"))
LIVE_BALL_IMGSZ = int(os.getenv("LIVE_BALL_IMGSZ", "480"))
LIVE_BALL_USE_YOLO = os.getenv("LIVE_BALL_USE_YOLO", "0").strip().lower() in ("1", "true", "yes")
LIVE_NO_POSE_GRACE_FRAMES = int(os.getenv("LIVE_NO_POSE_GRACE_FRAMES", "4"))
LIVE_POSE_HOLD_FRAMES = int(os.getenv("LIVE_POSE_HOLD_FRAMES", "10"))
LIVE_POSE_SMOOTH_ALPHA = float(os.getenv("LIVE_POSE_SMOOTH_ALPHA", "0.35"))
LIVE_MESSAGE_STABLE_FRAMES = int(os.getenv("LIVE_MESSAGE_STABLE_FRAMES", "8"))
LIVE_HINT_MIN_INTERVAL_SEC = float(os.getenv("LIVE_HINT_MIN_INTERVAL_SEC", "1.5"))
LIVE_CONTACT_HOLD_FRAMES = int(os.getenv("LIVE_CONTACT_HOLD_FRAMES", "40"))

yolo_model = YOLO(os.getenv("YOLO_MODEL_PATH", "yolov8n.pt"))
