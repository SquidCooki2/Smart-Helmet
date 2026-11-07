# 🧠 Smart Helmet CV System: Codebase Generation Specification

**Context for AI Agent:** You are generating a complete repository for a hackathon project. This is a Computer Vision "Smart Helmet" for cyclists. The system uses a Raspberry Pi 5 (with two MIPI cameras and a Bluetooth speaker) and a standard smartphone (taped to the back of the helmet as a display screen), all communicating with a Laptop over a local Wi-Fi hotspot. 

Please use this document to generate the necessary Python, HTML, and JS files.

## 1. System Architecture & Network Flow

*   **Network:** All devices (Pi, Laptop, Smartphone) are connected to a single local Wi-Fi network (e.g., a phone hotspot). 
*   **Node A (Raspberry Pi 5):** 
    *   Hardware: 2x Pi Camera Module 2 (NoIR), 1x Bluetooth Speaker.
    *   Role: Streams dual camera feeds (MJPEG) and listens for HTTP requests to play a warning sound.
*   **Node B (The Laptop):**
    *   Role: The central brain. Pulls the MJPEG streams, runs YOLOv8 and MediaPipe processing, overlays the AR dashboard on the screen, and sends trigger commands to the Pi and Smartphone.
*   **Node C (The Smartphone):**
    *   Role: Acts as the left/right turn signal. Points its mobile web browser to a Flask server hosted by the Laptop to display a full-screen, real-time UI (black screen, flashing amber arrows).

---

## 2. Target Repository Structure

```text
/smart-helmet-repo
├── pi_edge/
│   ├── camera_streamer.py    # Streams dual cameras using Picamera2
│   ├── audio_server.py       # Flask API to play collision warning sound
│   └── alarm.wav             # Sound file for rear collision
├── laptop_vision/
│   ├── main_pipeline.py      # Core OpenCV loop, YOLO, MediaPipe
│   ├── models/
│   │   ├── yolov8n.pt        # Base YOLO model for cars
│   │   └── pothole.pt        # Pre-trained YOLO model for potholes
│   ├── web_display/          # The smartphone UI server
│   │   ├── app.py            # Flask-SocketIO server for phone display
│   │   └── templates/
│   │       └── index.html    # Fullscreen JS/CSS turn signal display
│   └── requirements.txt      # Python dependencies
```

---

## 3. Node Specifications (Code Requirements)

### 3.1 `pi_edge/camera_streamer.py`
*   **Library:** Must use `Picamera2` (the required libcamera wrapper for Pi 5 OS Bookworm), OpenCV, and Flask.
*   **Functionality:** Initialize both cameras in low-res/high-FPS mode (e.g., 640x480 @ 30fps) to save bandwidth. Convert the NoIR frames to Grayscale immediately using `cv2.cvtColor`.
*   **Endpoints:** Host two MJPEG streams at `http://<PI_IP>:5000/front` and `http://<PI_IP>:5000/rear`.

### 3.2 `pi_edge/audio_server.py`
*   **Library:** Flask, `pygame` or `subprocess` (using `aplay`).
*   **Functionality:** A simple Flask server running on port 5001.
*   **Endpoints:** 
    *   `POST /play_alarm` -> Triggers the playback of `alarm.wav` over the Pi's default audio output (Bluetooth speaker). Prevent overlapping audio if triggered multiple times rapidly.

### 3.3 `laptop_vision/web_display/app.py` & `index.html`
*   **Library:** Flask, Flask-SocketIO.
*   **Functionality:** Hosts the website that the smartphone will display. 
*   **Frontend (`index.html`):** A responsive, pitch-black screen. Listens for SocketIO events (`signal_left`, `signal_right`, `signal_off`). When triggered, it flashes a massive, screen-filling Amber/Orange HTML/CSS arrow (⬅️ or ➡️) on a loop.
*   **Backend (`app.py`):** Runs on port 8080. Exposes a REST API (`POST /set_signal/<direction>`) that the `main_pipeline.py` can call. When this endpoint is hit, it emits the corresponding SocketIO event to the connected smartphone.

### 3.4 `laptop_vision/main_pipeline.py` (The Core Logic)
This is the main execution file. It must run asynchronous or threaded loops to prevent the video feeds from lagging behind the ML processing.
*   **Video Ingestion:** Use `cv2.VideoCapture` to pull the HTTP MJPEG streams from the Pi.
*   **Model 1 (Potholes - Front Cam):** Run custom YOLOv8 `pothole.pt`. If confidence > 60%, draw a bounding box.
*   **Model 2 (MediaPipe - Front Cam):** Run `mediapipe.solutions.pose`. 
    *   *Logic:* Check the x, y coordinates of `LEFT_WRIST`, `LEFT_SHOULDER`, `RIGHT_WRIST`, `RIGHT_SHOULDER`. 
    *   *Trigger:* If wrist extends significantly past the shoulder horizontally for > 10 consecutive frames, send `POST /set_signal/left` (or right) to the local Web Display server. If arms are down, send `POST /set_signal/off`.
*   **Model 3 (Rear Collision - Rear Cam):** Run base YOLOv8 targeting the `car`, `truck`, `bus` classes. 
    *   *Logic:* Track the area of the bounding box ($width \times height$). Maintain a history of the last 10 frames. Calculate the rate of expansion ($\frac{dA}{dt}$). 
    *   *Trigger:* If the bounding box area increases by > 30% within 1 second, the car is approaching too fast. Send `POST http://<PI_IP>:5001/play_alarm`. Implement a 5-second cooldown to prevent spamming the webhook.
*   **AR Dashboard (Output):** Combine both processed frames horizontally or vertically using `np.hstack`/`vstack`. Draw a custom HUD using `cv2.putText` displaying statuses (e.g., `[TURN SIGNAL: LEFT]`, `[REAR ALARM: ACTIVE]`). Show this combined frame via `cv2.imshow`.

---
**End of Specification.**