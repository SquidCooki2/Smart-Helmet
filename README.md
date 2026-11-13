# Smart Helmet Module (Tethered Edge Compute PoC)

An aftermarket, detachable smart helmet module using a **Tethered Edge Compute** architecture: an **ESP32-S3** helmet unit handles continuous MicroSD dashcam loop-recording, 24GHz mmWave radar monitoring, and BLE GATT snapshot handoff, while the **smartphone / edge receiver** reassembles the JPEG, runs local ML classification, and dispatches audio alerts.

See [Product Development Plan](doc/smart_helmet_module_product_plan.md) for the full product roadmap and [Software PoC Plan](doc/smart_helmet_software_poc_plan.md) for the ESP32-S3 + BLE GATT (`181C`) PoC specification.

## Repository Layout

| Path | Purpose |
|---|---|
| [firmware/esp32_smart_helmet/](firmware/esp32_smart_helmet) | ESP32-S3 C++/Arduino FreeRTOS firmware (Core 0 dashcam loop, Core 1 LD2410 radar watchdog + 512B BLE snapshot handoff) |
| [edge_receiver/config.py](edge_receiver/config.py) | BLE GATT UUIDs (`181C`, `2A6D`, `2A6E`, `2A6F`), 512-byte MTU framing, and 1.5s latency budget |
| [edge_receiver/ble_protocol.py](edge_receiver/ble_protocol.py) | 512-byte JPEG chunking/reassembly, `Radar_Telemetry` parser, and `Audio_Command` codec |
| [edge_receiver/classifier.py](edge_receiver/classifier.py) | Local ML vehicle classifier (`Car`, `Truck`, `Motorcycle`, `Unknown`) |
| [edge_receiver/receiver.py](edge_receiver/receiver.py) | BLE GATT client (`bleak`) and `--mock` end-to-end round-trip simulator |
| [tests/test_tethered_poc.py](tests/test_tethered_poc.py) | Unit and integration tests |

## Quick Start (Simulation / Edge Receiver Tests)

```powershell
python -m venv .venv; .venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
python -m edge_receiver.receiver --mock
```

## Hardware Mode (ESP32-S3 + BLE Receiver)

1. Flash [firmware/esp32_smart_helmet/](firmware/esp32_smart_helmet) using PlatformIO (`pio run -t upload`).
2. Install receiver dependencies and connect over BLE:
   ```powershell
   pip install -r requirements.txt
   python -m edge_receiver.receiver
   ```

## Docs
- [Product Development Plan](doc/smart_helmet_module_product_plan.md)
- [Software PoC Plan](doc/smart_helmet_software_poc_plan.md)
- [Backlog](doc/backlog.md) · [Contributing (agents)](doc/CONTRIBUTING_AGENTS.md)
