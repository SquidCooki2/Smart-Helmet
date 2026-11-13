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

import config as cfg
from logic import area_growth, arm_extended, next_signal, should_alarm, update_arm_counts

PI_IP = os.environ.get("PI_IP") or (sys.argv[1] if len(sys.argv) > 1 else cfg.PI_IP)
FRONT_URL = f"http://{PI_IP}:{cfg.PI_CAMERA_PORT}/front"
REAR_URL = f"http://{PI_IP}:{cfg.PI_CAMERA_PORT}/rear"
ALARM_URL = f"http://{PI_IP}:{cfg.PI_AUDIO_PORT}/play_alarm"
SIGNAL_URL = f"http://localhost:{cfg.DISPLAY_PORT}/set_signal/{{}}"
FRAME_SIZE = cfg.FRAME_SIZE


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


def blank():
    return np.zeros((FRAME_SIZE[1], FRAME_SIZE[0], 3), np.uint8)


def main():
    pothole_path = os.path.join(cfg.MODEL_DIR, "pothole.pt")
    if not os.path.exists(pothole_path):
        sys.exit(f"Missing {pothole_path}. Run: python download_models.py")
    pothole_model = YOLO(pothole_path)
    base_path = os.path.join(cfg.MODEL_DIR, "yolov8n.pt")
    car_model = YOLO(base_path if os.path.exists(base_path) else "yolov8n.pt")
    pose = mp.solutions.pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    PL = mp.solutions.pose.PoseLandmark
    kw = {"verbose": False}
    if cfg.YOLO_DEVICE:
        kw["device"] = cfg.YOLO_DEVICE

    front, rear = StreamReader(FRONT_URL), StreamReader(REAR_URL)
    front.start()
    rear.start()

    signal_state, sent_state = "off", "off"
    left_cnt = right_cnt = 0
    area_hist = deque(maxlen=10)  # (timestamp, area)
    last_alarm = 0.0
    alarm_until = 0.0
    frame_no = 0
    pothole_boxes = []  # cached detections between inference frames

    while True:
        f, r = front.latest(), rear.latest()
        f = blank() if f is None else cv2.resize(f, FRAME_SIZE)
        r = blank() if r is None else cv2.resize(r, FRAME_SIZE)
        if f.ndim == 2:
            f = cv2.cvtColor(f, cv2.COLOR_GRAY2BGR)
        if r.ndim == 2:
            r = cv2.cvtColor(r, cv2.COLOR_GRAY2BGR)
        frame_no += 1

        # Model 1: potholes (front), run every N frames to cut latency
        if frame_no % cfg.POTHOLE_EVERY_N == 0:
            pothole_boxes = [
                (tuple(map(int, b.xyxy[0])), float(b.conf[0]))
                for b in pothole_model(f, **kw)[0].boxes if float(b.conf[0]) > cfg.POTHOLE_CONF
            ]
        for (x1, y1, x2, y2), conf in pothole_boxes:
            cv2.rectangle(f, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(f, f"Pothole {conf:.0%}", (x1, max(y1 - 6, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # Model 2: pose -> turn signal
        res = pose.process(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        if res.pose_landmarks:
            lm = res.pose_landmarks.landmark
            pt = lambda p: (lm[p].x, lm[p].y)
            left_out = arm_extended(pt(PL.LEFT_WRIST), pt(PL.LEFT_SHOULDER), cfg.ARM_MARGIN, cfg.ARM_HEIGHT_TOL)
            right_out = arm_extended(pt(PL.RIGHT_WRIST), pt(PL.RIGHT_SHOULDER), cfg.ARM_MARGIN, cfg.ARM_HEIGHT_TOL)
            left_cnt, right_cnt = update_arm_counts(left_cnt, right_cnt, left_out, right_out)
            mp.solutions.drawing_utils.draw_landmarks(f, res.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
        else:
            left_cnt = right_cnt = 0

        signal_state = next_signal(signal_state, left_cnt, right_cnt, cfg.ARM_FRAMES)
        if signal_state != sent_state:
            post_async(SIGNAL_URL.format(signal_state))
            sent_state = signal_state

        # Model 3: rear collision
        now = time.time()
        best = 0
        for box in car_model(r, **kw)[0].boxes:
            if int(box.cls[0]) in cfg.VEHICLE_CLASSES:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(r, (x1, y1), (x2, y2), (0, 255, 0), 2)
                best = max(best, (x2 - x1) * (y2 - y1))
        if best:
            area_hist.append((now, best))
        else:
            area_hist.clear()
        growth = area_growth(area_hist, now, cfg.GROWTH_WINDOW)
        if should_alarm(growth, now, last_alarm, cfg.GROWTH_THRESHOLD, cfg.ALARM_COOLDOWN):
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
