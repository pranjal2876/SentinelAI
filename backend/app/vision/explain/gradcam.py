"""
Explainable AI utilities.

* `GradCAM` — gradient-weighted class-activation mapping for CNN backbones,
  producing a heatmap that highlights the image regions most responsible for a
  prediction. Works with any torch model exposing a convolutional target layer.

* `explain_threat` — a model-agnostic, human-readable rationale generator that
  turns a `ThreatEvent` plus its contributing evidence into a structured
  explanation (why it fired, the numeric factors, and the confidence).
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from app.vision.types import ThreatEvent


class GradCAM:
    """Grad-CAM for a single convolutional target layer."""

    def __init__(self, model, target_layer) -> None:
        self.model = model
        self.target_layer = target_layer
        self._activations = None
        self._gradients = None
        target_layer.register_forward_hook(self._save_activation)
        target_layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, _m, _i, output):
        self._activations = output.detach()

    def _save_gradient(self, _m, _gi, grad_output):
        self._gradients = grad_output[0].detach()

    def __call__(self, input_tensor, class_idx: Optional[int] = None) -> np.ndarray:
        import torch

        self.model.zero_grad()
        logits = self.model(input_tensor)
        if class_idx is None:
            class_idx = int(torch.argmax(logits, dim=1)[0])
        logits[0, class_idx].backward(retain_graph=True)

        grads = self._gradients          # (B, C, H, W)
        acts = self._activations
        weights = grads.mean(dim=(2, 3), keepdim=True)
        cam = torch.relu((weights * acts).sum(dim=1)).squeeze(0)
        cam = cam.cpu().numpy()
        cam -= cam.min()
        cam /= (cam.max() + 1e-9)
        return cam

    @staticmethod
    def overlay(cam: np.ndarray, frame_bgr: np.ndarray, alpha: float = 0.45
                ) -> np.ndarray:
        """Blend a CAM heatmap over the original frame."""
        import cv2

        h, w = frame_bgr.shape[:2]
        cam_resized = cv2.resize(cam, (w, h))
        heat = cv2.applyColorMap(np.uint8(255 * cam_resized), cv2.COLORMAP_JET)
        return cv2.addWeighted(heat, alpha, frame_bgr, 1 - alpha, 0)


# --------------------------------------------------------------------------- #
# Rule-level explanation (always available, no model required)
# --------------------------------------------------------------------------- #
_RULE_RATIONALE: Dict[str, str] = {
    "intrusion": "A person's ground position fell inside a user-defined "
                 "restricted polygon.",
    "loitering": "A person remained within a small area beyond the dwell-time "
                 "threshold while nearly stationary.",
    "abandoned_object": "A carriable object (bag/backpack/suitcase) stayed "
                        "static with no person nearby beyond the timeout.",
    "crowd": "The number of simultaneously tracked people exceeded the crowd "
             "threshold within a compact region.",
    "running": "A person's smoothed foot-point speed exceeded the running "
               "speed threshold.",
    "wrong_direction": "A track's motion vector opposed the corridor's allowed "
                       "direction (cosine < -0.5).",
    "vehicle_in_zone": "A vehicle's ground position entered a vehicle-excluded "
                       "or restricted zone.",
    "multiple_intruders": "Two or more people were simultaneously inside a "
                          "restricted zone.",
    "camera_tampering": "Frame statistics indicated defocus, occlusion, or a "
                        "sudden scene change persisting over many frames.",
    "anomaly": "An IsolationForest over scene motion features scored this frame "
               "far from the learned normal distribution.",
    "fire_smoke": "A fire/smoke classifier exceeded its detection threshold.",
    "violence": "A clip-level activity model classified the interaction as "
                "violent.",
    "fall": "A person's bounding box rapidly transitioned to a horizontal "
            "aspect ratio consistent with a fall.",
}


def explain_threat(event: ThreatEvent) -> Dict[str, object]:
    """Produce a structured, human-readable explanation of a threat event."""
    rationale = _RULE_RATIONALE.get(event.category.value, "Rule fired.")
    factors: List[Dict[str, object]] = []
    for k, v in event.metadata.items():
        factors.append({"factor": k, "value": v})
    return {
        "category": event.category.value,
        "severity": event.severity.value,
        "confidence": round(event.score, 3),
        "why": rationale,
        "message": event.message,
        "contributing_factors": factors,
        "tracks_involved": event.track_ids,
    }
