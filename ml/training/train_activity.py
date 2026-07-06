"""
Train the 3D-CNN (R3D-18) human-activity recognizer on short video clips.

Expected dataset layout (one folder per class of .mp4/.avi clips):
    <data>/walking/*.mp4
    <data>/running/*.mp4
    <data>/fighting/*.mp4
    ...

Uses transfer learning from Kinetics-pretrained R3D-18 weights.

Usage
-----
    python train_activity.py --data /data/activity_clips --epochs 40
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision.models.video import R3D_18_Weights, r3d_18

VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}


class ClipDataset(Dataset):
    def __init__(self, root: str, clip_len: int = 16, img_size: int = 112) -> None:
        self.clip_len = clip_len
        self.img_size = img_size
        self.classes = sorted(
            d.name for d in Path(root).iterdir() if d.is_dir()
        )
        self.cls_to_idx = {c: i for i, c in enumerate(self.classes)}
        self.samples: list[tuple[Path, int]] = []
        for c in self.classes:
            for clip in (Path(root) / c).rglob("*"):
                if clip.suffix.lower() in VIDEO_EXTS:
                    self.samples.append((clip, self.cls_to_idx[c]))
        if not self.samples:
            raise SystemExit(f"No clips found under {root}")

    def __len__(self) -> int:
        return len(self.samples)

    def _read_clip(self, path: Path) -> np.ndarray:
        cap = cv2.VideoCapture(str(path))
        frames = []
        while len(frames) < self.clip_len:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.resize(frame, (self.img_size, self.img_size))
            frames.append(frame[:, :, ::-1] / 255.0)
        cap.release()
        # Pad by repeating the last frame if the clip is short.
        while len(frames) < self.clip_len:
            frames.append(frames[-1] if frames else np.zeros(
                (self.img_size, self.img_size, 3)))
        clip = np.stack(frames[: self.clip_len], axis=0)  # (T,H,W,C)
        return np.transpose(clip, (3, 0, 1, 2)).astype(np.float32)  # (C,T,H,W)

    def __getitem__(self, idx: int):
        path, label = self.samples[idx]
        return torch.from_numpy(self._read_clip(path)), label


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train R3D-18 activity recognizer")
    p.add_argument("--data", required=True)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--batch", type=int, default=8)
    p.add_argument("--lr", type=float, default=5e-4)
    p.add_argument("--out", default="models/activity_r3d18.pt")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    ds = ClipDataset(args.data)
    print(f"Classes: {ds.classes}")
    dl = DataLoader(ds, batch_size=args.batch, shuffle=True, num_workers=2)

    model = r3d_18(weights=R3D_18_Weights.KINETICS400_V1)
    model.fc = nn.Linear(model.fc.in_features, len(ds.classes))
    model = model.to(device)

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    loss_fn = nn.CrossEntropyLoss()

    for epoch in range(1, args.epochs + 1):
        model.train()
        total, correct, seen = 0.0, 0, 0
        for clips, labels in dl:
            clips, labels = clips.to(device), labels.to(device)
            opt.zero_grad()
            logits = model(clips)
            loss = loss_fn(logits, labels)
            loss.backward()
            opt.step()
            total += loss.item() * clips.size(0)
            correct += (logits.argmax(1) == labels).sum().item()
            seen += clips.size(0)
        print(f"Epoch {epoch:>3}/{args.epochs}  loss={total/seen:.4f}  acc={correct/seen:.3f}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), out)
    print(f"\nSaved activity model -> {out}")


if __name__ == "__main__":
    main()
