"""
Occupancy heatmap accumulator.

Accumulates tracked foot-points into a float32 buffer, applies temporal decay
so the map reflects recent activity, and renders a colorized overlay. Used both
for the live dashboard heatmap panel and for stored analytics snapshots.
"""
from __future__ import annotations

from typing import List, Optional

import cv2
import numpy as np

from app.vision.types import Track


class HeatmapAccumulator:
    """Rolling occupancy heatmap for one camera."""

    def __init__(self, width: int, height: int, decay: float = 0.995,
                 sigma: int = 25) -> None:
        self.width = width
        self.height = height
        self.decay = decay
        self.sigma = sigma
        self.buffer = np.zeros((height, width), dtype=np.float32)

    def update(self, tracks: List[Track]) -> None:
        self.buffer *= self.decay
        for t in tracks:
            fx, fy = t.foot_point
            x, y = int(fx), int(fy)
            if 0 <= x < self.width and 0 <= y < self.height:
                self.buffer[y, x] += 1.0
        # Periodic light blur keeps the map smooth without doing it every frame.

    def render(self, base_frame: Optional[np.ndarray] = None,
               alpha: float = 0.5) -> np.ndarray:
        blurred = cv2.GaussianBlur(self.buffer, (0, 0), self.sigma)
        norm = blurred / (blurred.max() + 1e-6)
        colored = cv2.applyColorMap(np.uint8(255 * norm), cv2.COLORMAP_JET)
        if base_frame is not None:
            base = cv2.resize(base_frame, (self.width, self.height))
            return cv2.addWeighted(colored, alpha, base, 1 - alpha, 0)
        return colored

    def save(self, path: str, base_frame: Optional[np.ndarray] = None) -> None:
        cv2.imwrite(path, self.render(base_frame))
