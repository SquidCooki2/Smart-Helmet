"""Configuration for the Tethered Edge Compute BLE receiver."""

from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class EdgeConfig:
    """BLE GATT UUIDs, MTU framing, ML model paths, and latency budget."""

    mock_mode: bool = False
    device_name: str = "SmartHelmet-ESP32"

    # Helmet_Safety_Service GATT UUIDs
    service_uuid: str = "0000181c-0000-1000-8000-00805f9b34fb"
    radar_telemetry_uuid: str = "00002a6d-0000-1000-8000-00805f9b34fb"
    image_transfer_uuid: str = "00002a6e-0000-1000-8000-00805f9b34fb"
    audio_command_uuid: str = "00002a6f-0000-1000-8000-00805f9b34fb"

    # 512-byte BLE MTU framing
    ble_mtu_bytes: int = 512
    chunk_header_bytes: int = 4
    chunk_flag_eof: int = 0x01

    # Local ML & Latency Budget (Phase 2 goal: < 1.5 seconds round-trip)
    tflite_model_path: Path = BASE_DIR / "models" / "vehicle_mobilenet.tflite"
    round_trip_budget_ms: float = 1500.0
    fast_speed_mph: float = 25.0
