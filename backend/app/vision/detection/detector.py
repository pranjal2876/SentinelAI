"""
YOLO-based object detector (Ultralytics YOLOv8).

Wraps the Ultralytics API behind a stable interface returning our own
`Detection` dataclasses, so the rest of the pipeline is decoupled from the
underlying model version. Supports GPU with automatic CPU fallback and an
optional class allow-list for surveillance-relevant categories.
"""
from __future__ import annotations

from typing import Iterable, List, Optional

import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.vision.types import Detection

# Subset of the 80 COCO classes that matter for surveillance. The detector
# still runs full inference; this list is used to *filter* results.
COCO_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    24: "backpack",
    26: "handbag",
    28: "suitcase",
}

# Classes considered "carriable objects" for abandoned-object logic.
CARRIABLE_CLASSES = {"backpack", "handbag", "suitcase"}
VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck", "bicycle"}


def resolve_device(preference: str) -> str:
    """Resolve the torch device string from a user preference."""
    if preference == "cpu":
        return "cpu"
    try:
        import torch

        if preference in ("auto", "cuda") and torch.cuda.is_available():
            return "cuda:0"
    except Exception as exc:  # pragma: no cover - torch import guard
        logger.warning(f"Could not query CUDA availability: {exc}")
    if preference == "cuda":
        logger.warning("CUDA requested but unavailable — falling back to CPU.")
    return "cpu"


class ObjectDetector:
    """Thin, reusable wrapper over an Ultralytics YOLO model."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf: Optional[float] = None,
        iou: Optional[float] = None,
        device: Optional[str] = None,
        allowed_classes: Optional[Iterable[int]] = None,
    ) -> None:
        self.model_path = model_path or settings.YOLO_MODEL
        self.conf = conf if conf is not None else settings.DETECTION_CONF_THRESHOLD
        self.iou = iou if iou is not None else settings.DETECTION_IOU_THRESHOLD
        self.device = device or resolve_device(settings.DEVICE)
        self.allowed_classes = (
            set(allowed_classes) if allowed_classes is not None
            else set(COCO_CLASSES.keys())
        )
        self._model = None
        self._load()

    def _load(self) -> None:
        from ultralytics import YOLO

        logger.info(
            f"Loading YOLO model '{self.model_path}' on device '{self.device}'"
        )
        self._model = YOLO(self.model_path)
        # Warm up so the first real frame isn't penalised.
        try:
            self._model.to(self.device)
        except Exception as exc:  # pragma: no cover
            logger.warning(f"Model .to({self.device}) failed ({exc}); using CPU.")
            self.device = "cpu"
        logger.success(f"YOLO model ready ({self.model_path}).")

    @property
    def class_names(self) -> dict[int, str]:
        """Class-id -> name map exposed by the underlying model."""
        return self._model.names if self._model else COCO_CLASSES

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Run detection on a single BGR frame.

        Returns a list of `Detection` filtered to the allowed classes.
        """
        if self._model is None:
            raise RuntimeError("Detector model is not loaded.")

        results = self._model.predict(
            source=frame,
            conf=self.conf,
            iou=self.iou,
            device=self.device,
            verbose=False,
        )
        detections: List[Detection] = []
        if not results:
            return detections

        r = results[0]
        if r.boxes is None:
            return detections

        names = self.class_names
        for box in r.boxes:
            cls_id = int(box.cls[0])
            if cls_id not in self.allowed_classes:
                continue
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].tolist()
            detections.append(
                Detection(
                    bbox=(xyxy[0], xyxy[1], xyxy[2], xyxy[3]),
                    confidence=conf,
                    class_id=cls_id,
                    class_name=names.get(cls_id, COCO_CLASSES.get(cls_id, str(cls_id))),
                )
            )
        return detections
