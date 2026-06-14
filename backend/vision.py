import threading

import cv2
import mediapipe as mp
import numpy as np
import time

from backend.config import (
    LIVE_BALL_CONF,
    LIVE_BALL_HOLD_FRAMES,
    LIVE_BALL_IMGSZ,
    LIVE_BALL_USE_YOLO,
    LIVE_CONTACT_HOLD_FRAMES,
    LIVE_NO_POSE_GRACE_FRAMES,
    yolo_model,
)
from backend.stabilizers import MessageDebouncer, PoseLandmarkStabilizer
from logic.coach_engine import VolleyballPostureEvaluator, calculate_angle, check_volleyball_position
from logic.biomechanics import KOMUNIKAT_BRAK_NOG, nogi_widoczne

mp_pose = mp.solutions.pose
pose_tracker = None


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


def _detect_ball_yolo(frame, body_points=None):
    """YOLO COCO sports ball — działa słabo na siatkówce, używane jako pierwszy sygnał."""
    results_yolo = yolo_model(frame, conf=LIVE_BALL_CONF, imgsz=LIVE_BALL_IMGSZ, verbose=False)
    h, w = frame.shape[:2]
    frame_area = h * w
    min_area = max(40, int(frame_area * 0.00003))
    candidates = []

    for result in results_yolo:
        for box in result.boxes:
            cls = int(box.cls[0])
            if result.names[cls] != "sports ball":
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            area = (x2 - x1) * (y2 - y1)
            if area <= min_area:
                continue

            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            conf = float(box.conf[0]) if hasattr(box, "conf") else 0.5
            candidates.append((cx, cy, conf, x1, y1, x2, y2, "yolo"))

    zone = _ball_search_zone(body_points, frame.shape[0], frame.shape[1]) if body_points else None
    return _pick_best_ball_candidate(candidates, frame, body_points, zone=zone)


def _ball_search_zone(body_points, h, w):
    """
    Strefa poszukiwania piłki wokół platformy dłoni.

    W odbijaniu piłka leci wysoko w górę między kontaktami, więc strefa jest
    ELIPSĄ wyraźnie wydłużoną ku górze (nad dłonie), a nie ciasnym okręgiem.
    Dzięki temu piłkę śledzimy przez cały łuk lotu, a nie tracimy jej w szczycie.

    Zwraca: (cx, cy, rx, ry) — środek elipsy + półosie pozioma/pionowa.
    Poza strefą ignorujemy detekcje (lampy, meble w tle).
    """
    try:
        lw = body_points["lewy_nadgarstek"]
        rw = body_points["prawy_nadgarstek"]
        ls = body_points["lewe_ramie"]
        rs = body_points["prawe_ramie"]
    except KeyError:
        return None

    wrist_cx = int((lw.x + rw.x) / 2 * w)
    wrist_cy = int((lw.y + rw.y) / 2 * h)
    shoulder_w = max(0.12 * w, abs(ls.x - rs.x) * w)

    # Strefa umiarkowana: obejmuje dłonie i trochę nad nimi, ale NIE całe tło nad głową
    # (zbyt duża strefa łapała lampy/meble). Liczenie odbić i tak dzieje się w DNIE łuku
    # przy dłoniach, więc nie potrzebujemy sięgać aż do szczytu lotu piłki.
    rx = max(105, int(shoulder_w * 1.35))   # szerokość — dłonie + margines
    ry = max(155, int(shoulder_w * 2.3))    # wysokość — nad dłonie (łuk piłki)
    cy = int(wrist_cy - ry * 0.32)
    return wrist_cx, cy, rx, ry


def _in_ball_search_zone(cx, cy, zone, h, w):
    if zone is None:
        return False
    zcx, zcy, rx, ry = zone
    nx = (cx - zcx) / max(1, rx)
    ny = (cy - zcy) / max(1, ry)
    return (nx * nx + ny * ny) <= 1.0


def _detect_ball_color(frame, body_points=None):
    """
    Detekcja HSV — żółte/niebieskie panele siatkówki.
    Bez sylwetki nie szukamy (unikamy lamp i mebli w tle).
    """
    if not body_points:
        return []

    h, w = frame.shape[:2]
    zone = _ball_search_zone(body_points, h, w)
    if zone is None:
        return []

    zcx, zcy, rx, ry = zone
    pad_x = int(rx * 1.2)
    pad_y = int(ry * 1.1)
    x1 = max(0, zcx - pad_x)
    y1 = max(0, zcy - pad_y)
    x2 = min(w, zcx + pad_x)
    y2 = min(h, zcy + pad_y)
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return []

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    masks = [
        cv2.inRange(hsv, (17, 70, 70), (35, 255, 255)),    # żółty
        cv2.inRange(hsv, (95, 55, 55), (130, 255, 255)),   # niebieski
    ]
    mask = masks[0]
    for channel_mask in masks[1:]:
        mask = cv2.bitwise_or(mask, channel_mask)

    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    roi_area = (x2 - x1) * (y2 - y1)
    min_area = max(28, int(roi_area * 0.0006))
    max_area = int(roi_area * 0.10)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue
        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            continue
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        if circularity < 0.32:  # dość okrągły — odrzuca tło, ale nie gubi piłki w ruchu
            continue
        moments = cv2.moments(contour)
        if moments["m00"] == 0:
            continue
        cx = int(moments["m10"] / moments["m00"]) + x1
        cy = int(moments["m01"] / moments["m00"]) + y1
        bx, by, bw, bh = cv2.boundingRect(contour)
        candidates.append((cx, cy, circularity, bx + x1, by + y1, bx + x1 + bw, by + y1 + bh, "color"))

    return _pick_best_ball_candidate(candidates, frame, body_points, conf_key=2, zone=zone)


def _pick_best_ball_candidate(candidates, frame, body_points=None, conf_key=2, zone=None):
    if not candidates or not body_points:
        return []

    h, w = frame.shape[:2]
    if zone is None:
        zone = _ball_search_zone(body_points, h, w)
    if zone is None:
        return []

    # Dopuszczalna odległość od nadgarstka = wysokość strefy (piłka leci wysoko w górę).
    max_dist = max(80, int(max(zone[2], zone[3]) * 1.05))

    scored = []
    for item in candidates:
        cx, cy = item[0], item[1]
        if not _in_ball_search_zone(cx, cy, zone, h, w):
            continue
        score_val = item[conf_key]
        dist = _nearest_wrist_distance_px((cx, cy), body_points, (h, w))
        if dist is None:
            continue
        if dist > max_dist:
            continue
        proximity = 1.0 - min(1.0, dist / max_dist)
        score = score_val * 0.2 + proximity * 0.8
        scored.append((score, item))

    # Brak kandydata blisko dłoni → NIE zgadujemy (to właśnie powodowało
    # „wyrywanie" przypadkowych obiektów z tła i miganie ramki).
    if not scored:
        return []

    scored.sort(key=lambda entry: entry[0], reverse=True)
    item = scored[0][1]
    cx, cy = item[0], item[1]
    _draw_ball_bbox(frame, cx, cy, item[3], item[4], item[5], item[6], item[7])
    return [(cx, cy)]


def find_ball_positions(frame, body_points=None):
    """Detekcja koloru w strefie dłoni; YOLO jako zapas gdy kolor nie złapie."""
    if not body_points:
        return []
    detected = _detect_ball_color(frame, body_points)
    if detected:
        return detected
    return _detect_ball_yolo(frame, body_points)


def _nearest_wrist_distance_px(ball_center, body_points, frame_shape):
    h, w = frame_shape
    cx, cy = ball_center
    distances = []
    for side in ("lewy_nadgarstek", "prawy_nadgarstek"):
        lm = body_points.get(side)
        if lm is None:
            continue
        wx, wy = int(lm.x * w), int(lm.y * h)
        distances.append(((cx - wx) ** 2 + (cy - wy) ** 2) ** 0.5)
    return min(distances) if distances else None


def _draw_ball_bbox(frame, cx, cy, x1, y1, x2, y2, source="yolo"):
    color = (255, 255, 255) if source == "yolo" else (0, 220, 255)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    cv2.circle(frame, (cx, cy), 5, color, -1)


class BallTracker:
    """Utrzymuje pozycję piłki między klatkami bez inferencji YOLO."""

    def __init__(self, hold_frames=LIVE_BALL_HOLD_FRAMES):
        self.hold_frames = hold_frames
        self.hold_remaining = 0
        self.positions = []

    def update(self, frame, body_points=None, run_inference=True):
        h, w = frame.shape[:2]

        if run_inference:
            detected = find_ball_positions(frame, body_points=body_points) if body_points else []
            if detected:
                self.positions = detected
                self.hold_remaining = self.hold_frames
            elif self.hold_remaining > 0:
                self.hold_remaining -= 1
            else:
                self.positions = []
        elif self.hold_remaining > 0:
            self.hold_remaining -= 1
        else:
            self.positions = []

        if self.positions and body_points:
            zone = _ball_search_zone(body_points, h, w)
            if zone and not _in_ball_search_zone(self.positions[0][0], self.positions[0][1], zone, h, w):
                self.positions = []
                self.hold_remaining = 0

        if self.positions and not run_inference:
            for cx, cy in self.positions:
                cv2.circle(frame, (cx, cy), 7, (180, 180, 180), 2)

        return list(self.positions)

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


def platform_center_pixel(frame, body_points):
    lw = body_points["lewy_nadgarstek"]
    rw = body_points["prawy_nadgarstek"]
    w, h = frame.shape[1], frame.shape[0]
    return int((lw.x + rw.x) / 2 * w), int((lw.y + rw.y) / 2 * h)


def ball_contact_distance(frame, body_points, ball_positions):
    """Odległość piłki od strefy odbicia — min(przedramiona, środek platformy dłoni)."""
    if not body_points or not ball_positions:
        return None, None

    forearm_ball, forearm_dist = nearest_ball_to_forearms(frame, body_points, ball_positions)
    px, py = platform_center_pixel(frame, body_points)

    nearest_ball = forearm_ball
    nearest_distance = forearm_dist

    for ball_center in ball_positions:
        platform_dist = ((ball_center[0] - px) ** 2 + (ball_center[1] - py) ** 2) ** 0.5
        if nearest_distance is None or platform_dist < nearest_distance:
            nearest_distance = platform_dist
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
    ball_center, distance = ball_contact_distance(frame, body_points, ball_positions)
    if ball_center is None or distance is None:
        return False

    threshold = max(110, min(frame.shape[:2]) * 0.38)
    is_close = distance <= threshold
    draw_forearm_contact(frame, body_points, ball_center, is_close)
    return is_close


class BallContactTracker:
    def __init__(self, cooldown_frames=14):
        self.cooldown_frames = cooldown_frames
        # Cooldown dłuższy niż połowa cyklu odbicia → jedno fizyczne odbicie nie
        # jest liczone dwa razy (przez próg odległości ORAZ dno trajektorii).
        self.cooldown_sec = max(0.35, cooldown_frames / 25.0)
        self.contact_count = 0
        self.last_contact_at = 0.0
        self.was_in_contact = False
        self.last_ball_center = None
        self.contact_hold_remaining = 0
        self.new_contact_this_frame = False
        self._latched_edges = 0
        self._edge_lock = threading.Lock()
        self._state_lock = threading.Lock()
        # ── Śledzenie trajektorii pionowej piłki (detekcja dna odbicia) ──
        self._last_y = None
        self._going_down = False
        self._descent_start_y = None
        self._min_dist_in_phase = float("inf")

    def latch_contact_edge(self):
        """Dual-Cam: zachowaj zbocze kontaktu mimo gubienia klatek w kolejce."""
        with self._edge_lock:
            if self.new_contact_this_frame:
                self._latched_edges += 1

    def take_latched_edge(self) -> bool:
        """
        Zwraca True dokładnie raz na każde zarejestrowane zbocze kontaktu.

        Latch jest jedynym źródłem prawdy dla Dual-Cam — każdy kontakt zwiększa
        licznik o 1 (niezależnie od gubienia klatek w kolejce), a tu konsumujemy
        po jednym. BEZ fallbacku na new_contact_this_frame, bo ta flaga pozostaje
        True do następnej klatki i powodowała podwójne liczenie.
        """
        with self._edge_lock:
            if self._latched_edges > 0:
                self._latched_edges -= 1
                return True
            return False

    def _contact_threshold(self, frame):
        return max(110, min(frame.shape[:2]) * 0.38)

    def _register_contact(self):
        if self.new_contact_this_frame:
            return
        self.contact_count += 1
        self.last_contact_at = time.time()
        self.contact_hold_remaining = LIVE_CONTACT_HOLD_FRAMES
        self.new_contact_this_frame = True

    def _try_register_edge(self, distance_px, threshold):
        with self._state_lock:
            if distance_px is None:
                self.was_in_contact = False
                return False

            is_near = distance_px <= threshold
            enough_cooldown = time.time() - self.last_contact_at >= self.cooldown_sec
            if is_near and not self.was_in_contact and enough_cooldown:
                self._register_contact()

            self.was_in_contact = is_near
            return is_near

    def _note_trajectory(self, ball_center, distance_px, threshold):
        """
        Liczy odbicie w DNIE łuku piłki: gdy piłka przestaje opadać i zaczyna
        lecieć w górę, a w najniższym punkcie była blisko platformy dłoni.

        To znacznie pewniejsze niż sam próg odległości — wychwytuje sam moment
        uderzenia, nawet gdy piłka tylko na chwilę zbliży się do rąk.
        Wywoływane już pod self._state_lock.
        """
        move_eps = 2.0  # px — ignoruj drgania detekcji
        min_drop = max(18.0, threshold * 0.25)  # min. spadek przed dnem
        y = float(ball_center[1])

        if self._last_y is None:
            self._last_y = y
            self._descent_start_y = y
            self._min_dist_in_phase = distance_px
            return

        self._min_dist_in_phase = min(self._min_dist_in_phase, distance_px)
        dy = y - self._last_y  # dodatnie = piłka opada (y rośnie w dół)

        if dy > move_eps:
            if not self._going_down:
                self._going_down = True
                self._descent_start_y = self._last_y
                self._min_dist_in_phase = distance_px
        elif dy < -move_eps:
            if self._going_down:
                # Zwrot z opadania na wznoszenie → dno łuku w poprzedniej klatce.
                descent = self._last_y - (self._descent_start_y or self._last_y)
                near_bottom = self._min_dist_in_phase <= threshold
                enough_cooldown = time.time() - self.last_contact_at >= self.cooldown_sec
                if descent >= min_drop and near_bottom and enough_cooldown:
                    self._register_contact()
                self._going_down = False
                self._descent_start_y = self._last_y
                self._min_dist_in_phase = distance_px

        self._last_y = y

    def _reset_trajectory(self):
        self._last_y = None
        self._going_down = False
        self._descent_start_y = None
        self._min_dist_in_phase = float("inf")

    def note_bio_distance(self, distance_px, threshold_px=240):
        """Zapas: dystans piłka↔nadgarstek z analizuj_front."""
        self._try_register_edge(distance_px, threshold_px)

    def update(self, frame, body_points, ball_positions, frame_index):
        with self._state_lock:
            self.new_contact_this_frame = False

            if self.contact_hold_remaining > 0:
                self.contact_hold_remaining -= 1

            if not body_points:
                return self.contact_hold_remaining > 0

            ball_center, distance = ball_contact_distance(frame, body_points, ball_positions or [])
            threshold = self._contact_threshold(frame)

            if ball_center is None or distance is None:
                self.was_in_contact = False
                self.last_ball_center = None
                self._reset_trajectory()
                return self.contact_hold_remaining > 0

            # Dwa niezależne sygnały odbicia (dno trajektorii + próg odległości),
            # zdeduplikowane wspólnym cooldownem w _register_contact.
            self._note_trajectory(ball_center, distance, threshold)
            is_near = self._try_register_edge_unlocked(distance, threshold)
            self.last_ball_center = ball_center
            draw_forearm_contact(frame, body_points, ball_center, is_near)
            return is_near or self.contact_hold_remaining > 0

    def _try_register_edge_unlocked(self, distance_px, threshold):
        """Wewnętrzne — wywoływane już pod _state_lock."""
        if distance_px is None:
            self.was_in_contact = False
            return False

        is_near = distance_px <= threshold
        enough_cooldown = time.time() - self.last_contact_at >= self.cooldown_sec
        if is_near and not self.was_in_contact and enough_cooldown:
            self._register_contact()

        self.was_in_contact = is_near
        return is_near


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
    ball_tracker=None,
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

    if ball_tracker is not None:
        ball_positions = ball_tracker.update(
            frame,
            body_points=body_points or None,
            run_inference=detect_ball,
        )
    else:
        ball_positions = find_ball_positions(frame, body_points=body_points or None) if detect_ball else []

    if body_points and contact_tracker:
        contact_detected = contact_tracker.update(
            frame, body_points, ball_positions or [], frame_index
        )
    elif body_points and ball_positions:
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

    has_legs = nogi_widoczne(body_points) if body_points else False

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
        "hasLegs": has_legs,
        "komunikatNogi": None if has_legs or not body_points else KOMUNIKAT_BRAK_NOG,
        "hasBall": bool(ball_positions),
        "source": source,
        "isAnalyzing": True,
        # Wewnętrzne — używane przez biomechanikę, NIE są wysyłane do GUI
        "_ballCenters": ball_positions,
        "_bodyPoints": body_points,
        "_newContact": bool(contact_tracker and contact_tracker.new_contact_this_frame),
    }

    return frame, metrics
