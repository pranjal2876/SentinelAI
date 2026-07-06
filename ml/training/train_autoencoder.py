"""
Train the convolutional autoencoder for video-frame anomaly detection.

Trained on frames of *normal* activity only; at inference, frames with high
reconstruction error are flagged as anomalous. Saves the checkpoint and the
99th-percentile error threshold computed on a held-out split.

Usage
-----
    python train_autoencoder.py --frames /data/normal_frames --epochs 30
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

# Re-use the model definition from the backend package.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.vision.anomaly.autoencoder import ConvAutoencoder  # noqa: E402

IMG_EXTS = {".jpg", ".jpeg", ".png"}


class FrameDataset(Dataset):
    def __init__(self, root: str, img_size: int = 64) -> None:
        self.paths = [p for p in Path(root).rglob("*") if p.suffix.lower() in IMG_EXTS]
        self.img_size = img_size
        if not self.paths:
            raise SystemExit(f"No frames found under {root}")

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, idx: int) -> torch.Tensor:
        img = cv2.imread(str(self.paths[idx]), cv2.IMREAD_GRAYSCALE)
        img = cv2.resize(img, (self.img_size, self.img_size)).astype(np.float32) / 255.0
        return torch.from_numpy(img).unsqueeze(0)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train anomaly autoencoder")
    p.add_argument("--frames", required=True)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--batch", type=int, default=64)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--out", default="models/anomaly_ae.pt")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    ds = FrameDataset(args.frames)
    n_val = max(1, int(len(ds) * 0.1))
    train_ds, val_ds = torch.utils.data.random_split(ds, [len(ds) - n_val, n_val])
    train_dl = DataLoader(train_ds, batch_size=args.batch, shuffle=True)
    val_dl = DataLoader(val_ds, batch_size=args.batch)

    model = ConvAutoencoder().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = torch.nn.MSELoss()

    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0.0
        for x in train_dl:
            x = x.to(device)
            opt.zero_grad()
            loss = loss_fn(model(x), x)
            loss.backward()
            opt.step()
            total += loss.item() * x.size(0)
        print(f"Epoch {epoch:>3}/{args.epochs}  train_mse={total / len(train_ds):.5f}")

    # Compute anomaly threshold on validation frames.
    model.eval()
    errors = []
    with torch.no_grad():
        for x in val_dl:
            x = x.to(device)
            recon = model(x)
            per = ((recon - x) ** 2).mean(dim=[1, 2, 3])
            errors.extend(per.cpu().tolist())
    threshold = float(np.percentile(errors, 99))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), out)
    (out.with_suffix(".meta.json")).write_text(
        json.dumps({"threshold": threshold, "img_size": 64}, indent=2)
    )
    print(f"\nSaved model -> {out}")
    print(f"Anomaly threshold (p99): {threshold:.5f}")


if __name__ == "__main__":
    main()
