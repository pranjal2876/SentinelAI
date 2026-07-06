"""
Evaluate a trained YOLO model — mAP, per-class precision/recall, speed.

Usage
-----
    python evaluate_yolo.py --weights best.pt --data ../configs/surveillance.yaml
"""
from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate a YOLO model")
    p.add_argument("--weights", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--device", default="")
    p.add_argument("--split", default="val", choices=["val", "test"])
    return p.parse_args()


def main() -> None:
    from ultralytics import YOLO

    args = parse_args()
    model = YOLO(args.weights)
    metrics = model.val(
        data=args.data, imgsz=args.imgsz,
        device=args.device or None, split=args.split, plots=True,
    )

    print("\n===== Evaluation Summary =====")
    print(f"mAP50    : {metrics.box.map50:.4f}")
    print(f"mAP50-95 : {metrics.box.map:.4f}")
    print(f"Precision: {metrics.box.mp:.4f}")
    print(f"Recall   : {metrics.box.mr:.4f}")

    names = model.names
    print("\nPer-class mAP50-95:")
    for i, ap in enumerate(metrics.box.maps):
        print(f"  {names.get(i, i):<14} {ap:.4f}")


if __name__ == "__main__":
    main()
