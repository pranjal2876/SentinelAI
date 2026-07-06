"""
Fine-tune YOLOv8 on SentinelAI surveillance classes (transfer learning).

Starts from a COCO-pretrained checkpoint and adapts to the surveillance dataset
defined by a YOLO data YAML. Supports GPU or CPU and logs to TensorBoard via
Ultralytics.

Usage
-----
    python train_yolo.py --data ../configs/surveillance.yaml \
        --model yolov8s.pt --epochs 100 --imgsz 640 --batch 16
"""
from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fine-tune YOLOv8 for surveillance")
    p.add_argument("--data", required=True, help="YOLO data YAML")
    p.add_argument("--model", default="yolov8s.pt", help="pretrained checkpoint")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--device", default="", help="'0' for GPU, 'cpu', or '' for auto")
    p.add_argument("--project", default="runs/detect")
    p.add_argument("--name", default="sentinel_yolo")
    p.add_argument("--patience", type=int, default=30)
    p.add_argument("--resume", action="store_true")
    return p.parse_args()


def main() -> None:
    from ultralytics import YOLO

    args = parse_args()
    print(f"Loading pretrained model: {args.model}")
    model = YOLO(args.model)

    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device or None,
        project=args.project,
        name=args.name,
        patience=args.patience,
        resume=args.resume,
        # Augmentation for robustness to lighting / viewpoint.
        hsv_h=0.015, hsv_s=0.7, hsv_v=0.4,
        mosaic=1.0, mixup=0.1, degrees=5.0, translate=0.1, scale=0.5,
        plots=True,
        verbose=True,
    )
    best = Path(args.project) / args.name / "weights" / "best.pt"
    print(f"\nTraining complete. Best weights: {best}")
    print(f"mAP50-95: {getattr(results, 'box', None)}")


if __name__ == "__main__":
    main()
