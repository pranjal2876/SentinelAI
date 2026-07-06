"""
SurveillancePipeline — the per-camera orchestration of the full vision stack.

For each incoming frame it runs:
    detect -> track -> heatmap -> threat rules -> motion anomaly
    -> camera tampering -> activity recognition -> annotate

It is deliberately synchronous and single-camera; concurrency across cameras is
handled one level up by `CameraWorker` threads (see services/camera.py), which
keeps each pipeline's stateful detectors isolated and lock-free.
"""
from __future__ import annotations

import time
from typing import List, Optional

import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.vision.activity import HeuristicActivityRecognizer
from app.vision.annotate import annotate_frame
from app.vision.anomaly import MotionAnomalyDetector
from app.vision.detection import ObjectDetector
from app.vision.heatmap import HeatmapAccumulator
from app.vision.tampering import TamperingDetector
from app.vision.threat import ThreatEngine, Zone
from app.vision.tracking.tracker import build_tracker
from app.vision.types import Detection, FrameResult, Track


class SurveillancePipeline:
    """End-to-end vision pipeline for a single camera stream."""

    def __init__(
        self,
        camera_id: str,
        detector: Optional[ObjectDetector] = None,
        zones: Optional[List[Zone]] = None,
        enable_anomaly: bool = True,
        enable_tampering: bool = True,
        enable_activity: bool = True,
        annotate: bool = True,
    ) -> None:
        self.camera_id = camera_id
        # The detector is heavy; allow sharing one instance across pipelines.
        self.detector = detector or ObjectDetector()
        self.tracker = build_tracker()
        self.threat_engine = ThreatEngine(camera_id, zones=zones)
        self.anomaly = MotionAnomalyDetector(camera_id) if enable_anomaly else None
        self.tampering = TamperingDetector(camera_id) if enable_tampering else None
        self.activity = HeuristicActivityRecognizer() if enable_activity else None
        self.annotate = annotate

        self._heatmap: Optional[HeatmapAccumulator] = None
        self._frame_index = 0
        self._last_ts = time.time()
        self._fps = 0.0

    @property
    def zones(self) -> List[Zone]:
        return self.threat_engine.zones

    def set_zones(self, zones: List[Zone]) -> None:
        self.threat_engine.zones = zones

    def _update_fps(self) -> None:
        now = time.time()
        dt = now - self._last_ts
        if dt > 0:
            inst = 1.0 / dt
            self._fps = 0.9 * self._fps + 0.1 * inst if self._fps else inst
        self._last_ts = now

    def process(self, frame: np.ndarray) -> FrameResult:
        """Process one BGR frame end-to-end and return a `FrameResult`."""
        self._update_fps()
        self._frame_index += 1
        now = time.time()
        h, w = frame.shape[:2]

        if self._heatmap is None:
            self._heatmap = HeatmapAccumulator(w, h)

        # 1. Detection
        detections: List[Detection] = self.detector.detect(frame)

        # 2. Tracking
        tracks: List[Track] = self.tracker.update(detections, fps=max(self._fps, 1.0))

        # 3. Heatmap accumulation
        self._heatmap.update(tracks)

        # 4. Threat rules
        threats = self.threat_engine.evaluate(tracks, (h, w), now=now)

        # 5. Motion anomaly
        if self.anomaly is not None:
            anom = self.anomaly.update(tracks, now=now)
            if anom is not None:
                threats.append(anom)

        # 6. Camera tampering (frame-level)
        if self.tampering is not None:
            tamper = self.tampering.update(frame, now=now)
            if tamper is not None:
                threats.append(tamper)

        # 7. Activity recognition (attach as metadata on threats + result)
        activities = self.activity.recognise(tracks) if self.activity else []
        for th in threats:
            for act in activities:
                if act.track_id in th.track_ids and act.label in (
                    "falling", "fighting", "violence"
                ):
                    th.metadata["activity"] = act.label

        # 8. Annotation
        annotated = None
        if self.annotate:
            annotated = annotate_frame(frame, tracks, threats, self.zones, self._fps)

        if threats:
            logger.info(f"[{self.camera_id}] {len(threats)} threat(s): "
                        + ", ".join(t.category.value for t in threats))

        return FrameResult(
            camera_id=self.camera_id,
            frame_index=self._frame_index,
            timestamp=now,
            detections=detections,
            tracks=tracks,
            threats=threats,
            fps=self._fps,
            annotated_frame=annotated,
        )

    def render_heatmap(self, base_frame: Optional[np.ndarray] = None) -> Optional[np.ndarray]:
        return self._heatmap.render(base_frame) if self._heatmap else None

    @property
    def counting_stats(self):
        return self.threat_engine.counting
