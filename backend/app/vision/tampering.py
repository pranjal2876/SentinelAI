"""
Camera-tampering detection.

Detects three classic tampering conditions by analysing the raw frame stream:

* **Blur / defocus** — sudden collapse in high-frequency content
  (variance of the Laplacian).
* **Occlusion / covered lens** — large fraction of the frame becomes uniformly
  dark or low-contrast.
* **Scene change / moved camera** — abrupt, sustained drop in similarity with a
  running background reference (mean absolute difference).

It is intentionally model-free and cheap so it can run on every camera.
"""
from __future__ import annotations

import time
from typing import Optional

import cv2
import numpy as np

from app.vision.types import ThreatCategory, ThreatEvent


class TamperingDetector:
    """Frame-level tamper detection with hysteresis to avoid flicker."""

    def __init__(
        self,
        camera_id: str,
        blur_threshold: float = 45.0,
        dark_ratio_threshold: float = 0.85,
        scene_change_threshold: float = 55.0,
        persistence_frames: int = 15,
        cooldown_s: float = 20.0,
    ) -> None:
        self.camera_id = camera_id
        self.blur_threshold = blur_threshold
        self.dark_ratio_threshold = dark_ratio_threshold
        self.scene_change_threshold = scene_change_threshold
        self.persistence_frames = persistence_frames
        self.cooldown_s = cooldown_s
        self._bg: Optional[np.ndarray] = None
        self._streak = 0
        self._last_alert = 0.0

    def update(self, frame: np.ndarray, now: Optional[float] = None
               ) -> Optional[ThreatEvent]:
        now = now or time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (320, 180))

        blur = cv2.Laplacian(small, cv2.CV_64F).var()
        dark_ratio = float(np.mean(small < 30))

        scene_diff = 0.0
        if self._bg is None:
            self._bg = small.astype(np.float32)
        else:
            scene_diff = float(np.mean(cv2.absdiff(small, self._bg.astype(np.uint8))))
            # Slow-updating background reference.
            cv2.accumulateWeighted(small.astype(np.float32), self._bg, 0.02)

        reason = None
        if blur < self.blur_threshold:
            reason = "defocus/blur"
        elif dark_ratio > self.dark_ratio_threshold:
            reason = "lens occluded"
        elif scene_diff > self.scene_change_threshold:
            reason = "camera moved / scene changed"

        if reason:
            self._streak += 1
        else:
            self._streak = max(0, self._streak - 2)

        if (self._streak >= self.persistence_frames
                and (now - self._last_alert) >= self.cooldown_s):
            self._last_alert = now
            self._streak = 0
            return ThreatEvent(
                category=ThreatCategory.CAMERA_TAMPERING,
                score=0.88,
                camera_id=self.camera_id,
                timestamp=now,
                message=f"Possible camera tampering: {reason}.",
                metadata={"reason": reason, "blur": round(blur, 1),
                          "dark_ratio": round(dark_ratio, 2),
                          "scene_diff": round(scene_diff, 1)},
            )
        return None
