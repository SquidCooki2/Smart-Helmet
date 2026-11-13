"""CSI camera controller and coarse TFLite vehicle classifier."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

import numpy as np

from poc.config import PocConfig
from poc.radar_watchman import RadarThreatEvent

logger = logging.getLogger(__name__)

VALID_CLASSES = ("Car", "Truck", "Motorcycle", "Unknown")

_LABEL_MAP = {
    "car": "Car",
    "sedan": "Car",
    "suv": "Car",
    "cab": "Car",
    "truck": "Truck",
    "pickup": "Truck",
    "trailer truck": "Truck",
    "van": "Truck",
    "bus": "Truck",
    "motorcycle": "Motorcycle",
    "motorbike": "Motorcycle",
    "moped": "Motorcycle",
    "scooter": "Motorcycle",
}


@dataclass(frozen=True)
class ClassificationResult:
    """Coarse vehicle classification output from a triggered camera burst."""

    label: str
    confidence: float
    frames_analyzed: int
    trigger_latency_ms: float


def map_raw_label(raw_label: str) -> str:
    """Map a raw MobileNet/ImageNet label to Car, Truck, Motorcycle, or Unknown."""
    normalized = raw_label.strip().lower()
    for key, coarse in _LABEL_MAP.items():
        if key in normalized:
            return coarse
    return "Unknown"


class CameraClassifier:
    """Remains dormant until radar triggers a burst capture and TFLite classification."""

    def __init__(
        self,
        config: PocConfig,
        frame_capturer: Optional[Callable[[int], Sequence[np.ndarray]]] = None,
        mock_classifier: Optional[Callable[[Sequence[np.ndarray]], tuple[str, float]]] = None,
    ) -> None:
        self.config = config
        self._frame_capturer = frame_capturer
        self._mock_classifier = mock_classifier
        self._interpreter = None
        self._labels: list[str] = []
        self._picam2 = None

        if not config.mock_mode and mock_classifier is None:
            self._load_tflite()

    def _load_tflite(self) -> None:
        if not self.config.tflite_model_path.exists():
            logger.warning(
                "TFLite model not found at %s; falling back to Unknown classifier.",
                self.config.tflite_model_path,
            )
            return
        try:
            from tflite_runtime.interpreter import Interpreter  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("tflite-runtime not installed; falling back to Unknown classifier.")
            return

        self._interpreter = Interpreter(model_path=str(self.config.tflite_model_path))
        self._interpreter.allocate_tensors()
        if self.config.tflite_labels_path.exists():
            self._labels = [
                line.strip()
                for line in self.config.tflite_labels_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        logger.info("Loaded TFLite model from %s", self.config.tflite_model_path)

    def _capture_csi_burst(self, num_frames: int) -> list[np.ndarray]:
        if self._frame_capturer is not None:
            return list(self._frame_capturer(num_frames))
        if self.config.mock_mode:
            return [
                np.zeros((self.config.camera_height, self.config.camera_width, 3), dtype=np.uint8)
                for _ in range(num_frames)
            ]

        if self._picam2 is None:
            from picamera2 import Picamera2  # type: ignore[import-untyped]

            self._picam2 = Picamera2()
            cfg = self._picam2.create_still_configuration(
                main={"size": (self.config.camera_width, self.config.camera_height), "format": "RGB888"}
            )
            self._picam2.configure(cfg)
            self._picam2.start()

        return [self._picam2.capture_array() for _ in range(num_frames)]

    def _classify_frames(self, frames: Sequence[np.ndarray]) -> tuple[str, float]:
        if self._mock_classifier is not None:
            return self._mock_classifier(frames)
        if self.config.mock_mode:
            return ("Car", 0.91)
        if self._interpreter is None or not frames:
            return ("Unknown", 0.0)

        input_details = self._interpreter.get_input_details()[0]
        output_details = self._interpreter.get_output_details()[0]
        votes: dict[str, list[float]] = {}

        for frame in frames:
            tensor = np.expand_dims(frame, axis=0)
            if input_details["dtype"] == np.float32:
                tensor = tensor.astype(np.float32) / 255.0
            else:
                tensor = tensor.astype(input_details["dtype"])
            self._interpreter.set_tensor(input_details["index"], tensor)
            self._interpreter.invoke()
            scores = self._interpreter.get_tensor(output_details["index"])[0]
            top_idx = int(np.argmax(scores))
            conf = float(scores[top_idx])
            raw_name = self._labels[top_idx] if top_idx < len(self._labels) else "unknown"
            coarse = map_raw_label(raw_name)
            votes.setdefault(coarse, []).append(conf)

        best_label = max(votes, key=lambda k: (len(votes[k]), sum(votes[k])))
        avg_conf = sum(votes[best_label]) / len(votes[best_label])
        return (best_label, avg_conf)

    def handle_threat(self, event: RadarThreatEvent) -> ClassificationResult:
        """Wake up on radar trigger, capture burst frames, and return coarse classification."""
        frames = self._capture_csi_burst(self.config.camera_burst_frames)
        capture_done_ts = time.monotonic()
        trigger_latency_ms = max(0.0, (capture_done_ts - event.triggered_at) * 1000.0)

        if trigger_latency_ms > self.config.trigger_latency_budget_ms:
            logger.warning(
                "Trigger-to-capture latency %.1f ms exceeded %.1f ms budget.",
                trigger_latency_ms,
                self.config.trigger_latency_budget_ms,
            )

        label, confidence = self._classify_frames(frames)
        if label not in VALID_CLASSES:
            label = "Unknown"

        return ClassificationResult(
            label=label,
            confidence=confidence,
            frames_analyzed=len(frames),
            trigger_latency_ms=trigger_latency_ms,
        )

    def close(self) -> None:
        """Release the CSI camera resource if initialized."""
        if self._picam2 is not None:
            self._picam2.stop()
            self._picam2.close()
            self._picam2 = None
