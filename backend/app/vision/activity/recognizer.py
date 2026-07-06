"""
Human Activity Recognition (HAR).

Two implementations share a common `Activity` output:

* `HeuristicActivityRecognizer` — dependency-light, real-time. Infers
  walking / running / standing / loitering / falling / crawling from the
  tracked person's motion signature (speed, aspect-ratio dynamics, vertical
  displacement). Works out of the box with no extra model download.

* `DeepActivityRecognizer` — wraps a 3D-CNN (torchvision R3D-18) or a video
  transformer for clip-level classification of complex activities such as
  fighting / violence / falling. Loads a fine-tuned checkpoint if present,
  otherwise the pipeline gracefully falls back to the heuristic recogniser.

Train the deep model with `ml/training/train_activity.py`.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional

import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.vision.types import Track


@dataclass
class Activity:
    """A recognised activity for a specific track."""

    track_id: int
    label: str
    confidence: float


# Labels the system understands (superset across both recognisers).
ACTIVITY_LABELS = [
    "standing", "walking", "running", "loitering",
    "falling", "crawling", "fighting", "violence",
]


class HeuristicActivityRecognizer:
    """Rule/kinematics-based activity recogniser (no heavy model)."""

    def __init__(self) -> None:
        # Per-track short history of (aspect_ratio, foot_y) for fall/crawl cues.
        self._history: Dict[int, Deque] = {}

    def recognise(self, tracks: List[Track]) -> List[Activity]:
        results: List[Activity] = []
        for t in tracks:
            if t.class_name != "person":
                continue
            x1, y1, x2, y2 = t.bbox
            w, h = max(1.0, x2 - x1), max(1.0, y2 - y1)
            aspect = w / h  # >1 means wider than tall — lying/falling cue
            hist = self._history.setdefault(t.track_id, deque(maxlen=15))
            hist.append((aspect, (y1 + y2) / 2.0, t.speed))

            label, conf = self._classify(t, hist, aspect)
            results.append(Activity(track_id=t.track_id, label=label, confidence=conf))
        # Garbage-collect stale histories.
        active = {t.track_id for t in tracks}
        for tid in list(self._history):
            if tid not in active:
                self._history.pop(tid, None)
        return results

    @staticmethod
    def _classify(track: Track, hist: Deque, aspect: float):
        speed = track.speed
        # Fall: rapid increase in aspect ratio (person becomes horizontal) with
        # a preceding drop in center height.
        if len(hist) >= 6:
            aspects = [a for a, _, _ in hist]
            if aspects[-1] > 1.15 and (aspects[-1] - min(aspects[:-3])) > 0.5:
                return "falling", 0.72
        if aspect > 1.4 and speed < 40:
            return "crawling", 0.6
        if speed >= settings.RUNNING_SPEED_PX_PER_S:
            return "running", min(0.95, 0.6 + speed / 1000)
        if speed < 25 and track.dwell_seconds >= settings.LOITERING_SECONDS:
            return "loitering", 0.65
        if speed < 25:
            return "standing", 0.7
        return "walking", 0.75


class DeepActivityRecognizer:
    """Clip-level activity classifier backed by a 3D CNN (R3D-18)."""

    def __init__(self, checkpoint: Optional[str] = None,
                 clip_len: int = 16, device: Optional[str] = None) -> None:
        self.clip_len = clip_len
        self.device = device or ("cuda" if _cuda_available() else "cpu")
        self.labels = ["walking", "running", "standing", "fighting",
                       "falling", "violence"]
        self._model = None
        self._buffer: Deque[np.ndarray] = deque(maxlen=clip_len)
        self._load(checkpoint)

    def _load(self, checkpoint: Optional[str]) -> None:
        try:
            import torch
            from torchvision.models.video import r3d_18

            model = r3d_18(weights=None)
            import torch.nn as nn
            model.fc = nn.Linear(model.fc.in_features, len(self.labels))
            if checkpoint:
                state = torch.load(checkpoint, map_location=self.device)
                model.load_state_dict(state)
                logger.success(f"Loaded activity checkpoint: {checkpoint}")
            else:
                logger.warning("No activity checkpoint provided — deep HAR will "
                               "return low-confidence outputs until trained.")
            self._model = model.eval().to(self.device)
        except Exception as exc:  # pragma: no cover
            logger.warning(f"DeepActivityRecognizer unavailable ({exc}).")
            self._model = None

    def push_frame(self, frame_bgr: np.ndarray) -> None:
        """Append a frame (a person crop or full frame) to the clip buffer."""
        import cv2

        img = cv2.resize(frame_bgr, (112, 112))
        self._buffer.append(img[:, :, ::-1] / 255.0)  # BGR->RGB, normalise

    def predict(self) -> Optional[Activity]:
        """Classify the buffered clip once it is full."""
        if self._model is None or len(self._buffer) < self.clip_len:
            return None
        import torch

        clip = np.stack(self._buffer, axis=0)             # (T,H,W,C)
        clip = np.transpose(clip, (3, 0, 1, 2))            # (C,T,H,W)
        x = torch.from_numpy(clip).float().unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self._model(x)
            probs = torch.softmax(logits, dim=1)[0]
            idx = int(torch.argmax(probs))
        return Activity(track_id=-1, label=self.labels[idx],
                        confidence=float(probs[idx]))


def _cuda_available() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:
        return False
