import asyncio
import os
import sys
import threading
import time

import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from logic.coach_engine import evaluate_live_reception_position
from vision.detector import BallDetector
from vision.pose_analysis import PoseAnalyzer


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FrontCameraPayload(BaseModel):
    enabled: bool


class LiveCameraSession:
    def __init__(self):
        self.side_camera_index = 0
        self.front_camera_index = 1
        self.width = 640
        self.height = 480
        self.include_front = False
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

        self.side_pose = PoseAnalyzer(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.front_pose = PoseAnalyzer(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.ball_detector = BallDetector(model_path="yolov8s.pt", conf_threshold=0.4)

        self.side_frame = None
        self.front_frame = None
        self.side_status = "Oczekiwanie"
        self.front_status = "Wyłączona"
        self.last_hit_at = None
        self.last_hit_message = "Czekam na przyjęcie"
        self.last_hit_score = 0

        self.metrics = {
            "score": 0,
            "kneeAngle": 0,
            "elbowAngle": 0,
            "warnings": None,
            "weakPoints": [],
            "isAnalyzing": False,
            "hitDetected": False,
            "lastHitAt": None,
            "sideCamera": {"enabled": True, "index": self.side_camera_index, "status": self.side_status},
            "frontCamera": {"enabled": False, "index": self.front_camera_index, "status": self.front_status},
        }

    def set_front_enabled(self, enabled):
        with self.lock:
            self.include_front = enabled
            self.front_status = "Włączona" if enabled else "Wyłączona"
            self.metrics["frontCamera"] = {
                "enabled": enabled,
                "index": self.front_camera_index,
                "status": self.front_status,
            }

    def ensure_started(self):
        if self.running:
            return
        self.side_pose = PoseAnalyzer(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.front_pose = PoseAnalyzer(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=2.0)
        with self.lock:
            self.side_frame = None
            self.front_frame = None
            self.side_status = "Zatrzymana"
            self.front_status = "Wyłączona" if not self.include_front else "Zatrzymana"
            self.metrics["isAnalyzing"] = False
            self.metrics["hitDetected"] = False
            self.metrics["sideCamera"] = {
                "enabled": True,
                "index": self.side_camera_index,
                "status": self.side_status,
            }
            self.metrics["frontCamera"] = {
                "enabled": self.include_front,
                "index": self.front_camera_index,
                "status": self.front_status,
            }

    def _open_camera(self, index):
        camera = cv2.VideoCapture(index)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        return camera

    def _run(self):
        side_camera = self._open_camera(self.side_camera_index)
        front_camera = None
        front_opened_for = False

        try:
            while self.running:
                if not side_camera.isOpened():
                    self._set_camera_status("Błąd kamery 45°", "Wyłączona")
                    time.sleep(0.2)
                    continue

                include_front = self.include_front
                if include_front and not front_opened_for:
                    front_camera = self._open_camera(self.front_camera_index)
                    front_opened_for = True
                elif not include_front and front_opened_for:
                    if front_camera is not None:
                        front_camera.release()
                    front_camera = None
                    front_opened_for = False
                    with self.lock:
                        self.front_frame = None

                ok_side, side_frame = side_camera.read()
                if not ok_side:
                    self._set_camera_status("Brak klatki z kamery 45°", self.front_status)
                    time.sleep(0.02)
                    continue

                front_frame = None
                if include_front and front_camera is not None and front_camera.isOpened():
                    ok_front, raw_front_frame = front_camera.read()
                    if ok_front:
                        front_frame = raw_front_frame
                        self.front_status = "Aktywna"
                    else:
                        self.front_status = "Brak klatki"
                elif include_front:
                    self.front_status = "Nie można otworzyć kamery"
                else:
                    self.front_status = "Wyłączona"

                processed_side, processed_front, metrics = self._analyze(side_frame, front_frame)

                with self.lock:
                    self.side_frame = processed_side
                    self.front_frame = processed_front
                    self.side_status = "Aktywna"
                    self.metrics.update(metrics)
                    self.metrics["sideCamera"] = {
                        "enabled": True,
                        "index": self.side_camera_index,
                        "status": self.side_status,
                    }
                    self.metrics["frontCamera"] = {
                        "enabled": include_front,
                        "index": self.front_camera_index,
                        "status": self.front_status,
                    }

                time.sleep(0.01)
        finally:
            side_camera.release()
            if front_camera is not None:
                front_camera.release()
            self.side_pose.close()
            self.front_pose.close()

    def _set_camera_status(self, side_status, front_status):
        with self.lock:
            self.side_status = side_status
            self.front_status = front_status
            self.metrics["isAnalyzing"] = False
            self.metrics["sideCamera"] = {
                "enabled": True,
                "index": self.side_camera_index,
                "status": side_status,
            }
            self.metrics["frontCamera"] = {
                "enabled": self.include_front,
                "index": self.front_camera_index,
                "status": front_status,
            }

    def _analyze(self, side_frame, front_frame):
        side_rgb = cv2.cvtColor(side_frame, cv2.COLOR_BGR2RGB)
        side_landmarks = self.side_pose.analyze_frame(side_rgb)
        front_landmarks = None

        if side_landmarks and self.side_pose.last_landmarks:
            self.side_pose.draw_landmarks(side_frame, self.side_pose.last_landmarks)

        if front_frame is not None:
            front_rgb = cv2.cvtColor(front_frame, cv2.COLOR_BGR2RGB)
            front_landmarks = self.front_pose.analyze_frame(front_rgb)
            if front_landmarks and self.front_pose.last_landmarks:
                self.front_pose.draw_landmarks(front_frame, self.front_pose.last_landmarks)

        side_balls = self.ball_detector.detect_ball(side_frame)
        self.ball_detector.draw_detections(side_frame, side_balls)

        front_balls = []
        if front_frame is not None:
            front_balls = self.ball_detector.detect_ball(front_frame)
            self.ball_detector.draw_detections(front_frame, front_balls, color=(0, 255, 255))

        hit_detected = self._detect_hit(side_frame, side_landmarks, side_balls)
        if front_frame is not None:
            hit_detected = self._detect_hit(front_frame, front_landmarks, front_balls) or hit_detected

        position = evaluate_live_reception_position(side_landmarks, front_landmarks)
        if hit_detected:
            self.last_hit_at = time.time()
            self.last_hit_message = position["message"]
            self.last_hit_score = position["score"]

        self._draw_hud(side_frame, "Kamera 45°", position, hit_detected)
        if front_frame is not None:
            self._draw_hud(front_frame, "Kamera frontowa", position, hit_detected)

        return side_frame, front_frame, {
            "score": position["score"],
            "kneeAngle": position["knee_angle"],
            "elbowAngle": position["elbow_angle"],
            "warnings": None if position["is_correct"] else position["message"],
            "weakPoints": position["weak_points"],
            "isAnalyzing": True,
            "hitDetected": hit_detected,
            "lastHitAt": self.last_hit_at,
            "lastHitMessage": self.last_hit_message,
            "lastHitScore": self.last_hit_score,
        }

    def _detect_hit(self, frame, landmarks, ball_detections):
        if not landmarks or not ball_detections:
            return False

        frame_height, frame_width = frame.shape[:2]
        for ball in ball_detections:
            for wrist_name in ("lewy_nadgarstek", "prawy_nadgarstek"):
                if wrist_name not in landmarks:
                    continue
                wrist = landmarks[wrist_name]
                wrist_point = (int(wrist.x * frame_width), int(wrist.y * frame_height))
                if self.ball_detector.is_ball_near_point(ball["center"], wrist_point, distance_threshold=100):
                    cv2.line(frame, ball["center"], wrist_point, (0, 255, 255), 2)
                    return True
        return False

    def _draw_hud(self, frame, label, position, hit_detected):
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 72), (0, 0, 0), -1)
        cv2.putText(frame, label, (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (173, 198, 255), 2)
        status = "Odbicie wykryte" if hit_detected else "Analiza pozycji przed i w trakcie przyjęcia"
        color = (0, 255, 0) if position["is_correct"] else (0, 0, 255)
        cv2.putText(frame, status, (12, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    def get_metrics(self, start=False):
        if start:
            self.ensure_started()
        with self.lock:
            return dict(self.metrics)

    def get_frame(self, camera_name):
        self.ensure_started()
        with self.lock:
            frame = self.front_frame if camera_name == "front" else self.side_frame
            if frame is None:
                return None
            ok, buffer = cv2.imencode(".jpg", frame)
            if not ok:
                return None
            return buffer.tobytes()


live_session = LiveCameraSession()


def generate_frames(camera_name):
    while True:
        frame = live_session.get_frame(camera_name)
        if frame is None:
            time.sleep(0.05)
            continue
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"


@app.get("/video_feed")
def legacy_video_feed():
    return StreamingResponse(generate_frames("side"), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/video_feed/{camera_name}")
def video_feed(camera_name: str):
    if camera_name not in {"side", "front"}:
        camera_name = "side"
    return StreamingResponse(generate_frames(camera_name), media_type="multipart/x-mixed-replace; boundary=frame")


@app.post("/api/camera/front")
def set_front_camera(payload: FrontCameraPayload):
    live_session.set_front_enabled(payload.enabled)
    return live_session.get_metrics()


@app.get("/api/metrics")
def get_metrics():
    return live_session.get_metrics()


@app.post("/api/session/stop")
def stop_session():
    live_session.stop()
    return live_session.get_metrics()


@app.websocket("/ws/metrics")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    live_session.ensure_started()
    try:
        while True:
            await websocket.send_json(live_session.get_metrics())
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print("Client disconnected")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
