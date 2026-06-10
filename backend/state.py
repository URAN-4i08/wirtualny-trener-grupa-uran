import threading

from audio.voice_control import get_announcer

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
    "hasLegs": False,
    "komunikatNogi": None,
    "hasBall": False,
    "status": "Oczekiwanie na uruchomienie analizy",
    "source": "camera",
    "isAnalyzing": False,
    "videoProcessingStatus": "idle",
    "videoProcessingProgress": 0,
    "cameraMode": "front",
    "fuzjaOcena": 0,
    "komunikatFuzji": None,
    "brakPracyNog": False,
    "typOdbicia": None,
    "komunikatKolana": None,
    "katBiodra": None,
    "dystansPilkaRece": None,
    "zamachWykryty": False,
    "dynamikaZamachu": None,
    "fazaRuchu": "OCZEKIWANIE",
    "rozstawienieStop": None,
    "balansStop": None,
    "gotowoscPrzedOdbiciem": None,
    "feedbackFazy": None,
    "sessionStatus": "idle",
    "sessionSecondsRemaining": 0,
    "sessionContactCount": 0,
    "sessionSummary": None,
}


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


def swap_dual_camera_indices():
    with state_lock:
        if source_state.get("mode") != "camera_dual":
            return None
        a = source_state["cameraIndex"]
        b = source_state["cameraIndex2"]
        source_state["cameraIndex"] = b
        source_state["cameraIndex2"] = a
        source_state["jobId"] = source_state["jobId"] + 1
        return int(source_state["cameraIndex"]), int(source_state["cameraIndex2"])
