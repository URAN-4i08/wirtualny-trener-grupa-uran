import sys
import os
import cv2
import asyncio
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from mediapipe.python.solutions import drawing_utils as mp_drawing
from mediapipe.python.solutions import pose as mp_pose

# Add the root directory to path to import logic modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from logic.coach_engine import check_volleyball_position, calculate_angle

app = FastAPI()

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production (e.g., ["http://localhost:5173"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global metrics dictionary to share data between the video thread and WebSocket
global_metrics = {
    "score": 0,
    "kneeAngle": 120,
    "warnings": None,
    "isAnalyzing": False
}

# Initialize Models
yolo_model = YOLO('yolov8s.pt')
pose_tracker = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

def generate_frames():
    global global_metrics
    # Używamy lokalnego nagrania testowego zamiast kamery do celów testowych
    video_path = os.path.join(os.path.dirname(__file__), 'data', 'nagranie_testowe.mp4')
    camera = cv2.VideoCapture(video_path)
    
    if not camera.isOpened():
        print(f"Error: Could not open video file {video_path}.")
        # W razie braku pliku próbujemy kamerę 0
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            return

    while True:
        success, frame = camera.read()
        if not success:
            break
            
        global_metrics["isAnalyzing"] = True

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose_tracker.process(image_rgb)
        
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
            
            # Calculate average knee angle for the dashboard
            try:
                l_biodro = punkty_ciala["lewe_biodro"]
                l_kolano = punkty_ciala["lewe_kolano"]
                l_kostka = punkty_ciala["lewa_kostka"]
                kat_l_kolano = calculate_angle(l_biodro, l_kolano, l_kostka)
                
                p_biodro = punkty_ciala["prawe_biodro"]
                p_kolano = punkty_ciala["prawe_kolano"]
                p_kostka = punkty_ciala["prawa_kostka"]
                kat_p_kolano = calculate_angle(p_biodro, p_kolano, p_kostka)
                
                global_metrics["kneeAngle"] = int((kat_l_kolano + kat_p_kolano) / 2)
            except KeyError:
                pass

        # YOLO Ball detection
        results_yolo = yolo_model(frame, conf=0.4, verbose=False)
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
        
        # Check if the ball is close to wrists
        if punkty_ciala and ball_positions:
            for ball_center in ball_positions:
                for side in ['lewy_nadgarstek', 'prawy_nadgarstek']:
                    if side in punkty_ciala:
                        wrist_x = int(punkty_ciala[side].x * frame.shape[1])
                        wrist_y = int(punkty_ciala[side].y * frame.shape[0])
                        distance = ((ball_center[0] - wrist_x)**2 + (ball_center[1] - wrist_y)**2)**0.5
                        
                        if distance < 100:
                            cv2.line(frame, ball_center, (wrist_x, wrist_y), (0, 255, 255), 2)
                            moment_odbicia = True

        # Process the volleyball position logic if needed
        # We can either check it all the time or only on 'moment_odbicia'
        # Let's check it always to give live feedback, but maybe update score differently
        if punkty_ciala:
            czy_poprawna, komunikat, punkty = check_volleyball_position(punkty_ciala)
            global_metrics["score"] = punkty
            if not czy_poprawna and "IDEALNE ODBICIE" not in komunikat:
                global_metrics["warnings"] = komunikat
            else:
                global_metrics["warnings"] = None
        else:
            global_metrics["warnings"] = "Nie wykryto sylwetki"
            global_metrics["score"] = 0

        # Encode the frame
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    camera.release()
    global_metrics["isAnalyzing"] = False

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.websocket("/ws/metrics")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(global_metrics)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print("Client disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
