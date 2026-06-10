import contextlib
import io
import os
import re
import subprocess
import sys
import threading
import time

import cv2

# Wycisz natywne logi OpenCV (C++ idzie na stderr, nie przez Python logging).
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

# Continuity Camera (iPhone) bywa wolna — cache skanowania i dłuższy warmup.
_CAMERA_CACHE: list[int] | None = None
_CAMERA_NAMES: dict[int, str] = {}
_CAMERA_CACHE_AT = 0.0
_CACHE_TTL_SEC = 30.0
_PROBE_LOCK = threading.Lock()
_MAX_PROBE_INDEX = 6 if sys.platform == "darwin" else 6


@contextlib.contextmanager
def _quiet_opencv():
    """Wycisza spam OpenCV przy próbach nieistniejących indeksów kamer."""
    previous_level = None
    if hasattr(cv2, "utils") and hasattr(cv2.utils, "logging"):
        previous_level = cv2.utils.logging.getLogLevel()
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
    stderr_buffer = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr_buffer):
            yield
    finally:
        if previous_level is not None:
            cv2.utils.logging.setLogLevel(previous_level)


def open_camera(index: int):
    """Otwiera kamerę z preferowanym backendem na danym systemie."""
    with _quiet_opencv():
        if sys.platform == "darwin":
            cap = cv2.VideoCapture(int(index), cv2.CAP_AVFOUNDATION)
        else:
            cap = cv2.VideoCapture(int(index))
    return cap


def _warmup_reads(cap, attempts: int, delay_sec: float) -> bool:
    for _ in range(attempts):
        success, frame = cap.read()
        if success and frame is not None and frame.size > 0:
            return True
        time.sleep(delay_sec)
    return False


def open_camera_with_warmup(index: int, attempts: int | None = None, delay_sec: float | None = None):
    """
    Otwiera kamerę i czeka na pierwszą klatkę.
    Indeks >= 1 (np. iPhone / Continuity Camera) dostaje więcej prób i czasu.
    """
    is_continuity = int(index) >= 1
    attempts = attempts or (15 if is_continuity else 8)
    delay_sec = delay_sec or (0.2 if is_continuity else 0.1)

    cap = open_camera(index)
    if not cap.isOpened():
        cap.release()
        return None

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if _warmup_reads(cap, attempts, delay_sec):
        return cap

    cap.release()
    return None


def _quick_probe(index: int) -> bool:
    """Szybkie sprawdzenie indeksu bez pełnego warmup — do skanowania listy kamer."""
    cap = open_camera(index)
    if not cap.isOpened():
        cap.release()
        return False
    success, frame = cap.read()
    cap.release()
    return bool(success and frame is not None and frame.size > 0)


def _is_real_camera(name: str) -> bool:
    """Pomija wirtualne urządzenia AVFoundation (Widok blatu, nagrywanie ekranu)."""
    lowered = name.lower()
    skip_tokens = (
        "widok blatu",
        "desk view",
        "capture screen",
        "screen capture",
        "nagrywanie ekranu",
    )
    return not any(token in lowered for token in skip_tokens)


def _list_cameras_ffmpeg() -> list[tuple[int, str]]:
    """
    Lista urządzeń wideo przez AVFoundation (ffmpeg) — nie otwiera kamer.
    Na macOS wykrywa też iPhone (Continuity Camera), którego OpenCV często nie widzi przy szybkim skanie.
    """
    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-f",
                "avfoundation",
                "-list_devices",
                "true",
                "-i",
                "",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []

    devices: list[tuple[int, str]] = []
    in_video = False
    for line in proc.stderr.splitlines():
        if "AVFoundation video devices" in line:
            in_video = True
            continue
        if "AVFoundation audio devices" in line:
            break
        if not in_video:
            continue
        match = re.search(r"\[(\d+)\]\s*(.+?)\s*$", line.strip())
        if match:
            name = match.group(2).strip()
            if _is_real_camera(name):
                devices.append((int(match.group(1)), name))
    return devices


def get_camera_devices(*, refresh: bool = False) -> list[dict]:
    """Zwraca listę kamer z indeksami i nazwami urządzeń."""
    indices = list_available_cameras(refresh=refresh)
    return [{"index": idx, "name": _CAMERA_NAMES.get(idx, f"Kamera {idx}")} for idx in indices]


def _is_iphone_camera(name: str) -> bool:
    lowered = name.lower()
    if any(token in lowered for token in ("widok blatu", "desk view")):
        return False
    return any(token in lowered for token in ("iphone", "continuity", "ios")) or (
        "kamera (" in lowered and "macbook" not in lowered and "facetime" not in lowered
    )


def _is_builtin_mac_camera(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in ("facetime", "built-in", "macbook", "isight"))


def suggest_dual_indices(preferred_front: int = 0, preferred_side: int = 1) -> tuple[int, int]:
    """
    Dobiera parę (front, bok): MacBook jako front, iPhone jako bok — jeśli widać oba w systemie.
    """
    devices = _list_cameras_ffmpeg() if sys.platform == "darwin" else []
    if len(devices) >= 2:
        by_index = {idx: name for idx, name in devices}
        iphone = [idx for idx, name in by_index.items() if _is_iphone_camera(name)]
        mac = [idx for idx, name in by_index.items() if _is_builtin_mac_camera(name)]
        other = [idx for idx in by_index if idx not in iphone and idx not in mac]

        front = mac[0] if mac else (other[0] if other else devices[0][0])
        side = iphone[0] if iphone else devices[1][0]
        if front == side and len(devices) >= 2:
            side = devices[1][0] if devices[0][0] == front else devices[0][0]
        return front, side

    available = list_available_cameras(use_cache=True)
    if len(available) >= 2:
        return available[0], available[1]
    return preferred_front, preferred_side


def probe_camera(index: int) -> bool:
    """Lekkie sprawdzenie indeksu — do skanowania listy (bez długiego warmup)."""
    if _quick_probe(index):
        time.sleep(0.1)
        return True
    return False


def probe_camera_thorough(index: int) -> bool:
    """Dokładniejsze sprawdzenie — np. Continuity Camera (iPhone) bywa wolna."""
    if int(index) >= 1 and sys.platform == "darwin":
        cap = open_camera_with_warmup(index, attempts=8, delay_sec=0.15)
        if cap is None:
            return False
        cap.release()
        time.sleep(0.25)
        return True
    return probe_camera(index)


def validate_dual_pair(front_index: int, side_index: int) -> bool:
    """Sprawdza, czy obie kamery można otworzyć jednocześnie (jak w Dual-Cam)."""
    if front_index == side_index:
        return False

    cam_a = open_camera_with_warmup(front_index)
    if cam_a is None:
        return False

    time.sleep(0.5)
    cam_b = open_camera_with_warmup(side_index)
    if cam_b is None:
        cam_a.release()
        time.sleep(0.3)
        return False

    ok_a = _warmup_reads(cam_a, 3, 0.05)
    ok_b = _warmup_reads(cam_b, 3, 0.05)
    cam_a.release()
    cam_b.release()
    time.sleep(0.4)
    return ok_a and ok_b


def list_available_cameras(max_index: int | None = None, use_cache: bool = True, refresh: bool = False) -> list[int]:
    global _CAMERA_CACHE, _CAMERA_CACHE_AT, _CAMERA_NAMES

    if refresh:
        invalidate_camera_cache()

    max_index = max_index or _MAX_PROBE_INDEX
    now = time.time()
    if use_cache and _CAMERA_CACHE is not None and (now - _CAMERA_CACHE_AT) < _CACHE_TTL_SEC:
        return list(_CAMERA_CACHE)

    with _PROBE_LOCK:
        if use_cache and _CAMERA_CACHE is not None and (time.time() - _CAMERA_CACHE_AT) < _CACHE_TTL_SEC:
            return list(_CAMERA_CACHE)

        if sys.platform == "darwin":
            ffmpeg_devices = _list_cameras_ffmpeg()
            if ffmpeg_devices:
                _CAMERA_NAMES = {idx: name for idx, name in ffmpeg_devices}
                _CAMERA_CACHE = [idx for idx, _ in ffmpeg_devices]
                _CAMERA_CACHE_AT = time.time()
                return list(_CAMERA_CACHE)

        available: list[int] = []
        consecutive_misses = 0
        for index in range(max_index):
            found = probe_camera(index)
            if found:
                available.append(index)
                consecutive_misses = 0
                if index == 0 and 1 < max_index and 1 not in available:
                    if probe_camera_thorough(1):
                        available.append(1)
                        consecutive_misses = 0
                continue

            consecutive_misses += 1
            if consecutive_misses >= 2 and (available or index >= 1):
                break

        _CAMERA_CACHE = available
        _CAMERA_NAMES = {idx: f"Kamera {idx}" for idx in available}
        _CAMERA_CACHE_AT = time.time()
        return list(available)


def invalidate_camera_cache():
    global _CAMERA_CACHE, _CAMERA_CACHE_AT, _CAMERA_NAMES
    _CAMERA_CACHE = None
    _CAMERA_NAMES = {}
    _CAMERA_CACHE_AT = 0.0


def pick_dual_camera_indices(preferred_front: int, preferred_side: int) -> tuple[int, int] | None:
    """
    Zwraca parę indeksów (front, bok) lub None gdy nie da się otworzyć obu kamer naraz.
    """
    available = list_available_cameras(refresh=True)
    if len(available) < 2:
        return None

    suggested_front, suggested_side = suggest_dual_indices(preferred_front, preferred_side)
    candidates: list[tuple[int, int]] = []
    for pair in (
        (preferred_front, preferred_side),
        (preferred_side, preferred_front),
        (suggested_front, suggested_side),
        (suggested_side, suggested_front),
    ):
        if pair[0] != pair[1] and pair not in candidates:
            candidates.append(pair)

    for front in available:
        for side in available:
            if front != side:
                pair = (front, side)
                if pair not in candidates:
                    candidates.append(pair)

    for front, side in candidates:
        if front not in available or side not in available:
            continue
        if validate_dual_pair(front, side):
            return front, side

    return None


def open_dual_cameras(front_index: int, side_index: int, max_retries: int = 3):
    """
    Otwiera parę kamer z retry — Continuity Camera często wymaga 2. próby.
    Zwraca (cam_front, cam_side) lub (None, None).
    """
    for attempt in range(max_retries):
        if attempt > 0:
            print(f"[DUAL-CAM] Ponowna próba otwarcia kamer ({attempt + 1}/{max_retries})...")
            time.sleep(1.0 * attempt)

        cam_front = open_camera_with_warmup(front_index)
        if cam_front is None:
            continue

        time.sleep(0.6)
        cam_side = open_camera_with_warmup(side_index)
        if cam_side is None:
            cam_front.release()
            time.sleep(0.5)
            continue

        if _warmup_reads(cam_front, 3, 0.05) and _warmup_reads(cam_side, 3, 0.05):
            return cam_front, cam_side

        cam_front.release()
        cam_side.release()
        time.sleep(0.5)

    return None, None
