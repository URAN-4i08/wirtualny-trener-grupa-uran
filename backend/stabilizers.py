from mediapipe.framework.formats import landmark_pb2

from backend.config import (
    LIVE_MESSAGE_STABLE_FRAMES,
    LIVE_POSE_HOLD_FRAMES,
    LIVE_POSE_SMOOTH_ALPHA,
)


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
live_posture_debouncer = MessageDebouncer(stable_frames=LIVE_MESSAGE_STABLE_FRAMES)
live_contact_debouncer = MessageDebouncer(stable_frames=max(3, LIVE_MESSAGE_STABLE_FRAMES // 2))
