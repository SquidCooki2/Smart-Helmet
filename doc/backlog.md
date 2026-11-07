# Smart Helmet Backlog

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done. Priority: P0 (blocker) → P2 (nice to have).
Add new items per [CONTRIBUTING_AGENTS.md](CONTRIBUTING_AGENTS.md).

## Done
- [x] Pi camera streamer (`pi_edge/camera_streamer.py`)
- [x] Pi audio server (`pi_edge/audio_server.py`)
- [x] Phone display server + UI (`laptop_vision/web_display/`)
- [x] Laptop pipeline (`laptop_vision/main_pipeline.py`)
- [x] `requirements.txt`, alarm generator script (`pi_edge/make_alarm.py`)

## Backlog

| ID | Pri | Status | Task | Owner |
|----|-----|--------|------|-------|
| T-001 | P0 | [ ] | Install Python on dev laptop and generate `pi_edge/alarm.wav` via `make_alarm.py` | unassigned |
| T-002 | P0 | [ ] | Obtain/train pothole weights and place at `laptop_vision/models/pothole.pt` | unassigned |
| T-003 | P0 | [ ] | Install deps (`pip install -r laptop_vision/requirements.txt`) and smoke-test the pipeline | unassigned |
| T-004 | P0 | [ ] | Test on real Pi 5: both cameras stream at `/front` and `/rear`; confirm camera indices 0/1 | unassigned |
| T-005 | P1 | [ ] | Verify Bluetooth speaker pairing and `aplay` output on the Pi | unassigned |
| T-006 | P1 | [ ] | Tune arm-extension thresholds (margin, wrist/shoulder height) with real footage; check left/right mirroring | unassigned |
| T-007 | P1 | [ ] | Tune rear collision growth threshold/window with real vehicle footage | unassigned |
| T-008 | P1 | [ ] | Bundle Socket.IO client locally (currently loaded from CDN; hotspot may lack internet) | unassigned |
| T-009 | P1 | [ ] | Test phone display end to end (fullscreen, screen wake lock, reconnect) | unassigned |
| T-010 | P2 | [ ] | Add a top-level `README.md` with setup and run instructions | unassigned |
| T-011 | P2 | [ ] | Add systemd units to autostart Pi services | unassigned |
| T-012 | P2 | [ ] | Add unit tests for the collision-growth and arm-detection logic (refactor into functions) | unassigned |
| T-013 | P2 | [ ] | Move configuration (IPs, thresholds) to a config file | unassigned |
| T-014 | P2 | [ ] | Run YOLO on GPU / reduce inference frequency for lower latency | unassigned |

## Notes / Known limitations
- `pothole.pt` is not in the repo.
- Code is untested; Python was not available when written.
