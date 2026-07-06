"""
Multi-object tracker — a ByteTrack-inspired association pipeline.

Design
------
* Each active target is a `_STrack` carrying a Kalman motion model.
* Association uses IoU cost solved with the Hungarian algorithm.
* Two-stage matching (ByteTrack idea): first associate high-confidence
  detections, then recover low-confidence ones against still-unmatched tracks.
* Tracks survive a configurable number of missed frames (`max_age`) to bridge
  occlusions, and must be confirmed for `min_hits` frames before being emitted.

Output is a list of our `Track` dataclass (persistent IDs, trajectory, speed).
"""
from __future__ import annotations

import time
from collections import deque
from typing import Deque, List, Tuple

import numpy as np
from scipy.optimize import linear_sum_assignment

from app.core.config import settings
from app.vision.tracking.kalman import KalmanBoxTracker
from app.vision.types import Detection, Track

_TRAJECTORY_MAXLEN = 64


def _iou(a: Tuple[float, float, float, float],
         b: Tuple[float, float, float, float]) -> float:
    """Intersection-over-union of two xyxy boxes."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


class _STrack:
    """Internal single-target track state."""

    _next_id = 1

    def __init__(self, det: Detection, now: float) -> None:
        self.id = _STrack._next_id
        _STrack._next_id += 1
        self.kf = KalmanBoxTracker(det.bbox)
        self.class_id = det.class_id
        self.class_name = det.class_name
        self.confidence = det.confidence
        self.first_seen = now
        self.last_seen = now
        self.hits = 1
        self.age = 0
        self.time_since_update = 0
        self.trajectory: Deque[Tuple[float, float]] = deque(maxlen=_TRAJECTORY_MAXLEN)
        self.trajectory.append(det.foot_point)
        self.speed = 0.0

    @classmethod
    def reset_ids(cls) -> None:
        cls._next_id = 1

    def predict(self) -> None:
        self.kf.predict()
        self.age += 1
        self.time_since_update += 1

    def update(self, det: Detection, now: float, fps: float) -> None:
        prev_foot = self.trajectory[-1] if self.trajectory else det.foot_point
        self.kf.update(det.bbox)
        self.confidence = det.confidence
        self.class_id = det.class_id
        self.class_name = det.class_name
        self.last_seen = now
        self.hits += 1
        self.time_since_update = 0
        foot = det.foot_point
        self.trajectory.append(foot)
        # Instantaneous speed (px/s) using effective fps.
        dt = 1.0 / max(fps, 1e-3)
        dist = float(np.hypot(foot[0] - prev_foot[0], foot[1] - prev_foot[1]))
        # Exponential smoothing to reduce jitter.
        self.speed = 0.7 * self.speed + 0.3 * (dist / dt)

    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        return self.kf.bbox

    def to_track(self) -> Track:
        return Track(
            track_id=self.id,
            class_id=self.class_id,
            class_name=self.class_name,
            bbox=self.bbox,
            confidence=self.confidence,
            trajectory=list(self.trajectory),
            first_seen=self.first_seen,
            last_seen=self.last_seen,
            age_frames=self.age,
            speed=self.speed,
        )


class MultiObjectTracker:
    """ByteTrack-style tracker producing persistent IDs and trajectories."""

    def __init__(
        self,
        high_thresh: float = 0.5,
        low_thresh: float = 0.1,
        iou_match_thresh: float = 0.3,
        max_age: int = 30,
        min_hits: int = 3,
    ) -> None:
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        self.iou_match_thresh = iou_match_thresh
        self.max_age = max_age
        self.min_hits = min_hits
        self.tracks: List[_STrack] = []
        _STrack.reset_ids()

    # ------------------------------------------------------------------ #
    def _associate(self, tracks: List[_STrack], dets: List[Detection]
                   ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """IoU-based Hungarian association. Returns matches, unmatched_t, unmatched_d."""
        if not tracks or not dets:
            return [], list(range(len(tracks))), list(range(len(dets)))

        cost = np.zeros((len(tracks), len(dets)), dtype=float)
        for ti, t in enumerate(tracks):
            for di, d in enumerate(dets):
                cost[ti, di] = 1.0 - _iou(t.bbox, d.bbox)

        row_idx, col_idx = linear_sum_assignment(cost)
        matches, unmatched_t, unmatched_d = [], [], []
        matched_cols = set()
        for ti in range(len(tracks)):
            if ti not in row_idx:
                unmatched_t.append(ti)
        for r, c in zip(row_idx, col_idx):
            if cost[r, c] > 1.0 - self.iou_match_thresh:
                unmatched_t.append(r)
            else:
                matches.append((r, c))
                matched_cols.add(c)
        for di in range(len(dets)):
            if di not in matched_cols:
                unmatched_d.append(di)
        return matches, unmatched_t, unmatched_d

    def update(self, detections: List[Detection], fps: float = 25.0) -> List[Track]:
        """Advance the tracker by one frame and return confirmed tracks."""
        now = time.time()
        for t in self.tracks:
            t.predict()

        high = [d for d in detections if d.confidence >= self.high_thresh]
        low = [
            d for d in detections
            if self.low_thresh <= d.confidence < self.high_thresh
        ]

        # --- Stage 1: high-confidence association ---
        matches, un_t, un_d = self._associate(self.tracks, high)
        for ti, di in matches:
            self.tracks[ti].update(high[di], now, fps)

        # --- Stage 2: recover low-confidence detections on leftover tracks ---
        remaining_tracks = [self.tracks[i] for i in un_t]
        matches2, un_t2, _ = self._associate(remaining_tracks, low)
        for ti, di in matches2:
            remaining_tracks[ti].update(low[di], now, fps)
        still_unmatched = {id(remaining_tracks[i]) for i in un_t2}

        # --- Spawn new tracks from unmatched high-confidence detections ---
        for di in un_d:
            self.tracks.append(_STrack(high[di], now))

        # --- Cull dead tracks ---
        alive: List[_STrack] = []
        for t in self.tracks:
            if id(t) in still_unmatched and t.time_since_update > self.max_age:
                continue
            if t.time_since_update > self.max_age:
                continue
            alive.append(t)
        self.tracks = alive

        # --- Emit confirmed tracks ---
        confirmed = [
            t.to_track()
            for t in self.tracks
            if t.time_since_update == 0
            and (t.hits >= self.min_hits or t.age <= self.min_hits)
        ]
        return confirmed


def build_tracker() -> MultiObjectTracker:
    """Factory honouring the configured tracker (bytetrack-style default)."""
    # DeepSORT would add an appearance-embedding stage here; the ByteTrack-style
    # motion tracker is the robust, dependency-light default for SentinelAI.
    return MultiObjectTracker(
        high_thresh=max(0.4, settings.DETECTION_CONF_THRESHOLD),
    )
