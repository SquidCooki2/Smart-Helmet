# Smart Helmet CV System

A computer-vision smart helmet for cyclists: a Raspberry Pi 5 streams two cameras, a laptop runs YOLOv8 + MediaPipe, and a phone on the back of the helmet shows turn signals.

| Node | Role | Code |
|---|---|---|
| Raspberry Pi 5 | MJPEG camera streams (:5000), alarm audio (:5001) | [pi_edge/](pi_edge) |
| Laptop | Vision pipeline, AR dashboard, phone display server (:8080) | [laptop_vision/](laptop_vision) |
| Smartphone | Full-screen amber turn-signal page | browser → `http://<LAPTOP_IP>:8080` |

## Quick start
```powershell
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r laptop_vision\requirements.txt
python laptop_vision\download_models.py      # pothole + base YOLO weights
python -m unittest discover tests            # logic tests
```
Then follow [doc/RUNNING.md](doc/RUNNING.md) for the full multi-device run order.

## Docs
- [Specification](doc/master_repository_specification.md)
- [Running everything](doc/RUNNING.md)
- [Backlog](doc/backlog.md) · [Contributing (agents)](doc/CONTRIBUTING_AGENTS.md)

Settings (IPs, thresholds) live in [laptop_vision/config.py](laptop_vision/config.py).
