import asyncio
import os
import shutil
import threading
import time

from fastapi import APIRouter, File, Header, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse

from audio import speech_recognition as vosk_stt
from backend.cameras import get_camera_devices, list_available_cameras, pick_dual_camera_indices, suggest_dual_indices
from backend.state import (
    preprocessed_state,
    snapshot_metrics,
    snapshot_preprocessed,
    snapshot_source,
    source_state,
    state_lock,
    stop_current_analysis,
    swap_dual_camera_indices,
    update_metrics,
)
from backend.streams import generate_frames, preprocess_uploaded_video, stream_dual_camera_frames
from backend.training_session import start_session, stop_session

router = APIRouter()


@router.get("/api/cameras")
def get_cameras(refresh: bool = False):
    """Zwraca indeksy kamer wykrytych w systemie (na macOS przez ffmpeg/AVFoundation)."""
    devices = get_camera_devices(refresh=refresh)
    indices = [device["index"] for device in devices]
    return {"ok": True, "cameras": indices, "devices": devices, "count": len(indices)}


@router.get("/api/source")
def get_source():
    return {**snapshot_source(), "preprocessing": snapshot_preprocessed()}


@router.post("/api/analysis/stop")
def stop_analysis():
    stop_session()
    stop_current_analysis()
    return {"ok": True}


@router.post("/api/session/start")
def start_training_session(duration: int = 30):
    start_session(duration_sec=duration)
    update_metrics(
        sessionStatus="setup",
        sessionSecondsRemaining=0,
        sessionContactCount=0,
        sessionSummary=None,
        totalContacts=0,
        fazaRuchu="OCZEKIWANIE",
        feedbackFazy="Ustaw postawę — zaznacz wszystkie segmenty na zielono",
    )
    return {"ok": True}


@router.post("/api/session/stop")
def stop_training_session():
    stop_session()
    update_metrics(
        sessionStatus="idle",
        sessionSecondsRemaining=0,
        sessionContactCount=0,
        sessionSummary=None,
        fazaRuchu="OCZEKIWANIE",
    )
    return {"ok": True}


@router.post("/api/source/camera")
def set_camera_source(
    camera_index: int = 0,
    user_id: str = None,
    authorization: str | None = Header(default=None),
    camera_mode: str = "front",
):
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


@router.post("/api/source/camera-dual")
def set_dual_camera_source(
    camera_index_a: int = 0,
    camera_index_b: int = 1,
    user_id: str = None,
    authorization: str | None = Header(default=None),
):
    access_token = authorization.removeprefix("Bearer ").strip() if authorization else None
    available = list_available_cameras(refresh=True)
    if len(available) < 2:
        devices = get_camera_devices(refresh=False)
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": (
                    "Dual-Cam wymaga dwóch kamer w systemie. "
                    "iPhone musi być widoczny jako Continuity Camera (Ustawienia → AirPlay i Continuity). "
                    "Sam kabel USB nie wystarczy — odblokuj iPhone i zaufaj temu Macowi."
                ),
                "availableCameras": available,
                "devices": devices,
            },
        )

    preferred_front, preferred_side = suggest_dual_indices(camera_index_a, camera_index_b)

    # Dopiero gdy są 2 kamery — zwolnij aktywny strumień przed walidacją pary.
    with state_lock:
        source_state["jobId"] = source_state["jobId"] + 1
    time.sleep(0.6)
    picked = pick_dual_camera_indices(preferred_front, preferred_side)
    if picked is None:
        available = list_available_cameras(use_cache=True)
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "Nie udało się uruchomić obu kamer jednocześnie. Spróbuj odblokować iPhone albo zamienić kamery.",
                "availableCameras": available,
            },
        )
    camera_index_a, camera_index_b = picked
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


@router.post("/api/source/camera-dual/swap")
def swap_dual_camera_source():
    swapped = swap_dual_camera_indices()
    if swapped is None:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Tryb dual-cam nie jest aktywny"})
    front_idx, side_idx = swapped
    update_metrics(
        status=f"Zamieniono kamery: frontowa ({front_idx}) + boczna ({side_idx})",
    )
    return {
        "ok": True,
        "cameraIndex": front_idx,
        "cameraIndex2": side_idx,
    }


@router.post("/api/source/upload")
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


@router.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@router.get("/video_feed_dual")
def video_feed_dual():
    current_source = snapshot_source()
    if current_source["mode"] != "camera_dual":
        return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")
    return StreamingResponse(
        stream_dual_camera_frames(current_source),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/api/voice/status")
def voice_status():
    return {
        "ready": vosk_stt.model_is_ready(),
        "engine": "vosk",
        "model": vosk_stt.MODEL_DIR_NAME,
        "sampleRate": vosk_stt.SAMPLE_RATE,
    }


@router.post("/api/voice/prepare")
def voice_prepare():
    try:
        vosk_stt.download_model()
        return {"ok": True, "ready": True}
    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "ready": False, "error": str(error)},
        )


@router.websocket("/ws/voice")
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


@router.websocket("/ws/metrics")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(snapshot_metrics())
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print("Client disconnected")
