# Smart Helmet Module (Phase 1 PoC)

An aftermarket, detachable smart helmet module combining asymmetric sensor fusion (mmWave radar-triggered CSI camera AI), IMU crash detection with automated SOS, and hands-free audio alerts.

See [Product Development Plan](doc/smart_helmet_module_product_plan.md) for the full product vision and [Software PoC Plan](doc/smart_helmet_software_poc_plan.md) for the Phase 1 Raspberry Pi Zero 2 W architecture.

## Repository Layout

| Path | Purpose |
|---|---|
| [poc/config.py](poc/config.py) | Thresholds, hardware ports/bus addresses, and model paths |
| [poc/radar_watchman.py](poc/radar_watchman.py) | UART mmWave radar reader and collision threat trigger |
| [poc/camera_classifier.py](poc/camera_classifier.py) | Dormant CSI camera burst capture + TFLite MobileNet vehicle classifier |
| [poc/crash_detect.py](poc/crash_detect.py) | 6-axis I2C IMU G-force spike + stillness crash detector |
| [poc/alert_manager.py](poc/alert_manager.py) | Bluetooth TTS collision warnings and 15s cancellable SOS webhook |
| [poc/main_controller.py](poc/main_controller.py) | `asyncio` orchestrator + `--mock` simulation runner |
| [tests/test_poc.py](tests/test_poc.py) | Unit and integration tests |

## Quick Start (Simulation / Dev Machine)

```powershell
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m poc.main_controller --mock --scenario mixed --duration 4 --sos-countdown 1
```

## Raspberry Pi Zero 2 W (Hardware Mode)

```bash
pip install -r requirements-pi.txt
python -m poc.main_controller
```

## Docs
- [Product Development Plan](doc/smart_helmet_module_product_plan.md)
- [Software PoC Plan](doc/smart_helmet_software_poc_plan.md)
- [Backlog](doc/backlog.md) · [Contributing (agents)](doc/CONTRIBUTING_AGENTS.md)
