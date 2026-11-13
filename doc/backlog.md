# Smart Helmet Backlog

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done. Priority: P0 (blocker) → P2 (nice to have).
Add new items per [CONTRIBUTING_AGENTS.md](CONTRIBUTING_AGENTS.md).

## Done
- [x] Pi camera streamer (`pi_edge/camera_streamer.py`)
- [x] Pi audio server (`pi_edge/audio_server.py`)
- [x] Phone display server + UI (`laptop_vision/web_display/`)
- [x] Laptop pipeline (`laptop_vision/main_pipeline.py`)
- [x] `requirements.txt`, alarm generator script (`pi_edge/make_alarm.py`)
- [x] T-001 Python 3.12 installed; `pi_edge/alarm.wav` generated
- [~] T-002 Pothole weights: `laptop_vision/download_models.py` targets gated repo [cazzz307/Pothole-Finetuned-YoloV8](https://huggingface.co/cazzz307/Pothole-Finetuned-YoloV8); download blocked until access is granted (see T-002b)
- [x] T-008 Socket.IO client bundled locally (`web_display/static/`); T-009 partial: added screen wake lock to phone page
- [x] T-010 Top-level `README.md`
- [x] T-011 systemd units in `pi_edge/systemd/`
- [x] T-012 Logic refactored into `laptop_vision/logic.py`; 5 unit tests in `tests/` pass
- [x] T-013 Settings moved to `laptop_vision/config.py`
- [x] T-014 (partial) pothole model runs every N frames (`POTHOLE_EVERY_N`); GPU via `YOLO_DEVICE` env var

## Backlog

| ID | Pri | Status | Task | Owner |
|----|-----|--------|------|-------|
| T-003 | P0 | [~] | Deps installed in `.venv`, `main_pipeline` imports, `yolov8n.pt` loads, `mp.solutions` OK (mediapipe pinned to 0.10.21). Remaining: full run needs `pothole.pt` + live Pi streams | agent |
| T-002b | P0 | [ ] | `pothole.pt` download blocked: HF repo `cazzz307/Pothole-Finetuned-YoloV8` is gated. Owner must request access, log in (`HF_TOKEN`), run `laptop_vision/download_models.py` | user |
| T-004 | P0 | [ ] | Test on real Pi 5: both cameras stream at `/front` and `/rear`; confirm camera indices 0/1 (needs hardware) | unassigned |
| T-005 | P1 | [ ] | Verify Bluetooth speaker pairing and `aplay` output on the Pi (needs hardware) | unassigned |
| T-006 | P1 | [ ] | Tune arm-extension thresholds (`config.py`) with real footage; check left/right mirroring | unassigned |
| T-007 | P1 | [ ] | Tune rear collision growth threshold/window with real vehicle footage | unassigned |
| T-009 | P1 | [ ] | Test phone display end to end on a real phone (fullscreen, wake lock, reconnect) | unassigned |
| T-015 | P2 | [ ] | Install systemd units on the Pi (`pi_edge/systemd/`) and verify autostart | unassigned |

## Notes / Known limitations
- Hardware-dependent items cannot be done without the Pi, cameras, speaker and phone.
