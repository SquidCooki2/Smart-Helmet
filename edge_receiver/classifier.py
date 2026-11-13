"""Local edge ML vehicle classifier for reassembled BLE JPEG snapshots."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from edge_receiver.config import EdgeConfig

logger = logging.getLogger(__name__)

VALID_LABELS = ("Car", "Truck", "Motorcycle", "Unknown")


@dataclass(frozen=True)
class SnapshotClassification:
    """Result of classifying a reassembled BLE JPEG snapshot."""

    label: str
    confidence: float
    jpeg_bytes_len: int


class EdgeClassifier:
    """Runs local NPU/TFLite classification (or deterministic mock in PoC mode)."""

    def __init__(
        self,
        config: EdgeConfig,
        mock_predictor: Optional[Callable[[bytes], tuple[str, float]]] = None,
    ) -> None:
        self.config = config
        self._mock_predictor = mock_predictor

    def classify_jpeg(self, jpeg_bytes: bytes) -> SnapshotClassification:
        """Classify a reassembled JPEG snapshot into Car, Truck, Motorcycle, or Unknown."""
        if self._mock_predictor is not None:
            label, conf = self._mock_predictor(jpeg_bytes)
        elif self.config.mock_mode:
            label, conf = ("Truck", 0.93)
        else:
            # Hardware/TFLite path placeholder until mobile CoreML/TFLite model is supplied
            logger.warning("No local TFLite model loaded at %s; returning Unknown", self.config.tflite_model_path)
            label, conf = ("Unknown", 0.0)

        if label not in VALID_LABELS:
            label = "Unknown"

        return SnapshotClassification(
            label=label,
            confidence=conf,
            jpeg_bytes_len=len(jpeg_bytes),
        )
