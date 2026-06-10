import os
import queue as _queue
import shutil
import sys
import threading
import time
from datetime import datetime

import cv2
import mediapipe as mp
import numpy as np

from backend.cameras import list_available_cameras, open_camera, open_camera_with_warmup, open_dual_cameras, pick_dual_camera_indices
from backend.config import (
    CACHE_DIR,
    LIVE_BALL_EVERY_N_FRAMES,
    LIVE_CONTACT_HOLD_FRAMES,
    LIVE_HINT_MIN_INTERVAL_SEC,
    LIVE_MESSAGE_STABLE_FRAMES,
    LIVE_NO_POSE_GRACE_FRAMES,
    LIVE_POSE_SMOOTH_ALPHA,
    LIVE_POSE_HOLD_FRAMES,
    LIVE_STREAM_FPS,
    LIVE_STREAM_WIDTH,
    UPLOAD_DIR,
    yolo_model,
)
from backend.state import (
    get_capture_source,
    preprocessed_state,
    snapshot_preprocessed,
    snapshot_source,
    source_state,
    state_lock,
    stop_current_analysis,
    update_metrics,
)
from backend.stabilizers import MessageDebouncer, PoseLandmarkStabilizer
from backend.bounce_helpers import build_bounce_record
from backend.supabase_client import save_training_session
from backend.training_session import (
    get_session_snapshot,
    is_recording_bounces,
    is_timed_session_active,
    record_bounce,
    session_metrics_overlay,
    try_advance_from_setup,
)
from backend.vision import (
    BallContactTracker,
    BallTracker,
    analyze_frame,
    build_body_points,
    build_live_status,
    get_pose_tracker,
    resize_to_width,
    stabilize_live_metrics,
)
from logic.biomechanics import (
    PROG_PILKA_KONTAKT_PX,
    WristTrajectoryTracker,
    analizuj_bok,
    analizuj_faze,
    analizuj_front,
    analizuj_stopy,
    fuzja_sensorow,
    nogi_widoczne,
)
from logic.coach_engine import VolleyballPostureEvaluator

mp_pose = mp.solutions.pose


def _contact_cooldown_frames() -> int:
    return max(2, int(LIVE_STREAM_FPS * 0.10))


def _register_bounce_on_contact(
    contact_tracker: BallContactTracker | None,
    bio_front: dict,
    *,
    metrics: dict | None = None,
    bio_bok: dict | None = None,
    stats: dict | None = None,
    new_contact: bool | None = None,
) -> dict | None:
    """Rejestruje odbicie tylko na zboczu kontaktu (piłka wchodzi w strefę przedramion)."""
    contact_edge = new_contact
    if contact_edge is None:
        contact_edge = bool(contact_tracker and contact_tracker.new_contact_this_frame)
    if not contact_edge:
        return None

    typ = bio_front.get("typ_odbicia") or "DOLNE"
    knee = metrics.get("kneeAngle") if metrics else None
    bounce = build_bounce_record(
        typ,
        knee=knee,
        bio_front=bio_front,
        bio_bok=bio_bok,
    )

    if is_recording_bounces():
        record_bounce(bounce)
    elif not is_timed_session_active() and stats is not None:
        stats["contacts"] += 1

    return {
        "typ": typ,
        "czas": time.time(),
        "gotowosc": bounce["gotowosc"],
        "feedback": bounce["feedback"],
    }


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
    # Krótka pauza na zwolnienie zasobów kamery po poprzedniej sesji
    time.sleep(0.3)
    
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

    if isinstance(capture_source, int):
        camera = open_camera_with_warmup(capture_source)
        if camera is None:
            live_pose_tracker.close()
            update_metrics(
                isAnalyzing=False,
                status=f"Nie mozna otworzyc kamery (indeks {capture_source})",
                warnings="Nie mozna otworzyc kamery",
                postureWarnings="Nie mozna otworzyc kamery",
                source="camera",
            )
            return
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
    contact_tracker = BallContactTracker(cooldown_frames=_contact_cooldown_frames())
    ball_tracker = BallTracker()
    pose_stabilizer = PoseLandmarkStabilizer(alpha=LIVE_POSE_SMOOTH_ALPHA, hold_frames=LIVE_POSE_HOLD_FRAMES)
    posture_evaluator = VolleyballPostureEvaluator()
    posture_debouncer = MessageDebouncer(stable_frames=LIVE_MESSAGE_STABLE_FRAMES)
    contact_debouncer = MessageDebouncer(stable_frames=max(3, LIVE_MESSAGE_STABLE_FRAMES // 2))
    leg_debouncer = MessageDebouncer(stable_frames=LIVE_MESSAGE_STABLE_FRAMES)
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

    # ── Pamięć ostatniego odbicia (FOLLOW_THROUGH przez 3s) ──────────────────
    last_bounce = None  # {'typ': str, 'czas': float, 'gotowosc': dict, 'feedback': str}

    while True:
        latest_source = snapshot_source()
        if (
            latest_source["mode"] != "camera"
            or latest_source["cameraIndex"] != current_source["cameraIndex"]
            or latest_source["jobId"] != current_source["jobId"]
        ):
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
        try:
            analyzed_frame, metrics = analyze_frame(
                display_frame,
                live_pose_tracker,
                detect_ball=frame_counter % max(1, LIVE_BALL_EVERY_N_FRAMES) == 0,
                source="camera",
                contact_tracker=contact_tracker,
                ball_tracker=ball_tracker,
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

        if contact_tracker and bio_front.get('dystans_pilka_px') is not None:
            contact_tracker.note_bio_distance(
                bio_front['dystans_pilka_px'],
                threshold_px=PROG_PILKA_KONTAKT_PX,
            )

        # ── INTEGRACJA BIOMECHANIKI: kamera boczna ───────────────────────────
        elif camera_mode == "side" and metrics.get("hasPose"):
            _bp = metrics.get("_bodyPoints", {})
            if _bp:
                bio_bok = analizuj_bok(_bp, wrist_tracker)
                metrics["komunikatKolana"] = bio_bok.get("komunikat_kolana")
                metrics["postureWarnings"] = bio_bok.get("komunikat_kolana")

        # ── Zapamiętaj odbicie (zbocze kontaktu piłka ↔ przedramiona) ───────
        bounce_info = _register_bounce_on_contact(
            contact_tracker,
            bio_front,
            metrics=metrics,
            stats=stats,
        )
        if bounce_info:
            last_bounce = bounce_info
            if not is_timed_session_active():
                metrics["totalContacts"] = stats["contacts"]

        # ── Analiza fazy ruchu ────────────────────────────────────────────────
        dystans = bio_front.get('dystans_pilka_px') if bio_front else None
        ostatnie_odbicie = None if is_timed_session_active() else last_bounce
        in_setup = get_session_snapshot().get("sessionStatus") == "setup"
        dane_fazy = analizuj_faze(
            bio_front or {}, bio_bok or {}, dystans,
            kat_kolana_front=metrics.get('kneeAngle'),
            ostatnie_odbicie=ostatnie_odbicie,
            tryb_setup=in_setup,
            punkty=metrics.get("_bodyPoints") or None,
        )

        now = time.time()
        posture_warning = metrics.get("postureWarnings")
        if posture_warning != last_posture_hint and (now - last_hint_sent_at) >= LIVE_HINT_MIN_INTERVAL_SEC:
            last_posture_hint = posture_warning
            last_hint_sent_at = now

        published_metrics = {
            **metrics,
            "postureWarnings": last_posture_hint,
            "warnings": last_posture_hint,
            "totalContacts": stats["contacts"],
        }
        published_metrics["komunikatNogi"] = leg_debouncer.update(metrics.get("komunikatNogi"))
        published_metrics["hasLegs"] = metrics.get("hasLegs", True)

        # Dodaj pola biomechaniczne do metryki publikowanej do GUI
        if bio_front:
            published_metrics["typOdbicia"] = bio_front.get("typ_odbicia")
            published_metrics["dystansPilkaRece"] = bio_front.get("dystans_pilka_px")
            if contact_tracker.new_contact_this_frame:
                published_metrics["isContact"] = True

        # Feedback po odbiciu (single-cam) — tylko poza sesją czasową
        if last_bounce and dane_fazy and dane_fazy.get('faza') == 'FOLLOW_THROUGH' and not is_timed_session_active():
            published_metrics["typOdbicia"] = last_bounce['typ']
            published_metrics["komunikatFuzji"] = last_bounce['feedback']
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

        try_advance_from_setup(
            dane_fazy.get('gotowosc') if dane_fazy else None,
            has_pose=bool(metrics.get('hasPose')),
            has_legs=bool(metrics.get('hasLegs')),
            posture_warnings=published_metrics.get('postureWarnings'),
        )

        published_metrics.pop("_bodyPoints", None)
        published_metrics.pop("_ballCenters", None)
        published_metrics.update(session_metrics_overlay())

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
        if contact_tracker.new_contact_this_frame:
            h_f = analyzed_frame.shape[0]
            w_f = analyzed_frame.shape[1]
            overlay = analyzed_frame.copy()
            cv2.rectangle(overlay, (0, h_f - 6), (w_f, h_f), (0, 220, 80), -1)
            cv2.addWeighted(overlay, 0.7, analyzed_frame, 0.3, 0, analyzed_frame)

        ret, buffer = cv2.imencode(".jpg", analyzed_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 72])
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
    """
    import queue as _queue
    import numpy as np

    # ── KLUCZOWE: natychmiast wyślij klatkę "ładowania" ──────────────────────
    # Bez tego przeglądarka zrywa połączenie MJPEG bo generator milczy 2+ sekundy
    loading_frame = np.zeros((360, 960, 3), dtype=np.uint8)
    cv2.putText(loading_frame, "Dual-Cam: inicjalizacja kamer...", (80, 180),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2, cv2.LINE_AA)
    ret_l, buf_l = cv2.imencode(".jpg", loading_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    if ret_l:
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + buf_l.tobytes() + b"\r\n")

    cam_a = int(current_source.get("cameraIndex") or 0)
    cam_b = current_source.get("cameraIndex2")
    if cam_b is None:
        update_metrics(isAnalyzing=False, status="Brak drugiej kamery", warnings="Brak drugiej kamery", source="camera")
        return

    cam_b = int(cam_b)
    print(f"[DUAL-CAM] Start: front={cam_a}, bok={cam_b}")

    # Pauza na zwolnienie zasobów po poprzedniej sesji (Continuity Camera)
    time.sleep(0.8)

    camera1, camera2 = open_dual_cameras(cam_a, cam_b)

    if camera1 is not None and camera2 is not None:
        for cam in (camera1, camera2):
            cam.set(cv2.CAP_PROP_FRAME_WIDTH, LIVE_STREAM_WIDTH)
            cam.set(cv2.CAP_PROP_FPS, LIVE_STREAM_FPS)
        print(f"[DUAL-CAM] Obie kamery otwarte: front={cam_a}, bok={cam_b}")
    else:
        available = list_available_cameras(use_cache=False)
        if len(available) == 0:
            err_msg = "Nie wykryto kamery. Sprawdź uprawnienia kamery dla Terminala/Pythona."
        elif len(available) == 1:
            err_msg = (
                f"Wykryto tylko 1 kamerę (indeks {available[0]}). "
                "Upewnij się, że iPhone jest odblokowany i Continuity Camera włączona."
            )
        else:
            err_msg = (
                f"Nie udało się otworzyć obu kamer (front={cam_a}, bok={cam_b}). "
                f"Wykryte indeksy: {available}. Spróbuj „Zamień kamery”."
            )
        print(f"[DUAL-CAM] {err_msg}")
        update_metrics(isAnalyzing=False, status=err_msg, warnings=err_msg, source="camera")
        err_frame = np.zeros((360, 960, 3), dtype=np.uint8)
        cv2.putText(err_frame, err_msg[:85], (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.putText(err_frame, "iPhone: odblokuj, Bluetooth+WiFi, to samo Apple ID", (20, 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
        ret_e, buf_e = cv2.imencode(".jpg", err_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if ret_e:
            fb = b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + buf_e.tobytes() + b"\r\n"
            for _ in range(50):
                yield fb
                time.sleep(0.1)
        return

    print("[DUAL-CAM] Obie kamery otwarte — uruchamiam watki analizy...")

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
    contact_tracker    = BallContactTracker(cooldown_frames=_contact_cooldown_frames())
    ball_tracker_front = BallTracker()
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
                    ball_tracker=ball_tracker_front,
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
            if contact_tracker and dane_front.get("dystans_pilka_px") is not None:
                contact_tracker.note_bio_distance(
                    dane_front["dystans_pilka_px"],
                    threshold_px=PROG_PILKA_KONTAKT_PX,
                )
            contact_edge = bool(contact_tracker and contact_tracker.new_contact_this_frame)
            contact_tracker.latch_contact_edge()
            # Wynik do kolejki (nadpisuje jeśli pełna — drop old frame)
            try:
                kolejka_front.put_nowait((analyzed, m, dane_front, contact_edge))
            except _queue.Full:
                try:
                    kolejka_front.get_nowait()
                except _queue.Empty:
                    pass
                kolejka_front.put_nowait((analyzed, m, dane_front, contact_edge))


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
            if bp_bok:
                dane_bok["nogi_widoczne"] = nogi_widoczne(bp_bok)
                dane_bok["dane_stopy_bok"] = analizuj_stopy(bp_bok)
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
    last_bounce = None  # pamięć ostatniego odbicia
    dual_contact_count = 0
    leg_debouncer = MessageDebouncer(stable_frames=LIVE_MESSAGE_STABLE_FRAMES)

    # ── Pętla główna generatora (synchronizacja klatek z obu wątków) ─────────
    while True:
        latest_source = snapshot_source()
        if latest_source["mode"] != "camera_dual" or latest_source["jobId"] != current_source["jobId"]:
            break

        try:
            # Blokujące pobieranie z timeoutem — "software lock-step"
            # Jeśli jedna kamera jest wolniejsza, czekamy max 80 ms
            frame_front, m_front, dane_front, contact_edge_front = kolejka_front.get(timeout=0.08)
            frame_bok,   m_bok,   dane_bok   = kolejka_bok.get(timeout=0.08)
        except Exception:
            # Jedna z kamer spóźniona — użyj ostatnich metryk i kontynuuj
            time.sleep(0.02)
            continue

        # ── FUZJA SENSORÓW ────────────────────────────────────────────────────
        # PUNKT INTEGRACJI: wywołaj fuzja_sensorow() dla obu kamer
        wynik_fuzji = fuzja_sensorow(dane_front, dane_bok)

        # ── Analiza stóp (front + zapas z kamery bocznej) ─────────────────────
        bp_front_latest = m_front.get('_bodyPoints', {})
        dane_stopy = analizuj_stopy(bp_front_latest)
        bok_stopy = dane_bok.get('dane_stopy_bok') or {}
        if bok_stopy.get('nogi_widoczne') and not dane_stopy.get('nogi_widoczne'):
            dane_stopy = {**dane_stopy, **bok_stopy}
        elif dane_bok.get('nogi_widoczne'):
            dane_stopy = {**dane_stopy, 'nogi_widoczne': True}

        dane_front_merged = {**dane_front, 'dane_stopy': dane_stopy}
        dystans = dane_front.get('dystans_pilka_px')
        new_contact = bool(contact_edge_front) or contact_tracker.take_latched_edge()

        bounce_info = _register_bounce_on_contact(
            contact_tracker,
            dane_front_merged,
            metrics=m_front,
            bio_bok=dane_bok,
            new_contact=new_contact,
        )
        if bounce_info:
            if not is_timed_session_active():
                dual_contact_count += 1
            last_bounce = bounce_info

        kat_front = m_front.get('kneeAngle') if m_front else None
        in_setup = get_session_snapshot().get("sessionStatus") == "setup"
        bp_front = m_front.get("_bodyPoints") or {}
        dane_fazy = analizuj_faze(
            dane_front_merged,
            dane_bok,
            dystans,
            kat_kolana_front=kat_front,
            ostatnie_odbicie=None if is_timed_session_active() else last_bounce,
            tryb_setup=in_setup,
            punkty=bp_front or None,
        )

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
            komunikat_kontaktu = "Odbicie OK — spróbuj zaangażować nogi!"

        metrics.pop("_bodyPoints", None)
        metrics.pop("_ballCenters", None)

        has_legs = bool(
            m_front.get("hasLegs")
            or m_bok.get("hasLegs")
            or dane_stopy.get("nogi_widoczne")
            or dane_bok.get("nogi_widoczne")
        )
        leg_msg = m_front.get("komunikatNogi") or m_bok.get("komunikatNogi")
        posture_live = m_front.get("postureWarnings") or m_bok.get("postureWarnings")
        session_status = get_session_snapshot().get("sessionStatus")
        in_timed = session_status in ("setup", "prep", "active", "summary")

        metrics.update({
            "score": wynik_fuzji["ocena_fuzji"] if not in_timed else 0,
            "fuzjaOcena": wynik_fuzji["ocena_fuzji"],
            "postureWarnings": posture_live if in_setup else wynik_fuzji["komunikat_fuzji"],
            "warnings": posture_live if in_setup else wynik_fuzji["komunikat_fuzji"],
            "contactWarning": komunikat_kontaktu,
            "brakPracyNog": wynik_fuzji["brak_pracy_nog"],
            "typOdbicia": wynik_fuzji["typ_odbicia"],
            "komunikatKolana": dane_bok.get("komunikat_kolana"),
            "katBiodra": dane_bok.get("kat_biodra"),
            "zamachWykryty": dane_bok.get("zamach_wykryty", False),
            "dynamikaZamachu": dane_bok.get("dynamika_zamachu"),
            "dystansPilkaRece": dane_front.get("dystans_pilka_px"),
            "isContact": new_contact,
            "cameraMode": "dual",
            "totalContacts": dual_contact_count,
            "status": wynik_fuzji["komunikat_fuzji"] or build_live_status(metrics),
            "videoProcessingStatus": "idle",
            "videoProcessingProgress": 0,
            "rozstawienieStop": dane_stopy.get('rozstawienie_stop') if dane_stopy else None,
            "balansStop": dane_stopy.get('balans') if dane_stopy else None,
            "fazaRuchu": dane_fazy.get('faza', 'OCZEKIWANIE') if dane_fazy else 'OCZEKIWANIE',
            "gotowoscPrzedOdbiciem": dane_fazy.get('gotowosc') if dane_fazy else None,
            "feedbackFazy": dane_fazy.get('feedback_fazy') if dane_fazy else None,
            "hasLegs": has_legs,
            "komunikatNogi": leg_debouncer.update(leg_msg),
        })
        try_advance_from_setup(
            dane_fazy.get('gotowosc') if dane_fazy else None,
            has_pose=bool(metrics.get('hasPose')),
            has_legs=bool(has_legs),
            posture_warnings=posture_live,
        )
        metrics.update(session_metrics_overlay())

        update_metrics(**metrics)

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
        if new_contact:
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

        ret, buffer = cv2.imencode(".jpg", combined, [int(cv2.IMWRITE_JPEG_QUALITY), 68])
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
