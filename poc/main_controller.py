"""Central asyncio orchestrator for the Smart Helmet Phase 1 PoC."""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from typing import Optional

from poc.alert_manager import AlertManager
from poc.camera_classifier import CameraClassifier
from poc.config import PocConfig
from poc.crash_detect import CrashDetector, CrashEvent, ImuSample
from poc.radar_watchman import RadarThreatEvent, RadarWatchman

logger = logging.getLogger(__name__)


class MockSensorFeed:
    """Provides deterministic simulated UART radar lines and I2C IMU samples for `--mock` runs."""

    def __init__(self, scenario: str = "mixed") -> None:
        self.scenario = scenario
        self._start = time.monotonic()
        self._radar_emitted = False
        self._impact_emitted = False

    def next_radar_line(self) -> Optional[str]:
        elapsed = time.monotonic() - self._start
        if self.scenario in ("collision", "mixed") and not self._radar_emitted and elapsed >= 0.2:
            self._radar_emitted = True
            return "DIST:28.0,VEL:28.5,ANG:-8.0"
        return "DIST:85.0,VEL:2.0,ANG:0.0"

    def next_imu_sample(self) -> ImuSample:
        now = time.monotonic()
        elapsed = now - self._start
        if self.scenario in ("crash", "mixed") and not self._impact_emitted and elapsed >= 0.4:
            self._impact_emitted = True
            return ImuSample(ax_g=7.2, ay_g=1.5, az_g=0.8, gx_dps=120.0, timestamp=now)
        return ImuSample(ax_g=0.0, ay_g=0.0, az_g=1.0, gx_dps=0.5, timestamp=now)


async def _collision_worker(
    threat_queue: asyncio.Queue[RadarThreatEvent],
    classifier: CameraClassifier,
    alerts: AlertManager,
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set() or not threat_queue.empty():
        try:
            event = await asyncio.wait_for(threat_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            continue
        result = await asyncio.to_thread(classifier.handle_threat, event)
        msg = await alerts.alert_collision(result, event.reading)
        logger.info(
            "Collision alert: %r (label=%s conf=%.2f frames=%d latency=%.1fms)",
            msg,
            result.label,
            result.confidence,
            result.frames_analyzed,
            result.trigger_latency_ms,
        )
        threat_queue.task_done()


async def _crash_worker(
    crash_queue: asyncio.Queue[CrashEvent],
    alerts: AlertManager,
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set() or not crash_queue.empty():
        try:
            event = await asyncio.wait_for(crash_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            continue
        dispatched = await alerts.handle_sos(event)
        logger.info("SOS protocol completed (webhook_sent=%s, peak_g=%.2f)", dispatched, event.peak_g)
        crash_queue.task_done()


async def run_controller(
    config: PocConfig,
    duration_s: Optional[float] = None,
    scenario: str = "mixed",
) -> dict[str, int]:
    """Run all PoC modules concurrently and return a summary of handled events."""
    threat_queue: asyncio.Queue[RadarThreatEvent] = asyncio.Queue()
    crash_queue: asyncio.Queue[CrashEvent] = asyncio.Queue()
    stop_event = asyncio.Event()

    mock_feed = MockSensorFeed(scenario=scenario) if config.mock_mode else None
    radar = RadarWatchman(
        config,
        line_reader=mock_feed.next_radar_line if mock_feed else None,
    )
    classifier = CameraClassifier(
        config,
        mock_classifier=(lambda _frames: ("Truck", 0.94)) if config.mock_mode else None,
    )
    crash_detector = CrashDetector(
        config,
        sample_reader=mock_feed.next_imu_sample if mock_feed else None,
    )
    alerts = AlertManager(config)

    tasks = [
        asyncio.create_task(radar.run(threat_queue, stop_event), name="radar_watchman"),
        asyncio.create_task(crash_detector.run(crash_queue, stop_event), name="crash_detect"),
        asyncio.create_task(_collision_worker(threat_queue, classifier, alerts, stop_event), name="collision_worker"),
        asyncio.create_task(_crash_worker(crash_queue, alerts, stop_event), name="crash_worker"),
    ]

    try:
        if duration_s is not None:
            await asyncio.sleep(duration_s)
            stop_event.set()
        else:
            await asyncio.gather(*tasks)
    finally:
        stop_event.set()
        await asyncio.gather(*tasks, return_exceptions=True)
        classifier.close()

    return {
        "spoken_alerts": len(alerts.spoken_messages),
        "sos_webhooks_sent": len(alerts.sos_dispatched_payloads),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smart Helmet Phase 1 PoC Controller")
    parser.add_argument("--mock", action="store_true", help="Run with simulated radar, camera, IMU, and audio")
    parser.add_argument(
        "--scenario",
        choices=("collision", "crash", "mixed"),
        default="mixed",
        help="Mock scenario to simulate when --mock is enabled",
    )
    parser.add_argument("--duration", type=float, default=None, help="Optional run duration in seconds")
    parser.add_argument("--sos-countdown", type=float, default=None, help="Override SOS countdown seconds")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    args = _parse_args()
    cfg_kwargs: dict[str, object] = {"mock_mode": args.mock}
    if args.sos_countdown is not None:
        cfg_kwargs["sos_countdown_s"] = args.sos_countdown
    config = PocConfig(**cfg_kwargs)  # type: ignore[arg-type]

    try:
        summary = asyncio.run(run_controller(config, duration_s=args.duration, scenario=args.scenario))
        logger.info("Controller stopped: %s", summary)
    except KeyboardInterrupt:
        logger.info("Controller interrupted by user.")


if __name__ == "__main__":
    main()
