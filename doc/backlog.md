# Smart Helmet Backlog

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done. Priority: P0 (blocker) → P2 (nice to have).
Add new items per [CONTRIBUTING_AGENTS.md](CONTRIBUTING_AGENTS.md).

## Done
- [x] T-001 Phase 1 PoC project scaffolding (`poc/config.py`, `requirements.txt`, `requirements-pi.txt`, `README.md`)
- [x] T-002 Radar watchman module (`poc/radar_watchman.py`) with UART parser, threat thresholds (<50m, >15 mph), and cooldown
- [x] T-003 Camera classifier module (`poc/camera_classifier.py`) with dormant burst capture, latency check (<200ms), and TFLite MobileNet mapping (`Car`, `Truck`, `Motorcycle`, `Unknown`)
- [x] T-004 Crash detector module (`poc/crash_detect.py`) with 6-axis I2C IMU reader, >6G impact + stillness state machine, and `SOS_PROTOCOL` trigger
- [x] T-005 Alert manager (`poc/alert_manager.py`) with Bluetooth TTS collision alerts and 15s cancellable SOS webhook
- [x] T-006 Central `asyncio` orchestrator (`poc/main_controller.py`) with `--mock` simulation mode and 10 passing unit/integration tests (`tests/test_poc.py`)

## Backlog

| ID | Pri | Status | Task | Owner |
|----|-----|--------|------|-------|
| T-007 | P0 | [ ] | Verify raw UART parsing against the physical mmWave radar sensor on Raspberry Pi Zero 2 W (`poc/radar_watchman.py`) | unassigned |
| T-008 | P0 | [ ] | Verify 6-axis I2C IMU (`0x68`) raw reads and G-force calibration on Raspberry Pi Zero 2 W (`poc/crash_detect.py`) | unassigned |
| T-009 | P0 | [ ] | Source/place quantized MobileNet `.tflite` + `labels.txt` in `models/` and benchmark <200ms radar-to-camera trigger latency on Pi Zero 2 W (`poc/camera_classifier.py`) | unassigned |
| T-010 | P1 | [ ] | Configure Bluetooth headset audio sink on Pi OS Lite and verify `espeak` / TTS collision and SOS countdown playback (`poc/alert_manager.py`) | unassigned |
| T-011 | P1 | [ ] | Add passive loop-recording dashcam buffer to local SD card in `poc/camera_classifier.py` per product plan | unassigned |
| T-012 | P1 | [ ] | Conduct controlled parking-lot ride tests to tune `crash_g_threshold`, `radar_max_distance_m`, and `radar_danger_speed_mph` in `poc/config.py` | unassigned |
| T-013 | P2 | [ ] | Add BLE peripheral / companion app stub and handlebar turn-signal RF/ANT+ sync prototype per product plan | unassigned |
| T-014 | P2 | [ ] | Phase 2 ergonomics: 3D-print 100g/130g/160g "Spider" dummy mounts and run helmet balance ride tests | unassigned |

## Notes / Known limitations
- Hardware-dependent items (T-007 through T-010, T-012) cannot be verified without the Raspberry Pi Zero 2 W, CSI camera, mmWave radar, I2C IMU, and Bluetooth headset.
- Current `tests/test_poc.py` and `--mock` mode validate orchestration, state machines, and interfaces using simulated sensor feeds.
