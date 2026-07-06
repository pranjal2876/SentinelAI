"""
Prepare / verify a YOLO-format detection dataset.

* Splits a flat image+label directory into train/val/test.
* Verifies every image has a matching label and that label values are
  normalized in [0,1].
* Writes a summary of class distribution.

Usage
-----
    python prepare_yolo_dataset.py --src /data/raw --out /data/yolo \
        --val 0.15 --test 0.05
"""
from __future__ import annotations

import argparse
import random
import shutil
from collections import Counter
from pathlib import Path

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare a YOLO detection dataset")
    p.add_argument("--src", required=True, help="dir with images/ and labels/")
    p.add_argument("--out", required=True, help="output dataset root")
    p.add_argument("--val", type=float, default=0.15)
    p.add_argument("--test", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def verify_label(label_path: Path) -> list[int]:
    """Return the list of class ids in a label file, raising on bad values."""
    classes: list[int] = []
    if not label_path.exists():
        return classes
    for line in label_path.read_text().strip().splitlines():
        parts = line.split()
        if len(parts) != 5:
            raise ValueError(f"Malformed line in {label_path}: '{line}'")
        cls, *coords = parts
        for c in coords:
            v = float(c)
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"Un-normalized coord {v} in {label_path}")
        classes.append(int(cls))
    return classes


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    src = Path(args.src)
    out = Path(args.out)

    images = [p for p in (src / "images").rglob("*") if p.suffix.lower() in IMG_EXTS]
    if not images:
        raise SystemExit(f"No images found under {src / 'images'}")
    random.shuffle(images)

    n = len(images)
    n_val = int(n * args.val)
    n_test = int(n * args.test)
    splits = {
        "val": images[:n_val],
        "test": images[n_val:n_val + n_test],
        "train": images[n_val + n_test:],
    }

    class_counter: Counter = Counter()
    for split, files in splits.items():
        if not files:
            continue
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)
        for img in files:
            label = (src / "labels" / img.relative_to(src / "images")).with_suffix(".txt")
            class_counter.update(verify_label(label))
            shutil.copy2(img, out / "images" / split / img.name)
            if label.exists():
                shutil.copy2(label, out / "labels" / split / label.name)
        print(f"[{split}] {len(files)} images")

    print("\nClass distribution:")
    for cls, count in sorted(class_counter.items()):
        print(f"  class {cls}: {count} boxes")
    print(f"\nDataset written to {out}")


if __name__ == "__main__":
    main()
