"""Streams dual Pi cameras as grayscale MJPEG on port 5000 (/front, /rear)."""
import threading
import time

import cv2
from flask import Flask, Response
from picamera2 import Picamera2

WIDTH, HEIGHT, FPS = 640, 480, 30

app = Flask(__name__)
latest = {"front": None, "rear": None}  # latest JPEG bytes per camera


def capture_loop(name, cam_index):
    cam = Picamera2(cam_index)
    config = cam.create_video_configuration(
        main={"size": (WIDTH, HEIGHT), "format": "RGB888"},
        controls={"FrameRate": FPS},
    )
    cam.configure(config)
    cam.start()
    while True:
        frame = cam.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # NoIR -> grayscale
        ok, jpg = cv2.imencode(".jpg", gray, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if ok:
            latest[name] = jpg.tobytes()


def mjpeg(name):
    while True:
        data = latest[name]
        if data is None:
            time.sleep(0.05)
            continue
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + data + b"\r\n"
        time.sleep(1.0 / FPS)


@app.route("/front")
def front():
    return Response(mjpeg("front"), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/rear")
def rear():
    return Response(mjpeg("rear"), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    for n, i in (("front", 0), ("rear", 1)):
        threading.Thread(target=capture_loop, args=(n, i), daemon=True).start()
    app.run(host="0.0.0.0", port=5000, threaded=True)
