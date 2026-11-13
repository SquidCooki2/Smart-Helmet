"""UART mmWave radar watchman that detects approaching collision threats."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Callable, Optional

from poc.config import PocConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RadarReading:
    """Parsed measurement from the rear-facing mmWave radar sensor."""

    distance_m: float
    closing_speed_mph: float
    angle_deg: float = 0.0
    timestamp: float = 0.0


@dataclass(frozen=True)
class RadarThreatEvent:
    """Event emitted when a radar reading crosses the collision threat threshold."""

    reading: RadarReading
    triggered_at: float


def parse_radar_line(raw_line: str, now: Optional[float] = None) -> Optional[RadarReading]:
    """Parse a UART radar line in JSON or `DIST:<m>,VEL:<mph>[,ANG:<deg>]` format."""
    line = raw_line.strip()
    if not line:
        return None
    ts = time.monotonic() if now is None else now

    if line.startswith("{"):
        try:
            payload = json.loads(line)
            return RadarReading(
                distance_m=float(payload["distance_m"]),
                closing_speed_mph=float(payload["closing_speed_mph"]),
                angle_deg=float(payload.get("angle_deg", 0.0)),
                timestamp=ts,
            )
        except (ValueError, KeyError, TypeError):
            return None

    fields: dict[str, float] = {}
    for token in line.split(","):
        if ":" not in token:
            continue
        key, val = token.split(":", 1)
        try:
            fields[key.strip().upper()] = float(val.strip())
        except ValueError:
            return None

    if "DIST" not in fields or "VEL" not in fields:
        return None

    return RadarReading(
        distance_m=fields["DIST"],
        closing_speed_mph=fields["VEL"],
        angle_deg=fields.get("ANG", 0.0),
        timestamp=ts,
    )


class RadarWatchman:
    """Continuously monitors mmWave radar over UART and flags `THREAT_DETECTED`."""

    def __init__(
        self,
        config: PocConfig,
        line_reader: Optional[Callable[[], Optional[str]]] = None,
    ) -> None:
        self.config = config
        self._line_reader = line_reader
        self._serial = None
        self._last_trigger_ts = -float("inf")
        self.threat_detected = False

    def _open_serial(self):
        if self._line_reader is not None or self.config.mock_mode:
            return
        import serial  # type: ignore[import-untyped]

        self._serial = serial.Serial(
            port=self.config.radar_serial_port,
            baudrate=self.config.radar_baudrate,
            timeout=0.1,
        )
        logger.info("Opened radar UART on %s @ %d", self.config.radar_serial_port, self.config.radar_baudrate)

    def close(self) -> None:
        """Close the UART serial port if open."""
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def read_line(self) -> Optional[str]:
        """Read one raw line from the injected reader or UART serial port."""
        if self._line_reader is not None:
            return self._line_reader()
        if self._serial is None:
            return None
        raw = self._serial.readline()
        return raw.decode("utf-8", errors="ignore") if raw else None

    def is_threat(self, reading: RadarReading) -> bool:
        """Return True when target is within danger distance and closing above speed threshold."""
        return (
            0.0 < reading.distance_m < self.config.radar_max_distance_m
            and reading.closing_speed_mph > self.config.radar_danger_speed_mph
        )

    def evaluate_line(self, raw_line: str, now: Optional[float] = None) -> Optional[RadarThreatEvent]:
        """Parse one line and return a RadarThreatEvent if threat criteria + cooldown pass."""
        ts = time.monotonic() if now is None else now
        reading = parse_radar_line(raw_line, now=ts)
        if reading is None:
            return None
        if not self.is_threat(reading):
            self.threat_detected = False
            return None

        self.threat_detected = True
        if (ts - self._last_trigger_ts) < self.config.radar_cooldown_s:
            return None

        self._last_trigger_ts = ts
        return RadarThreatEvent(reading=reading, triggered_at=ts)

    async def run(
        self,
        threat_queue: asyncio.Queue[RadarThreatEvent],
        stop_event: asyncio.Event,
    ) -> None:
        """Continuously poll the radar and push threat events without blocking."""
        self._open_serial()
        try:
            while not stop_event.is_set():
                line = await asyncio.to_thread(self.read_line)
                if line:
                    event = self.evaluate_line(line)
                    if event is not None:
                        await threat_queue.put(event)
                await asyncio.sleep(self.config.radar_poll_interval_s)
        finally:
            self.close()
