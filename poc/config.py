"""Central configuration for the Smart Helmet Phase 1 PoC."""

from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class PocConfig:
    """Configuration parameters for radar, camera AI, IMU crash detection, and alerts."""

    # Runtime mode
    mock_mode: bool = False

    # Radar Watchman (UART mmWave)
    radar_serial_port: str = "/dev/ttyS0"
    radar_baudrate: int = 115200
    radar_max_distance_m: float = 50.0
    radar_danger_speed_mph: float = 15.0
    radar_cooldown_s: float = 2.0
    radar_poll_interval_s: float = 0.02

    # Camera Classifier (CSI + TFLite MobileNet)
    camera_burst_frames: int = 4
    camera_width: int = 224
    camera_height: int = 224
    tflite_model_path: Path = BASE_DIR / "models" / "mobilenet_v2_vehicle.tflite"
    tflite_labels_path: Path = BASE_DIR / "models" / "labels.txt"
    trigger_latency_budget_ms: float = 200.0

    # Crash Detection (6-axis I2C IMU)
    imu_i2c_bus: int = 1
    imu_i2c_addr: int = 0x68
    imu_sample_rate_hz: float = 50.0
    crash_g_threshold: float = 6.0
    stillness_g_delta: float = 0.25
    stillness_gyro_dps_max: float = 15.0
    stillness_duration_s: float = 2.0

    # Alert Manager & SOS
    sos_countdown_s: float = 15.0
    sos_webhook_url: str = "http://localhost:8090/sos"
    sos_webhook_timeout_s: float = 5.0
    tts_command: str = "espeak"
