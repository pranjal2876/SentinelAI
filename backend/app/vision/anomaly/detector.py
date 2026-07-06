"""
Unsupervised motion-anomaly detection.

Two complementary approaches are provided:

1. `IsolationForest` over per-frame motion feature vectors (fast, online-ish,
   retrainable). This is the default runtime detector.
2. A PyTorch autoencoder (`autoencoder.py`) whose reconstruction error flags
   rare frames — used for offline training / higher-accuracy deployments.

The runtime detector maintains a rolling buffer of scene feature vectors:
    [ num_objects, mean_speed, speed_std, mean_area, motion_entropy ]
It fits an IsolationForest once enough samples are gathered, then scores each
new frame. Scores above a percentile threshold raise an ANOMALY threat.
"""
from __future__ import annotations

import time
from collections import deque
from typing import Deque, List, Optional, Tuple

import numpy as np

from app.core.logging import logger
from app.vision.types import Track, ThreatCategory, ThreatEvent


def scene_features(tracks: List[Track]) -> np.ndarray:
    """Compute a compact motion feature vector describing the current scene."""
    if not tracks:
        return np.zeros(5, dtype=float)
    speeds = np.array([t.speed for t in tracks], dtype=float)
    areas = np.array([
        max(1.0, (t.bbox[2] - t.bbox[0]) * (t.bbox[3] - t.bbox[1]))
        for t in tracks
    ])
    # Directional entropy from trajectory headings.
    headings = []
    for t in tracks:
        if len(t.trajectory) >= 2:
            dx = t.trajectory[-1][0] - t.trajectory[-2][0]
            dy = t.trajectory[-1][1] - t.trajectory[-2][1]
            headings.append(np.arctan2(dy, dx))
    if headings:
        hist, _ = np.histogram(headings, bins=8, range=(-np.pi, np.pi))
        p = hist / (hist.sum() + 1e-9)
        entropy = float(-np.sum(p * np.log(p + 1e-9)))
    else:
        entropy = 0.0
    return np.array([
        len(tracks),
        float(speeds.mean()),
        float(speeds.std()),
        float(np.log1p(areas.mean())),
        entropy,
    ], dtype=float)


class MotionAnomalyDetector:
    """Online IsolationForest anomaly detector over scene motion features."""

    def __init__(
        self,
        camera_id: str,
        buffer_size: int = 900,        # ~30-60s of frames
        min_train: int = 150,
        refit_every: int = 300,
        contamination: float = 0.03,
        cooldown_s: float = 12.0,
    ) -> None:
        self.camera_id = camera_id
        self.buffer: Deque[np.ndarray] = deque(maxlen=buffer_size)
        self.min_train = min_train
        self.refit_every = refit_every
        self.contamination = contamination
        self.cooldown_s = cooldown_s
        self._model = None
        self._frames_since_fit = 0
        self._last_alert = 0.0
        self._score_ref: Optional[Tuple[float, float]] = None  # (mean, std)

    def _fit(self) -> None:
        from sklearn.ensemble import IsolationForest

        data = np.array(self.buffer)
        self._model = IsolationForest(
            n_estimators=100,
            contamination=self.contamination,
            random_state=42,
        )
        self._model.fit(data)
        scores = self._model.score_samples(data)
        self._score_ref = (float(scores.mean()), float(scores.std() + 1e-6))
        self._frames_since_fit = 0
        logger.debug(f"[{self.camera_id}] IsolationForest (re)fitted on "
                     f"{len(data)} samples.")

    def update(self, tracks: List[Track], now: Optional[float] = None
               ) -> Optional[ThreatEvent]:
        """Push the current scene and return an ANOMALY event if flagged."""
        now = now or time.time()
        feat = scene_features(tracks)
        self.buffer.append(feat)
        self._frames_since_fit += 1

        if self._model is None:
            if len(self.buffer) >= self.min_train:
                self._fit()
            return None

        if self._frames_since_fit >= self.refit_every:
            self._fit()

        raw = float(self._model.score_samples(feat.reshape(1, -1))[0])
        mean, std = self._score_ref  # type: ignore[misc]
        # Lower score => more anomalous. Convert to a positive z-deviation.
        z = (mean - raw) / std
        if z > 3.0 and (now - self._last_alert) >= self.cooldown_s and tracks:
            self._last_alert = now
            score = float(min(0.95, 0.55 + (z - 3.0) * 0.1))
            return ThreatEvent(
                category=ThreatCategory.ANOMALY,
                score=score,
                camera_id=self.camera_id,
                timestamp=now,
                message=f"Unusual scene dynamics detected (anomaly z={z:.1f}).",
                track_ids=[t.track_id for t in tracks],
                metadata={"z_score": round(z, 2), "features": feat.round(2).tolist()},
            )
        return None
