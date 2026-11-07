"""Smart Helmet laptop pipeline: YOLO potholes, MediaPipe signals, rear collision, AR HUD."""
import os
import sys
import threading
import time
from collections import deque

import cv2
import mediapipe as mp
import numpy as np
import requests
from ultralytics import YOLO

PI_IP = os.environ.get("PI_IP", sys.argv[1] if len(sys.argv) > 1 else "192.168.1.50")
FRONT_URL = f"http://{PI_IP}:5000/front"
REAR_URL = f"http://{PI_IP}:5000/rear"
ALARM_URL = f"http://{PI_IP}:5001/play_alarm"
SIGNAL_URL = "http://localhost:8080/set_signal/{}"

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
POTHOLE_CONF = 0.60
ARM_FRAMES = 10
GROWTH_THRESHOLD = 1.30      # >30% area growth
GROWTH_WINDOW = 1.0          # seconds
ALARM_COOLDOWN = 5.0         # seconds
VEHICLE_CLASSES = {2, 5, 7}  # COCO: car, bus, truck
FRAME_SIZE = (640, 480)


class StreamReader(threading.Thread):
    """Continuously grabs the newest frame so processing never lags behind."""

    def __init__(self, url):
        super().__init__(daemon=True)
        self.url, self.frame, self.lock = url, None, threading.Lock()
        self.cap = cv2.VideoCapture(url)

    def run(self):
        while True:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.5)
                self.cap.release()
                self.cap = cv2.VideoCapture(self.url)
                continue
            with self.lock:
                self.frame = frame

    def latest(self):
        with self.lock:
            return None if self.frame is None else self.frame.copy()


def post_async(url):
    def _go():
        try:
            requests.post(url, timeout=2)
        except requests.RequestException:
            pass
    threading.Thread(target=_go, daemon=True).start()


def main():
    pothole_model = YOLO(os.path.join(MODEL_DIR, "pothole.pt"))
    base_path = os.path.join(MODEL_DIR, "yolov8n.pt")
    car_model = YOLO(base_path if os.path.exists(base_path) else "yolov8n.pt")
    pose = mp.solutions.pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    PL = mp.solutions.pose.PoseLandmark

    front, rear = StreamReader(FRONT_URL), StreamReader(REAR_URL)
    front.start()
    rear.start()

    signal_state, sent_state = "off", "off"
    left_cnt = right_cnt = 0
    area_hist = deque(maxlen=10)  # (timestamp, area)
    last_alarm = 0.0
    alarm_until = 0.0

    while True:
        f, r = front.latest(), rear.latest()
        f = np.zeros((FRAME_SIZE[1], FRAME_SIZE[0], 3), np.uint8) if f is None else cv2.resize(f, FRAME_SIZE)
        r = np.zeros((FRAME_SIZE[1], FRAME_SIZE[0], 3), np.uint8) if r is None else cv2.resize(r, FRAME_SIZE)
        if f.ndim == 2:
            f = cv2.cvtColor(f, cv2.COLOR_GRAY2BGR)

        # Model 1: potholes
        for box in pothole_model(f, verbose=False)[0].boxes:
            conf = float(box.conf[0])
            if conf > POTHOLE_CONF:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(f, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(f, f"Pothole {conf:.0%}", (x1, max(y1 - 6, 12)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # Model 2: pose -> turn signal
        res = pose.process(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        if res.pose_landmarks:
            lm = res.pose_landmarks.landmark
            w = f.shape[1]
            lw, ls = lm[PL.LEFT_WRIST], lm[PL.LEFT_SHOULDER]
            rw, rs = lm[PL.RIGHT_WRIST], lm[PL.RIGHT_SHOULDER]
            margin = 0.15
            # Image x grows rightward; subject's left arm appears on image right
            # when facing the camera, so extension direction is judged in image space.
            # Wrist near shoulder height and far to the side counts as extended.
            left_out = abs(lw.x - ls.x) > margin and abs(lw.y - ls.y) < 0.15
            right_out = abs(rw.x - rs.x) > margin and abs(rw.y - rs.y) < 0.15
            left_cnt = left_cnt + 1 if left_out and not right_out else 0
            right_cnt = right_cnt + 1 if right_out and not left_out else 0
            mp.solutions.drawing_utils.draw_landmarks(f, res.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
        else:
            left_cnt = right_cnt = 0

        if left_cnt > ARM_FRAMES:
            signal_state = "left"
        elif right_cnt > ARM_FRAMES:
            signal_state = "right"
        elif left_cnt == 0 and right_cnt == 0:
            signal_state = "off"
        if signal_state != sent_state:
            post_async(SIGNAL_URL.format(signal_state))
            sent_state = signal_state

        # Model 3: rear collision
        now = time.time()
        best = 0
        for box in car_model(r, verbose=False)[0].boxes:
            if int(box.cls[0]) in VEHICLE_CLASSES:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(r, (x1, y1), (x2, y2), (0, 255, 0), 2)
                best = max(best, (x2 - x1) * (y2 - y1))
        if best:
            area_hist.append((now, best))
        else:
            area_hist.clear()
        recent = [(t, a) for t, a in area_hist if now - t <= GROWTH_WINDOW]
        if len(recent) >= 2 and recent[0][1] > 0:
            growth = recent[-1][1] / recent[0][1]
            if growth > GROWTH_THRESHOLD and now - last_alarm > ALARM_COOLDOWN:
                post_async(ALARM_URL)
                last_alarm = now
                alarm_until = now + 3.0

        # AR dashboard
        alarm_on = now < alarm_until
        combined = np.hstack((f, r))
        cv2.putText(combined, f"[TURN SIGNAL: {signal_state.upper()}]", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        cv2.putText(combined, "[REAR ALARM: ACTIVE]" if alarm_on else "[REAR ALARM: OFF]",
                    (FRAME_SIZE[0] + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 0, 255) if alarm_on else (0, 255, 0), 2)
        cv2.imshow("Smart Helmet AR Dashboard", combined)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
