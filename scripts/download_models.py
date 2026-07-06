"""
Pre-download YOLO weights into ./models so the first inference isn't delayed
(useful for baking into Docker images or air-gapped deployment prep).

Usage
-----
    python scripts/download_models.py --models yolov8n yolov8s
"""
from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download YOLO weights")
    p.add_argument("--models", nargs="+", default=["yolov8n"],
                   help="model stems, e.g. yolov8n yolov8s yolov8m")
    p.add_argument("--out", default="models")
    return p.parse_args()


def main() -> None:
    from ultralytics import YOLO

    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for stem in args.models:
        name = stem if stem.endswith(".pt") else f"{stem}.pt"
        print(f"Fetching {name} ...")
        YOLO(name)  # triggers Ultralytics download + cache
        print(f"  ready: {name}")
    print("Done. Set YOLO_MODEL in .env to the desired weight.")


if __name__ == "__main__":
    main()
