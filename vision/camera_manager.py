# camera_manager.py
# Manager do synchronizacji dwóch kamer: 45° i opcjonalnego frontu.

import queue
import threading
import time

import cv2


class DualCameraManager:
    """Manager do równoległego odczytywania i synchronizacji dwóch kamer."""

    def __init__(self, camera_45deg=0, camera_front=1, width=640, height=480, buffer_size=2):
        self.camera_45deg_idx = camera_45deg
        self.camera_front_idx = camera_front
        self.width = width
        self.height = height
        self.buffer_size = buffer_size

        self.frame_queue_45 = queue.Queue(maxsize=buffer_size)
        self.frame_queue_front = queue.Queue(maxsize=buffer_size)
        self.running = False
        self.threads = []

        self.frame_count_45 = 0
        self.frame_count_front = 0
        self.dropped_frames_45 = 0
        self.dropped_frames_front = 0

    def _read_camera(self, cap, frame_queue, camera_key):
        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.001)
                continue

            if self.width and self.height:
                frame = cv2.resize(frame, (self.width, self.height))

            timestamp = time.time()

            try:
                frame_queue.put_nowait((frame, timestamp))
                if camera_key == "45":
                    self.frame_count_45 += 1
                else:
                    self.frame_count_front += 1
            except queue.Full:
                try:
                    frame_queue.get_nowait()
                    frame_queue.put_nowait((frame, timestamp))
                    if camera_key == "45":
                        self.dropped_frames_45 += 1
                    else:
                        self.dropped_frames_front += 1
                except queue.Empty:
                    pass

    def start(self, include_front=True):
        cap_45 = cv2.VideoCapture(self.camera_45deg_idx)
        cap_front = cv2.VideoCapture(self.camera_front_idx) if include_front else None

        if self.width and self.height:
            cap_45.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap_45.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            if cap_front is not None:
                cap_front.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                cap_front.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        if not cap_45.isOpened():
            print(f"BŁĄD: Nie można otworzyć kamery 45° (index={self.camera_45deg_idx})")
            return False

        if include_front and cap_front is not None and not cap_front.isOpened():
            print(f"BŁĄD: Nie można otworzyć kamery frontowej (index={self.camera_front_idx})")
            cap_45.release()
            return False

        self.running = True
        thread_45 = threading.Thread(target=self._read_camera, args=(cap_45, self.frame_queue_45, "45"), daemon=True)
        self.threads = [thread_45]
        thread_45.start()
        self.cap_45 = cap_45

        if include_front and cap_front is not None:
            thread_front = threading.Thread(
                target=self._read_camera,
                args=(cap_front, self.frame_queue_front, "front"),
                daemon=True,
            )
            thread_front.start()
            self.threads.append(thread_front)
            self.cap_front = cap_front

        return True

    def get_synchronized_frames(self, timeout=1.0):
        frame_45 = None
        frame_front = None
        timestamp_45 = None
        timestamp_front = None

        try:
            while True:
                frame_45, timestamp_45 = self.frame_queue_45.get(timeout=timeout)
        except queue.Empty:
            pass

        try:
            while True:
                frame_front, timestamp_front = self.frame_queue_front.get_nowait()
        except queue.Empty:
            pass

        if frame_45 is None:
            return None, None, None

        if frame_front is None:
            return frame_45, None, None

        return frame_45, frame_front, abs(timestamp_45 - timestamp_front)

    def get_stats(self):
        return {
            "frame_count_45": self.frame_count_45,
            "frame_count_front": self.frame_count_front,
            "dropped_frames_45": self.dropped_frames_45,
            "dropped_frames_front": self.dropped_frames_front,
            "queue_size_45": self.frame_queue_45.qsize(),
            "queue_size_front": self.frame_queue_front.qsize(),
        }

    def stop(self):
        self.running = False

        for thread in self.threads:
            thread.join(timeout=2.0)

        if hasattr(self, "cap_45"):
            self.cap_45.release()
        if hasattr(self, "cap_front"):
            self.cap_front.release()

        print("Kamery zamknięte")
