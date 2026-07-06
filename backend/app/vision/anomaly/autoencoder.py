"""
Convolutional autoencoder for video-frame anomaly detection (offline / training).

The reconstruction error of a frame that differs strongly from the learned
"normal" distribution is high; thresholding this error flags anomalies. This
module defines the model plus helpers to compute a normalized anomaly score.
Train it with `ml/training/train_autoencoder.py`.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np

try:
    import torch
    import torch.nn as nn
    _TORCH = True
except Exception:  # pragma: no cover
    _TORCH = False


if _TORCH:

    class ConvAutoencoder(nn.Module):
        """A compact conv autoencoder for 64x64 grayscale frame patches."""

        def __init__(self, latent_dim: int = 128) -> None:
            super().__init__()
            self.encoder = nn.Sequential(
                nn.Conv2d(1, 32, 3, stride=2, padding=1), nn.ReLU(True),   # 32x32
                nn.Conv2d(32, 64, 3, stride=2, padding=1), nn.ReLU(True),  # 16x16
                nn.Conv2d(64, 128, 3, stride=2, padding=1), nn.ReLU(True), # 8x8
                nn.Flatten(),
                nn.Linear(128 * 8 * 8, latent_dim), nn.ReLU(True),
            )
            self.decoder_fc = nn.Linear(latent_dim, 128 * 8 * 8)
            self.decoder = nn.Sequential(
                nn.ConvTranspose2d(128, 64, 3, stride=2, padding=1, output_padding=1),
                nn.ReLU(True),
                nn.ConvTranspose2d(64, 32, 3, stride=2, padding=1, output_padding=1),
                nn.ReLU(True),
                nn.ConvTranspose2d(32, 1, 3, stride=2, padding=1, output_padding=1),
                nn.Sigmoid(),
            )

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            z = self.encoder(x)
            z = self.decoder_fc(z).view(-1, 128, 8, 8)
            return self.decoder(z)

    @torch.no_grad()
    def reconstruction_error(model: "ConvAutoencoder", frame_gray: np.ndarray,
                             device: str = "cpu") -> float:
        """Return MSE reconstruction error for a single grayscale frame."""
        import cv2

        patch = cv2.resize(frame_gray, (64, 64)).astype(np.float32) / 255.0
        x = torch.from_numpy(patch).unsqueeze(0).unsqueeze(0).to(device)
        recon = model(x)
        return float(((recon - x) ** 2).mean().item())

else:  # pragma: no cover
    ConvAutoencoder = None  # type: ignore

    def reconstruction_error(*_args, **_kwargs) -> float:
        raise RuntimeError("PyTorch is not installed; autoencoder unavailable.")
