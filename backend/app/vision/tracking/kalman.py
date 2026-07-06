"""
Constant-velocity Kalman filter for 2D bounding-box tracking.

State vector: [cx, cy, a, h, vcx, vcy, va, vh]
    cx, cy : box center
    a      : aspect ratio (w / h)
    h      : height
    v*     : respective velocities

This is the classic SORT/DeepSORT motion model, implemented with NumPy so it
carries no heavy dependency and runs comfortably in real time.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np


class KalmanBoxTracker:
    """Kalman filter tracking a single bounding box in image space."""

    def __init__(self, bbox_xyxy: Tuple[float, float, float, float]) -> None:
        ndim, dt = 4, 1.0

        # State transition (constant velocity) and observation matrices.
        self._F = np.eye(2 * ndim)
        for i in range(ndim):
            self._F[i, ndim + i] = dt
        self._H = np.eye(ndim, 2 * ndim)

        # Uncertainty weights (as in DeepSORT).
        self._std_weight_position = 1.0 / 20
        self._std_weight_velocity = 1.0 / 160

        measurement = self._xyxy_to_xyah(bbox_xyxy)
        self.mean = np.r_[measurement, np.zeros(ndim)]
        std = np.array([
            2 * self._std_weight_position * measurement[3],
            2 * self._std_weight_position * measurement[3],
            1e-2,
            2 * self._std_weight_position * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            1e-5,
            10 * self._std_weight_velocity * measurement[3],
        ])
        self.covariance = np.diag(np.square(std))

    # ------------------------------------------------------------------ #
    @staticmethod
    def _xyxy_to_xyah(b: Tuple[float, float, float, float]) -> np.ndarray:
        x1, y1, x2, y2 = b
        w, h = x2 - x1, y2 - y1
        cx, cy = x1 + w / 2.0, y1 + h / 2.0
        a = w / h if h > 0 else 0.0
        return np.array([cx, cy, a, h], dtype=float)

    @staticmethod
    def _xyah_to_xyxy(m: np.ndarray) -> Tuple[float, float, float, float]:
        cx, cy, a, h = m[:4]
        w = a * h
        return (cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0)

    # ------------------------------------------------------------------ #
    def predict(self) -> None:
        """Advance the state by one time step."""
        std_pos = [
            self._std_weight_position * self.mean[3],
            self._std_weight_position * self.mean[3],
            1e-2,
            self._std_weight_position * self.mean[3],
        ]
        std_vel = [
            self._std_weight_velocity * self.mean[3],
            self._std_weight_velocity * self.mean[3],
            1e-5,
            self._std_weight_velocity * self.mean[3],
        ]
        motion_cov = np.diag(np.square(np.r_[std_pos, std_vel]))
        self.mean = self._F @ self.mean
        self.covariance = self._F @ self.covariance @ self._F.T + motion_cov

    def update(self, bbox_xyxy: Tuple[float, float, float, float]) -> None:
        """Correct the state with a new measurement."""
        measurement = self._xyxy_to_xyah(bbox_xyxy)
        std = [
            self._std_weight_position * self.mean[3],
            self._std_weight_position * self.mean[3],
            1e-1,
            self._std_weight_position * self.mean[3],
        ]
        innovation_cov = np.diag(np.square(std))
        projected_mean = self._H @ self.mean
        projected_cov = self._H @ self.covariance @ self._H.T + innovation_cov

        kalman_gain = (
            self.covariance @ self._H.T @ np.linalg.inv(projected_cov)
        )
        innovation = measurement - projected_mean
        self.mean = self.mean + kalman_gain @ innovation
        self.covariance = (
            self.covariance - kalman_gain @ projected_cov @ kalman_gain.T
        )

    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        return self._xyah_to_xyxy(self.mean)
