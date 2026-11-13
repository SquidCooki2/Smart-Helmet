"""Unit and integration tests for the Tethered Edge Compute Smart Helmet PoC."""

from __future__ import annotations

import unittest

from edge_receiver.ble_protocol import (
    JpegReassembler,
    RadarTelemetry,
    chunk_jpeg_packets,
    format_audio_command,
    format_spoken_prompt,
    parse_radar_telemetry,
)
from edge_receiver.classifier import EdgeClassifier
from edge_receiver.config import EdgeConfig
from edge_receiver.receiver import run_mock_round_trip


class TestBleProtocol(unittest.TestCase):
    def test_parse_radar_telemetry(self) -> None:
        t = parse_radar_telemetry("DIST:30,SPD:45")
        self.assertEqual(t, RadarTelemetry(distance_m=30.0, speed_mph=45.0))
        self.assertIsNone(parse_radar_telemetry("INVALID"))
        self.assertIsNone(parse_radar_telemetry("DIST:abc,SPD:10"))

    def test_audio_command_and_prompt(self) -> None:
        self.assertEqual(format_audio_command("Truck"), "PLAY:TRUCK_APPROACHING")
        self.assertEqual(format_audio_command("Car"), "PLAY:CAR_APPROACHING")
        self.assertEqual(format_audio_command("Unknown"), "PLAY:VEHICLE_APPROACHING")

        prompt = format_spoken_prompt("Truck", RadarTelemetry(distance_m=30.0, speed_mph=45.0))
        self.assertEqual(prompt, "Fast truck approaching")

    def test_512_byte_chunking_and_reassembly(self) -> None:
        payload = b"\xff\xd8" + bytes(range(256)) * 60 + b"\xff\xd9"  # ~15.3KB JPEG
        packets = chunk_jpeg_packets(payload, mtu_bytes=512)
        self.assertTrue(all(len(p) <= 512 for p in packets))
        self.assertGreater(len(packets), 1)

        reassembler = JpegReassembler()
        assembled = None
        for pkt in packets[:-1]:
            self.assertIsNone(reassembler.feed_packet(pkt))
        assembled = reassembler.feed_packet(packets[-1])
        self.assertEqual(assembled, payload)

    def test_out_of_order_reassembly(self) -> None:
        payload = b"A" * 1200
        packets = chunk_jpeg_packets(payload, mtu_bytes=512)
        self.assertEqual(len(packets), 3)

        reassembler = JpegReassembler()
        # Deliver EOF packet first, then 0, then 1
        self.assertIsNone(reassembler.feed_packet(packets[2]))
        self.assertIsNone(reassembler.feed_packet(packets[0]))
        self.assertEqual(reassembler.feed_packet(packets[1]), payload)


class TestEdgeClassifier(unittest.TestCase):
    def test_mock_classification(self) -> None:
        cfg = EdgeConfig(mock_mode=True)
        clf = EdgeClassifier(cfg, mock_predictor=lambda _b: ("Motorcycle", 0.91))
        res = clf.classify_jpeg(b"\xff\xd8\xff\xd9")
        self.assertEqual(res.label, "Motorcycle")
        self.assertEqual(res.confidence, 0.91)
        self.assertEqual(res.jpeg_bytes_len, 4)


class TestMockRoundTrip(unittest.IsolatedAsyncioTestCase):
    async def test_mock_round_trip_under_1500ms(self) -> None:
        cfg = EdgeConfig(mock_mode=True)
        res = await run_mock_round_trip(cfg, jpeg_size_bytes=15360)
        self.assertIsNotNone(res.telemetry)
        self.assertEqual(res.classification.label, "Truck")
        self.assertEqual(res.classification.jpeg_bytes_len, 15360)
        self.assertEqual(res.audio_command, "PLAY:TRUCK_APPROACHING")
        self.assertEqual(res.spoken_prompt, "Fast truck approaching")
        self.assertTrue(res.within_budget)
        self.assertLess(res.round_trip_ms, cfg.round_trip_budget_ms)


if __name__ == "__main__":
    unittest.main()
