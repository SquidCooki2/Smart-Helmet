"""6-axis I2C IMU crash detector (G-force spike + post-impact stillness)."""

from __future__ import annotations

import asyncio
import logging
import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from poc.config import PocConfig

logger = logging.getLogger(__name__)

# MPU-6050 register addresses and default scale factors (+/-2g, +/-250 dps)
_MPU_PWR_MGMT_1 = 0x6B
_MPU_ACCEL_XOUT_H = 0x3B
_MPU_GYRO_XOUT_H = 0x43
_ACCEL_SCALE_LSB_PER_G = 16384.0
_GYRO_SCALE_LSB_PER_DPS = 131.0


class CrashState(str, Enum):
    """State machine states for crash detection."""

    MONITORING = "monitoring"
    IMPACT_DETECTED = "impact_detected"
    SOS_TRIGGERED = "sos_triggered"


@dataclass(frozen=True)
class ImuSample:
    """Single 6-axis IMU measurement in Gs and degrees/sec."""

    ax_g: float
    ay_g: float
    az_g: float
    gx_dps: float = 0.0
    gy_dps: float = 0.0
    gz_dps: float = 0.0
    timestamp: float = 0.0


@dataclass(frozen=True)
class CrashEvent:
    """Event emitted when a crash (>6G spike + sustained stillness) is confirmed."""

    peak_g: float
    stillness_duration_s: float
    triggered_at: float


def compute_g_force(sample: ImuSample) -> float:
    """Compute total G-force vector magnitude from 3-axis acceleration."""
    return math.sqrt(sample.ax_g ** 2 + sample.ay_g ** 2 + sample.az_g ** 2)


def compute_gyro_magnitude(sample: ImuSample) -> float:
    """Compute angular velocity magnitude in degrees per second."""
    return math.sqrt(sample.gx_dps ** 2 + sample.gy_dps ** 2 + sample.gz_dps ** 2)


def _signed_word(high: int, low: int) -> int:
    val = (high << 8) | low
    return val - 65536 if val >= 32768 else val


class CrashDetector:
    """Monitors 6-axis IMU via I2C and triggers `SOS_PROTOCOL` on crash + stillness."""

    def __init__(
        self,
        config: PocConfig,
        sample_reader: Optional[Callable[[], Optional[ImuSample]]] = None,
    ) -> None:
        self.config = config
        self._sample_reader = sample_reader
        self._bus = None
        self.state = CrashState.MONITORING
        self.sos_protocol = False
        self._peak_g = 0.0
        self._stillness_start_ts: Optional[float] = None

    def _open_i2c(self) -> None:
        if self._sample_reader is not None or self.config.mock_mode:
            return
        from smbus2 import SMBus  # type: ignore[import-untyped]

        self._bus = SMBus(self.config.imu_i2c_bus)
        # Wake MPU-6050 from sleep
        self._bus.write_byte_data(self.config.imu_i2c_addr, _MPU_PWR_MGMT_1, 0x00)
        logger.info("Opened IMU I2C on bus %d addr 0x%02X", self.config.imu_i2c_bus, self.config.imu_i2c_addr)

    def close(self) -> None:
        """Close the I2C bus if open."""
        if self._bus is not None:
            self._bus.close()
            self._bus = None

    def read_sample(self) -> Optional[ImuSample]:
        """Read one 6-axis sample from injected reader or I2C IMU."""
        if self._sample_reader is not None:
            return self._sample_reader()
        if self._bus is None:
            return None

        accel_bytes = self._bus.read_i2c_block_data(self.config.imu_i2c_addr, _MPU_ACCEL_XOUT_H, 6)
        gyro_bytes = self._bus.read_i2c_block_data(self.config.imu_i2c_addr, _MPU_GYRO_XOUT_H, 6)
        return ImuSample(
            ax_g=_signed_word(accel_bytes[0], accel_bytes[1]) / _ACCEL_SCALE_LSB_PER_G,
            ay_g=_signed_word(accel_bytes[2], accel_bytes[3]) / _ACCEL_SCALE_LSB_PER_G,
            az_g=_signed_word(accel_bytes[4], accel_bytes[5]) / _ACCEL_SCALE_LSB_PER_G,
            gx_dps=_signed_word(gyro_bytes[0], gyro_bytes[1]) / _GYRO_SCALE_LSB_PER_DPS,
            gy_dps=_signed_word(gyro_bytes[2], gyro_bytes[3]) / _GYRO_SCALE_LSB_PER_DPS,
            gz_dps=_signed_word(gyro_bytes[4], gyro_bytes[5]) / _GYRO_SCALE_LSB_PER_DPS,
            timestamp=time.monotonic(),
        )

    def _is_still(self, sample: ImuSample, g_force: float) -> bool:
        return (
            abs(g_force - 1.0) <= self.config.stillness_g_delta
            and compute_gyro_magnitude(sample) <= self.config.stillness_gyro_dps_max
        )

    def reset(self) -> None:
        """Reset crash state machine back to MONITORING."""
        self.state = CrashState.MONITORING
        self.sos_protocol = False
        self._peak_g = 0.0
        self._stillness_start_ts = None

    def process_sample(self, sample: ImuSample) -> Optional[CrashEvent]:
        """Evaluate one IMU sample and return a CrashEvent if SOS_PROTOCOL triggers."""
        ts = sample.timestamp if sample.timestamp > 0 else time.monotonic()
        g_force = compute_g_force(sample)

        if self.state == CrashState.MONITORING:
            if g_force > self.config.crash_g_threshold:
                self.state = CrashState.IMPACT_DETECTED
                self._peak_g = g_force
                self._stillness_start_ts = None
                logger.warning("High-G impact detected: %.2f G", g_force)
            return None

        if self.state == CrashState.IMPACT_DETECTED:
            if g_force > self._peak_g:
                self._peak_g = g_force

            if self._is_still(sample, g_force):
                if self._stillness_start_ts is None:
                    self._stillness_start_ts = ts
                elapsed = ts - self._stillness_start_ts
                if elapsed >= self.config.stillness_duration_s:
                    self.state = CrashState.SOS_TRIGGERED
                    self.sos_protocol = True
                    return CrashEvent(
                        peak_g=self._peak_g,
                        stillness_duration_s=elapsed,
                        triggered_at=ts,
                    )
            else:
                # Rider is still moving (e.g., pothole or normal riding)
                if g_force <= self.config.crash_g_threshold:
                    self._stillness_start_ts = None
                    if compute_gyro_magnitude(sample) > self.config.stillness_gyro_dps_max * 2:
                        self.reset()
            return None

        return None

    async def run(
        self,
        crash_queue: asyncio.Queue[CrashEvent],
        stop_event: asyncio.Event,
    ) -> None:
        """Continuously poll the IMU at `imu_sample_rate_hz`."""
        self._open_i2c()
        interval = 1.0 / max(1.0, self.config.imu_sample_rate_hz)
        try:
            while not stop_event.is_set():
                sample = await asyncio.to_thread(self.read_sample)
                if sample is not None:
                    event = self.process_sample(sample)
                    if event is not None:
                        await crash_queue.put(event)
                await asyncio.sleep(interval)
        finally:
            self.close()
