"""Unit and integration tests for the Smart Helmet Phase 1 PoC."""

from __future__ import annotations

import asyncio
import unittest

import numpy as np

from poc.alert_manager import AlertManager, format_collision_alert
from poc.camera_classifier import CameraClassifier, ClassificationResult, map_raw_label
from poc.config import PocConfig
from poc.crash_detect import CrashDetector, CrashEvent, CrashState, ImuSample, compute_g_force
from poc.main_controller import run_controller
from poc.radar_watchman import RadarReading, RadarThreatEvent, RadarWatchman, parse_radar_line


class TestRadarWatchman(unittest.TestCase):
    def test_parse_key_value_and_json(self) -> None:
        r1 = parse_radar_line("DIST:32.5,VEL:22.1,ANG:-6.0", now=10.0)
        self.assertIsNotNone(r1)
        assert r1 is not None
        self.assertEqual(r1.distance_m, 32.5)
        self.assertEqual(r1.closing_speed_mph, 22.1)
        self.assertEqual(r1.angle_deg, -6.0)

        r2 = parse_radar_line('{"distance_m": 18.0, "closing_speed_mph": 30.0}', now=11.0)
        self.assertIsNotNone(r2)
        assert r2 is not None
        self.assertEqual(r2.distance_m, 18.0)
        self.assertEqual(r2.closing_speed_mph, 30.0)

        self.assertIsNone(parse_radar_line("GARBAGE_LINE"))
        self.assertIsNone(parse_radar_line(""))

    def test_threat_threshold_and_cooldown(self) -> None:
        cfg = PocConfig(mock_mode=True, radar_cooldown_s=2.0)
        watchman = RadarWatchman(cfg)

        # Too far / too slow -> no threat
        self.assertIsNone(watchman.evaluate_line("DIST:60.0,VEL:25.0", now=1.0))
        self.assertIsNone(watchman.evaluate_line("DIST:25.0,VEL:10.0", now=1.5))
        self.assertFalse(watchman.threat_detected)

        # Within 50m and >15 mph -> triggers
        ev1 = watchman.evaluate_line("DIST:25.0,VEL:20.0", now=2.0)
        self.assertIsNotNone(ev1)
        self.assertTrue(watchman.threat_detected)

        # Within cooldown -> suppressed
        self.assertIsNone(watchman.evaluate_line("DIST:20.0,VEL:22.0", now=3.0))

        # After cooldown -> triggers again
        ev2 = watchman.evaluate_line("DIST:15.0,VEL:24.0", now=4.5)
        self.assertIsNotNone(ev2)


class TestCameraClassifier(unittest.TestCase):
    def test_label_mapping(self) -> None:
        self.assertEqual(map_raw_label("sports car"), "Car")
        self.assertEqual(map_raw_label("trailer truck"), "Truck")
        self.assertEqual(map_raw_label("motorcycle"), "Motorcycle")
        self.assertEqual(map_raw_label("traffic light"), "Unknown")

    def test_triggered_burst_under_latency_budget(self) -> None:
        cfg = PocConfig(mock_mode=True, camera_burst_frames=4)
        dummy_frames = [np.zeros((224, 224, 3), dtype=np.uint8) for _ in range(4)]
        classifier = CameraClassifier(
            cfg,
            frame_capturer=lambda _n: dummy_frames,
            mock_classifier=lambda _f: ("Motorcycle", 0.88),
        )
        event = RadarThreatEvent(
            reading=RadarReading(distance_m=20.0, closing_speed_mph=22.0),
            triggered_at=100.0,
        )
        # Use current monotonic time for realistic latency check
        import time

        event = RadarThreatEvent(reading=event.reading, triggered_at=time.monotonic())
        result = classifier.handle_threat(event)
        self.assertEqual(result.label, "Motorcycle")
        self.assertEqual(result.frames_analyzed, 4)
        self.assertLess(result.trigger_latency_ms, cfg.trigger_latency_budget_ms)


class TestCrashDetector(unittest.TestCase):
    def test_g_force_and_crash_stillness_triggers_sos(self) -> None:
        cfg = PocConfig(mock_mode=True, crash_g_threshold=6.0, stillness_duration_s=2.0)
        detector = CrashDetector(cfg)

        self.assertAlmostEqual(compute_g_force(ImuSample(0.0, 0.0, 1.0)), 1.0)
        self.assertIsNone(detector.process_sample(ImuSample(0.0, 0.0, 1.0, timestamp=1.0)))
        self.assertEqual(detector.state, CrashState.MONITORING)

        # >6G impact spike
        self.assertIsNone(detector.process_sample(ImuSample(6.5, 1.0, 0.5, gx_dps=90.0, timestamp=2.0)))
        self.assertEqual(detector.state, CrashState.IMPACT_DETECTED)

        # Stillness for 1.0s (not enough yet)
        self.assertIsNone(detector.process_sample(ImuSample(0.0, 0.0, 1.0, gx_dps=1.0, timestamp=2.5)))
        self.assertIsNone(detector.process_sample(ImuSample(0.0, 0.0, 1.0, gx_dps=1.0, timestamp=3.5)))

        # Stillness crosses 2.0s -> SOS_PROTOCOL
        crash = detector.process_sample(ImuSample(0.0, 0.0, 1.0, gx_dps=1.0, timestamp=4.6))
        self.assertIsNotNone(crash)
        assert crash is not None
        self.assertTrue(detector.sos_protocol)
        self.assertEqual(detector.state, CrashState.SOS_TRIGGERED)
        self.assertGreater(crash.peak_g, 6.0)

    def test_pothole_followed_by_movement_resets(self) -> None:
        cfg = PocConfig(mock_mode=True, crash_g_threshold=6.0, stillness_duration_s=2.0)
        detector = CrashDetector(cfg)

        detector.process_sample(ImuSample(6.2, 0.0, 0.0, gx_dps=50.0, timestamp=1.0))
        self.assertEqual(detector.state, CrashState.IMPACT_DETECTED)

        # Rider keeps riding (high angular motion)
        detector.process_sample(ImuSample(0.1, 0.2, 1.0, gx_dps=45.0, timestamp=1.5))
        self.assertEqual(detector.state, CrashState.MONITORING)
        self.assertFalse(detector.sos_protocol)


class TestAlertManager(unittest.IsolatedAsyncioTestCase):
    def test_format_collision_alert(self) -> None:
        res = ClassificationResult(label="Truck", confidence=0.92, frames_analyzed=4, trigger_latency_ms=25.0)
        msg = format_collision_alert(res, RadarReading(distance_m=22.0, closing_speed_mph=30.0, angle_deg=-8.0))
        self.assertEqual(msg, "Fast truck approaching left")

    async def test_sos_sends_webhook_when_not_cancelled(self) -> None:
        cfg = PocConfig(mock_mode=True, sos_countdown_s=0.05)
        alerts = AlertManager(cfg)
        sent = await alerts.handle_sos(CrashEvent(peak_g=7.5, stillness_duration_s=2.1, triggered_at=10.0))
        self.assertTrue(sent)
        self.assertEqual(len(alerts.sos_dispatched_payloads), 1)
        self.assertIn("Crash detected, calling 911", alerts.spoken_messages[0])

    async def test_sos_cancelled_before_timeout(self) -> None:
        cfg = PocConfig(mock_mode=True, sos_countdown_s=1.0)
        alerts = AlertManager(cfg)

        async def cancel_soon() -> None:
            await asyncio.sleep(0.05)
            alerts.cancel_sos()

        task = asyncio.create_task(cancel_soon())
        sent = await alerts.handle_sos(CrashEvent(peak_g=7.5, stillness_duration_s=2.1, triggered_at=10.0))
        await task
        self.assertFalse(sent)
        self.assertEqual(len(alerts.sos_dispatched_payloads), 0)
        self.assertEqual(alerts.spoken_messages[-1], "SOS cancelled")


class TestMainControllerIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_mock_mixed_scenario_end_to_end(self) -> None:
        cfg = PocConfig(
            mock_mode=True,
            stillness_duration_s=0.15,
            sos_countdown_s=0.05,
            radar_poll_interval_s=0.01,
            imu_sample_rate_hz=50.0,
        )
        summary = await run_controller(cfg, duration_s=0.9, scenario="mixed")
        self.assertGreaterEqual(summary["spoken_alerts"], 2)
        self.assertEqual(summary["sos_webhooks_sent"], 1)


if __name__ == "__main__":
    unittest.main()
