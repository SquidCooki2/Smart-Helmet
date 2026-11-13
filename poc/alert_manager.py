"""Audio alerts over Bluetooth and 15-second cancellable SOS webhook dispatcher."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import urllib.request
from typing import Callable, Optional

from poc.camera_classifier import ClassificationResult
from poc.config import PocConfig
from poc.crash_detect import CrashEvent
from poc.radar_watchman import RadarReading

logger = logging.getLogger(__name__)


def format_collision_alert(classification: ClassificationResult, reading: RadarReading) -> str:
    """Format a concise spoken collision warning from radar + camera outputs."""
    vehicle = classification.label.lower() if classification.label != "Unknown" else "vehicle"
    speed_prefix = "Fast " if reading.closing_speed_mph >= 25.0 else ""

    if reading.angle_deg <= -5.0:
        direction = " approaching left"
    elif reading.angle_deg >= 5.0:
        direction = " approaching right"
    else:
        direction = " approaching"

    phrase = f"{speed_prefix}{vehicle}{direction}"
    return phrase[0].upper() + phrase[1:]


class AlertManager:
    """Manages Bluetooth TTS collision warnings and the 15s SOS countdown/webhook."""

    def __init__(
        self,
        config: PocConfig,
        speaker: Optional[Callable[[str], None]] = None,
        webhook_sender: Optional[Callable[[dict], bool]] = None,
    ) -> None:
        self.config = config
        self._speaker = speaker
        self._webhook_sender = webhook_sender
        self._sos_cancel_event = asyncio.Event()
        self.spoken_messages: list[str] = []
        self.sos_dispatched_payloads: list[dict] = []

    def speak(self, text: str) -> None:
        """Speak an alert over Bluetooth audio (or mock/callback)."""
        self.spoken_messages.append(text)
        if self._speaker is not None:
            self._speaker(text)
            return
        if self.config.mock_mode:
            logger.info("[AUDIO MOCK] %s", text)
            return
        try:
            subprocess.run([self.config.tts_command, text], check=False)
        except FileNotFoundError:
            logger.warning("TTS command %r not found; logged alert: %s", self.config.tts_command, text)

    async def alert_collision(
        self,
        classification: ClassificationResult,
        reading: RadarReading,
    ) -> str:
        """Format and play a collision warning without blocking the event loop."""
        message = format_collision_alert(classification, reading)
        await asyncio.to_thread(self.speak, message)
        return message

    def cancel_sos(self) -> None:
        """Cancel an active SOS countdown."""
        self._sos_cancel_event.set()

    def _send_webhook(self, payload: dict) -> bool:
        self.sos_dispatched_payloads.append(payload)
        if self._webhook_sender is not None:
            return self._webhook_sender(payload)
        if self.config.mock_mode:
            logger.critical("[SOS WEBHOOK MOCK] POST %s payload=%s", self.config.sos_webhook_url, payload)
            return True

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.config.sos_webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.config.sos_webhook_timeout_s) as resp:
                return 200 <= resp.status < 300
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send SOS webhook: %s", exc)
            return False

    async def handle_sos(self, crash_event: CrashEvent) -> bool:
        """Run the 15s audio countdown; send mock/API SOS webhook unless cancelled."""
        self._sos_cancel_event.clear()
        seconds = int(round(self.config.sos_countdown_s))
        await asyncio.to_thread(
            self.speak,
            f"Crash detected, calling 911 in {seconds} seconds",
        )

        try:
            await asyncio.wait_for(self._sos_cancel_event.wait(), timeout=self.config.sos_countdown_s)
            await asyncio.to_thread(self.speak, "SOS cancelled")
            logger.info("SOS countdown cancelled by rider.")
            return False
        except asyncio.TimeoutError:
            payload = {
                "event": "SOS_PROTOCOL",
                "peak_g": round(crash_event.peak_g, 2),
                "stillness_duration_s": round(crash_event.stillness_duration_s, 2),
                "message": "Automated smart helmet crash alert.",
            }
            return await asyncio.to_thread(self._send_webhook, payload)
