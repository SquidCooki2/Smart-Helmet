# Smart Helmet Backlog

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done. Priority: P0 (blocker) → P2 (nice to have).
Add new items per [CONTRIBUTING_AGENTS.md](CONTRIBUTING_AGENTS.md).

## Done
- [x] T-001 Tethered Edge Compute project scaffolding (`firmware/esp32_smart_helmet/`, `edge_receiver/`, `requirements.txt`, `README.md`)
- [x] T-002 ESP32-S3 dual-core FreeRTOS firmware skeleton (`firmware/esp32_smart_helmet/src/main.cpp`) with Core 0 MJPEG dashcam loop, Core 1 LD2410 radar watchdog, and 512-byte BLE `Image_Transfer` chunking
- [x] T-003 BLE GATT protocol codec (`edge_receiver/ble_protocol.py`) for `Radar_Telemetry` (`DIST:30,SPD:45`), 512-byte JPEG chunking/reassembly, and `Audio_Command` (`PLAY:TRUCK_APPROACHING`)
- [x] T-004 Edge receiver & `--mock` round-trip simulator (`edge_receiver/receiver.py`, `edge_receiver/classifier.py`) with 6 passing unit/integration tests (`tests/test_tethered_poc.py`)

## Backlog

| ID | Pri | Status | Task | Owner |
|----|-----|--------|------|-------|
| T-005 | P0 | [ ] | Configure exact OV2640 pinout and `SD_MMC` initialization for target ESP32-S3 board and compile/flash with PlatformIO (`firmware/esp32_smart_helmet/src/main.cpp`) | unassigned |
| T-006 | P0 | [ ] | Wire LD2410 24GHz mmWave radar to ESP32-S3 RX/TX and verify real serial target parsing (`firmware/esp32_smart_helmet/src/main.cpp`) | unassigned |
| T-007 | P0 | [ ] | Verify 3-minute MJPEG MicroSD loop recording without frame drops on ESP32-S3 (`dashcamLoopTask`) | unassigned |
| T-008 | P0 | [ ] | Test live BLE GATT (`181C`) 512-byte chunked JPEG transfer from ESP32-S3 to `edge_receiver/receiver.py` and verify <1.5s round-trip latency | unassigned |
| T-009 | P1 | [ ] | Integrate local CoreML / TFLite vehicle classification model (`Car`, `Truck`, `Motorcycle`) into `edge_receiver/classifier.py` / mobile companion app | unassigned |
| T-010 | P1 | [ ] | Add 6-axis IMU crash detection + SOS GPS/cellular trigger and route `Audio_Command` (`PLAY:...`) to helmet speakers | unassigned |
| T-011 | P1 | [ ] | Build iOS/Android companion app skeleton with background BLE execution entitlements and <1.5s end-to-end latency testing | unassigned |
| T-012 | P2 | [ ] | Add ANT+ / RF handlebar turn-signal remote sync prototype per product plan | unassigned |
| T-013 | P2 | [ ] | Phase 3 ergonomics: 3D-print sub-100g "Spider" dummy mounts (~500mAh LiPo form factor) and run helmet balance ride tests | unassigned |

## Notes / Known limitations
- Hardware-dependent items (T-005 through T-008) cannot be verified without the ESP32-S3 PSRAM/OV2640 board, LD2410 radar, MicroSD card, and BLE radio.
- Current `tests/test_tethered_poc.py` and `--mock` mode validate 512-byte BLE JPEG chunking/reassembly, telemetry/command codecs, and simulated round-trip latency.
