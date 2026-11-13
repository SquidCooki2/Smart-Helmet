#pragma once

// BLE GATT Service & Characteristics (Helmet_Safety_Service)
#define HELMET_SERVICE_UUID        "181C"
#define RADAR_TELEMETRY_CHAR_UUID  "2A6D"
#define IMAGE_TRANSFER_CHAR_UUID   "2A6E"
#define AUDIO_COMMAND_CHAR_UUID    "2A6F"

// BLE MTU & Snapshot framing
constexpr size_t BLE_MTU_BYTES = 512;
constexpr size_t CHUNK_HEADER_BYTES = 4; // [seq_lo, seq_hi, flags, reserved]
constexpr size_t CHUNK_PAYLOAD_MAX = BLE_MTU_BYTES - CHUNK_HEADER_BYTES;
constexpr uint8_t CHUNK_FLAG_EOF = 0x01;

// Radar (LD2410 24GHz mmWave over UART)
constexpr int RADAR_RX_PIN = 44;
constexpr int RADAR_TX_PIN = 43;
constexpr long RADAR_BAUDRATE = 256000;
constexpr float DANGER_CLOSING_SPEED_MPH = 15.0f;
constexpr float DANGER_MAX_DISTANCE_M = 50.0f;
constexpr unsigned long TRIGGER_COOLDOWN_MS = 2000;

// Dashcam MicroSD Loop Recording
constexpr unsigned long DASHCAM_CHUNK_DURATION_MS = 180000; // 3-minute MJPEG chunks
constexpr size_t MAX_DASHCAM_FILES = 20;
