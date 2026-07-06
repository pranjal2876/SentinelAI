"""
Camera capture workers and the camera manager.

Each `CameraWorker` runs in its own thread: it opens the video source (webcam
index, RTSP URL, or file path), reads frames with automatic reconnection, runs
the `SurveillancePipeline`, publishes threats through the `event_bus`, and keeps
the latest annotated JPEG for MJPEG / WebSocket streaming.

`CameraManager` owns all workers and a single shared `ObjectDetector` (the
heaviest resource), exposing lifecycle and frame-access methods to the API.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import cv2
import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.services.event_bus import event_bus
from app.vision.detection import ObjectDetector
from app.vision.pipeline import SurveillancePipeline
from app.vision.threat import Zone


def _parse_source(source: str):
    """Return an int for webcam indices, else the original string."""
    return int(source) if source.isdigit() else source


@dataclass
class CameraRuntime:
    camera_id: str
    name: str
    source: str
    status: str = "offline"
    fps: float = 0.0
    last_frame_ts: float = 0.0
    error: Optional[str] = None


class CameraWorker(threading.Thread):
    """Threaded frame-grabber + inference loop for one camera."""

    def __init__(
        self,
        camera_id: str,
        name: str,
        source: str,
        detector: ObjectDetector,
        zones: Optional[List[Zone]] = None,
    ) -> None:
        super().__init__(daemon=True, name=f"cam-{camera_id}")
        self.camera_id = camera_id
        self.runtime = CameraRuntime(camera_id, name, source)
        self.pipeline = SurveillancePipeline(camera_id, detector=detector, zones=zones)
        self._stop = threading.Event()
        self._latest_jpeg: Optional[bytes] = None
        self._lock = threading.Lock()
        self._reconnect_delay = 2.0

    # -- lifecycle ---------------------------------------------------- #
    def stop(self) -> None:
        self._stop.set()

    def update_zones(self, zones: List[Zone]) -> None:
        self.pipeline.set_zones(zones)

    # -- frame access ------------------------------------------------- #
    def latest_jpeg(self) -> Optional[bytes]:
        with self._lock:
            return self._latest_jpeg

    def heatmap_jpeg(self) -> Optional[bytes]:
        img = self.pipeline.render_heatmap()
        if img is None:
            return None
        ok, buf = cv2.imencode(".jpg", img)
        return buf.tobytes() if ok else None

    # -- main loop ---------------------------------------------------- #
    def _open(self) -> Optional[cv2.VideoCapture]:
        self.runtime.status = "connecting"
        cap = cv2.VideoCapture(_parse_source(self.runtime.source))
        # Keep buffer small for low latency on live streams.
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not cap.isOpened():
            self.runtime.status = "error"
            self.runtime.error = "Could not open source"
            logger.error(f"[{self.camera_id}] cannot open source "
                         f"'{self.runtime.source}'")
            return None
        self.runtime.status = "online"
        self.runtime.error = None
        logger.success(f"[{self.camera_id}] stream opened.")
        return cap

    def run(self) -> None:  # noqa: C901
        cap = self._open()
        stride = max(1, settings.FRAME_STRIDE)
        min_dt = 1.0 / max(settings.MAX_INFERENCE_FPS, 1)
        frame_no = 0

        while not self._stop.is_set():
            if cap is None or not cap.isOpened():
                time.sleep(self._reconnect_delay)
                cap = self._open()
                continue

            t0 = time.time()
            ok, frame = cap.read()
            if not ok or frame is None:
                # File ended -> loop; live stream -> reconnect.
                if str(self.runtime.source).isdigit() or "://" in str(self.runtime.source):
                    self.runtime.status = "offline"
                    cap.release()
                    cap = None
                    continue
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # loop video files
                continue

            frame_no += 1
            if frame_no % stride != 0:
                continue

            try:
                result = self.pipeline.process(frame)
            except Exception as exc:  # pragma: no cover
                logger.exception(f"[{self.camera_id}] pipeline error: {exc}")
                continue

            self.runtime.fps = result.fps
            self.runtime.last_frame_ts = result.timestamp

            annotated = result.annotated_frame if result.annotated_frame is not None else frame
            ok_enc, buf = cv2.imencode(".jpg", annotated,
                                       [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if ok_enc:
                with self._lock:
                    self._latest_jpeg = buf.tobytes()

            # Publish threats (with the annotated snapshot).
            for threat in result.threats:
                event_bus.publish_threat(threat, annotated)

            # Throttle to the configured max FPS.
            elapsed = time.time() - t0
            if elapsed < min_dt:
                time.sleep(min_dt - elapsed)

        if cap is not None:
            cap.release()
        self.runtime.status = "offline"
        logger.info(f"[{self.camera_id}] worker stopped.")


class CameraManager:
    """Owns all camera workers and the shared detector."""

    def __init__(self) -> None:
        self._workers: Dict[str, CameraWorker] = {}
        self._detector: Optional[ObjectDetector] = None
        self._lock = threading.Lock()

    @property
    def detector(self) -> ObjectDetector:
        if self._detector is None:
            self._detector = ObjectDetector()
        return self._detector

    def start_camera(self, camera_id: str, name: str, source: str,
                     zones: Optional[List[Zone]] = None) -> None:
        with self._lock:
            if camera_id in self._workers:
                logger.warning(f"Camera {camera_id} already running.")
                return
            worker = CameraWorker(camera_id, name, source, self.detector, zones)
            self._workers[camera_id] = worker
            worker.start()
            logger.info(f"Started camera worker '{camera_id}'.")

    def stop_camera(self, camera_id: str) -> None:
        with self._lock:
            worker = self._workers.pop(camera_id, None)
        if worker:
            worker.stop()
            worker.join(timeout=5)

    def stop_all(self) -> None:
        for cid in list(self._workers):
            self.stop_camera(cid)

    def get(self, camera_id: str) -> Optional[CameraWorker]:
        return self._workers.get(camera_id)

    def runtimes(self) -> List[CameraRuntime]:
        return [w.runtime for w in self._workers.values()]

    def update_zones(self, camera_id: str, zones: List[Zone]) -> bool:
        w = self._workers.get(camera_id)
        if w:
            w.update_zones(zones)
            return True
        return False


# Global singleton manager.
camera_manager = CameraManager()
