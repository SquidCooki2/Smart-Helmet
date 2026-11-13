"""BLE GATT client & Tethered Edge Compute PoC runner (supports `--mock`)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

from edge_receiver.ble_protocol import (
    JpegReassembler,
    RadarTelemetry,
    chunk_jpeg_packets,
    format_audio_command,
    format_spoken_prompt,
    parse_radar_telemetry,
)
from edge_receiver.classifier import EdgeClassifier, SnapshotClassification
from edge_receiver.config import EdgeConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RoundTripResult:
    """End-to-end snapshot round-trip telemetry and classification."""

    telemetry: Optional[RadarTelemetry]
    classification: SnapshotClassification
    audio_command: str
    spoken_prompt: str
    round_trip_ms: float
    within_budget: bool


def _build_dummy_jpeg(size_bytes: int = 15360) -> bytes:
    """Create a ~15KB synthetic JPEG-framed payload (SOI + padding + EOI) for mock BLE testing."""
    body_len = max(0, size_bytes - 4)
    return b"\xff\xd8" + (b"\x00" * body_len) + b"\xff\xd9"


async def run_mock_round_trip(config: EdgeConfig, jpeg_size_bytes: int = 15360) -> RoundTripResult:
    """Simulate ESP32 radar trigger -> 512B BLE JPEG transfer -> edge AI -> audio command."""
    classifier = EdgeClassifier(config)
    reassembler = JpegReassembler()

    t0 = time.monotonic()
    telemetry = parse_radar_telemetry("DIST:30,SPD:45")
    packets = chunk_jpeg_packets(_build_dummy_jpeg(jpeg_size_bytes), mtu_bytes=config.ble_mtu_bytes)

    assembled: Optional[bytes] = None
    for pkt in packets:
        await asyncio.sleep(0.001)  # Simulate BLE notification pacing
        assembled = reassembler.feed_packet(pkt)

    assert assembled is not None, "Mock BLE JPEG reassembly failed"
    classification = classifier.classify_jpeg(assembled)
    audio_cmd = format_audio_command(classification.label)
    prompt = format_spoken_prompt(classification.label, telemetry)
    elapsed_ms = (time.monotonic() - t0) * 1000.0

    return RoundTripResult(
        telemetry=telemetry,
        classification=classification,
        audio_command=audio_cmd,
        spoken_prompt=prompt,
        round_trip_ms=elapsed_ms,
        within_budget=elapsed_ms < config.round_trip_budget_ms,
    )


async def run_ble_client(config: EdgeConfig) -> None:
    """Connect to the physical ESP32-S3 Helmet_Safety_Service via `bleak`."""
    from bleak import BleakClient, BleakScanner  # type: ignore[import-untyped]

    device = await BleakScanner.find_device_by_name(config.device_name, timeout=10.0)
    if device is None:
        raise RuntimeError(f"BLE device {config.device_name!r} not found")

    classifier = EdgeClassifier(config)
    reassembler = JpegReassembler()
    latest_telemetry: Optional[RadarTelemetry] = None
    trigger_ts = time.monotonic()

    async with BleakClient(device) as client:
        logger.info("Connected to %s (%s)", config.device_name, device.address)

        def on_radar(_sender: int, data: bytearray) -> None:
            nonlocal latest_telemetry, trigger_ts
            trigger_ts = time.monotonic()
            latest_telemetry = parse_radar_telemetry(data.decode("utf-8", errors="ignore"))
            logger.info("Radar telemetry: %s", latest_telemetry)

        async def _handle_image(jpeg_bytes: bytes) -> None:
            res = classifier.classify_jpeg(jpeg_bytes)
            cmd = format_audio_command(res.label)
            prompt = format_spoken_prompt(res.label, latest_telemetry)
            await client.write_gatt_char(config.audio_command_uuid, cmd.encode("utf-8"))
            elapsed_ms = (time.monotonic() - trigger_ts) * 1000.0
            logger.info("Prompt=%r Cmd=%s Latency=%.1fms", prompt, cmd, elapsed_ms)

        def on_image(_sender: int, data: bytearray) -> None:
            assembled = reassembler.feed_packet(bytes(data))
            if assembled is not None:
                asyncio.create_task(_handle_image(assembled))

        await client.start_notify(config.radar_telemetry_uuid, on_radar)
        await client.start_notify(config.image_transfer_uuid, on_image)
        while client.is_connected:
            await asyncio.sleep(0.5)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Smart Helmet Tethered Edge Compute Receiver")
    parser.add_argument("--mock", action="store_true", help="Run simulated ESP32->BLE->AI round-trip")
    args = parser.parse_args()

    cfg = EdgeConfig(mock_mode=args.mock)
    if args.mock:
        res = asyncio.run(run_mock_round_trip(cfg))
        logger.info(
            "Mock round-trip: telemetry=%s label=%s bytes=%d cmd=%s prompt=%r latency=%.1fms within_budget=%s",
            res.telemetry,
            res.classification.label,
            res.classification.jpeg_bytes_len,
            res.audio_command,
            res.spoken_prompt,
            res.round_trip_ms,
            res.within_budget,
        )
    else:
        asyncio.run(run_ble_client(cfg))


if __name__ == "__main__":
    main()
