# Running the Smart Helmet System

Three devices on one Wi-Fi network (e.g. a phone hotspot): **Raspberry Pi 5**, **Laptop**, **Smartphone**.
Ports: Pi camera `5000`, Pi audio `5001`, Laptop phone-display `8080`.

## 0. One-time setup

### Network
1. Start the hotspot and connect the Pi and laptop to it (the display phone can be the hotspot host or a client).
2. Find the IPs:
   - Pi: `hostname -I`
   - Laptop (PowerShell): `ipconfig` (IPv4 address)
3. Allow inbound TCP 8080 through Windows Firewall on the laptop (accept the prompt on first run, or allow it manually) so the phone can reach it.

### Pi (Raspberry Pi OS Bookworm)
```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-opencv python3-flask alsa-utils
```
- Both Camera Module 2 NoIR cameras must be connected and detected: `rpicam-hello --list-cameras`.
- Pair the Bluetooth speaker and set it as default output (`bluetoothctl`: `scan on`, `pair`, `trust`, `connect <MAC>`). Test: `aplay pi_edge/alarm.wav`.
- Copy the `pi_edge/` folder to the Pi. If `alarm.wav` is missing, run `python3 make_alarm.py` in that folder.

### Laptop (Windows)
```powershell
cd Smart-Helmet
python -m venv .venv
.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r laptop_vision\requirements.txt
```
- Place pothole weights at `laptop_vision/models/pothole.pt` (required; see `models/README.md`).
- `yolov8n.pt` downloads automatically on first run if absent.
- Use a Python version supported by mediapipe/torch (3.12 is fine).

## 1. Start order

### Step 1: Pi camera streamer (Pi, terminal 1)
```bash
cd pi_edge
python3 camera_streamer.py
```
Check from the laptop browser: `http://<PI_IP>:5000/front` and `http://<PI_IP>:5000/rear` show grayscale video.

### Step 2: Pi audio server (Pi, terminal 2)
```bash
cd pi_edge
python3 audio_server.py
```
Test from the laptop:
```powershell
curl.exe -X POST http://<PI_IP>:5001/play_alarm
```
You should hear the alarm on the Bluetooth speaker.

### Step 3: Phone display server (Laptop, terminal 1)
```powershell
cd laptop_vision\web_display
python app.py
```
On the smartphone browser open `http://<LAPTOP_IP>:8080`, tap once for fullscreen. Test the signal:
```powershell
curl.exe -X POST http://localhost:8080/set_signal/left
curl.exe -X POST http://localhost:8080/set_signal/right
curl.exe -X POST http://localhost:8080/set_signal/off
```
The phone should flash an amber arrow, then go black on `off`.
Note: the page loads the Socket.IO client from a CDN, so the phone needs internet access (backlog T-008).

### Step 4: Main pipeline (Laptop, terminal 2)
```powershell
cd laptop_vision
python main_pipeline.py <PI_IP>
# or: $env:PI_IP="<PI_IP>"; python main_pipeline.py
```
An "Smart Helmet AR Dashboard" window opens: front cam (left) and rear cam (right) with a HUD. Press `q` to quit.

## 2. Verifying features
| Feature | How to test | Expected |
|---|---|---|
| Pothole | Show a pothole image/video to the front camera | Red box when confidence > 60% |
| Turn signal | Extend one arm sideways at shoulder height for ~10+ frames | HUD `[TURN SIGNAL: LEFT/RIGHT]`, phone flashes arrow; lowering arms sets `OFF` |
| Rear alarm | Move a toy car/vehicle image rapidly toward the rear camera (>30% area growth in 1 s) | HUD `[REAR ALARM: ACTIVE]`, Pi plays sound; 5 s cooldown |

## 3. Troubleshooting
- **Black/empty panel in dashboard:** the stream isn't reachable. Open the stream URL in a browser; check the Pi IP and that both devices are on the same network.
- **`pothole.pt` not found:** add the weights file (see above).
- **Phone shows nothing:** check the laptop IP, firewall on port 8080, and phone internet (CDN script).
- **No sound:** verify the Bluetooth speaker is connected and default (`aplay alarm.wav` directly on the Pi).
- **Camera errors on the Pi:** run `rpicam-hello --list-cameras`; the streamer uses camera indices 0 (front) and 1 (rear). Swap them in `camera_streamer.py` if reversed.
- **Left/right mirrored:** adjust the logic in `main_pipeline.py` (backlog T-006).
- **Lag:** lower resolution, or run YOLO on a GPU (backlog T-014).

## 4. Shutdown
Press `q` in the dashboard window, then `Ctrl+C` in each server terminal.

> The system has not yet been tested end to end on hardware (see [backlog.md](backlog.md)).
