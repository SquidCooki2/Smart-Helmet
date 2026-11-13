"""BLE GATT protocol helpers: 512-byte JPEG chunking/reassembly and telemetry/audio codecs."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional

CHUNK_HEADER_FORMAT = "<HBB"  # uint16 seq, uint8 flags, uint8 reserved
CHUNK_HEADER_SIZE = struct.calcsize(CHUNK_HEADER_FORMAT)
CHUNK_FLAG_EOF = 0x01


@dataclass(frozen=True)
class RadarTelemetry:
    """Parsed `Radar_Telemetry` characteristic payload (`DIST:30,SPD:45`)."""

    distance_m: float
    speed_mph: float


def parse_radar_telemetry(raw_text: str) -> Optional[RadarTelemetry]:
    """Parse `DIST:<m>,SPD:<mph>` telemetry string from the ESP32."""
    fields: dict[str, float] = {}
    for part in raw_text.strip().split(","):
        if ":" not in part:
            continue
        key, val = part.split(":", 1)
        try:
            fields[key.strip().upper()] = float(val.strip())
        except ValueError:
            return None
    if "DIST" not in fields or "SPD" not in fields:
        return None
    return RadarTelemetry(distance_m=fields["DIST"], speed_mph=fields["SPD"])


def format_audio_command(vehicle_label: str) -> str:
    """Format `Audio_Command` characteristic payload (e.g., `PLAY:TRUCK_APPROACHING`)."""
    normalized = vehicle_label.strip().upper()
    if normalized not in ("CAR", "TRUCK", "MOTORCYCLE"):
        normalized = "VEHICLE"
    return f"PLAY:{normalized}_APPROACHING"


def format_spoken_prompt(vehicle_label: str, telemetry: Optional[RadarTelemetry] = None) -> str:
    """Format human-readable voice alert (e.g., 'Fast truck approaching')."""
    label = vehicle_label.lower() if vehicle_label in ("Car", "Truck", "Motorcycle") else "vehicle"
    if telemetry is not None and telemetry.speed_mph >= 25.0:
        return f"Fast {label} approaching"
    return f"{label.capitalize()} approaching"


def chunk_jpeg_packets(jpeg_bytes: bytes, mtu_bytes: int = 512) -> list[bytes]:
    """Split a JPEG buffer into <=mtu_bytes BLE packets with 4-byte sequence/EOF headers."""
    if mtu_bytes <= CHUNK_HEADER_SIZE:
        raise ValueError("mtu_bytes must exceed header size")
    max_payload = mtu_bytes - CHUNK_HEADER_SIZE
    if not jpeg_bytes:
        return [struct.pack(CHUNK_HEADER_FORMAT, 0, CHUNK_FLAG_EOF, 0)]

    packets: list[bytes] = []
    total = len(jpeg_bytes)
    offset = 0
    seq = 0
    while offset < total:
        chunk = jpeg_bytes[offset : offset + max_payload]
        offset += len(chunk)
        flags = CHUNK_FLAG_EOF if offset >= total else 0
        header = struct.pack(CHUNK_HEADER_FORMAT, seq, flags, 0)
        packets.append(header + chunk)
        seq += 1
    return packets


class JpegReassembler:
    """Reassembles incoming 512-byte BLE `Image_Transfer` packets into a JPEG buffer."""

    def __init__(self) -> None:
        self._chunks: dict[int, bytes] = {}
        self._eof_seq: Optional[int] = None

    def reset(self) -> None:
        self._chunks.clear()
        self._eof_seq = None

    def feed_packet(self, packet: bytes) -> Optional[bytes]:
        """Add one BLE packet; return complete JPEG bytes once all packets up to EOF arrive."""
        if len(packet) < CHUNK_HEADER_SIZE:
            return None
        seq, flags, _ = struct.unpack(CHUNK_HEADER_FORMAT, packet[:CHUNK_HEADER_SIZE])
        self._chunks[seq] = packet[CHUNK_HEADER_SIZE:]
        if flags & CHUNK_FLAG_EOF:
            self._eof_seq = seq

        if self._eof_seq is None:
            return None
        expected_count = self._eof_seq + 1
        if len(self._chunks) < expected_count:
            return None
        if not all(i in self._chunks for i in range(expected_count)):
            return None

        assembled = b"".join(self._chunks[i] for i in range(expected_count))
        self.reset()
        return assembled
