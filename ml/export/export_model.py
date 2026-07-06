"""
Export a trained YOLO model to a deployment format (ONNX / TensorRT / OpenVINO).

ONNX is portable (onnxruntime CPU/GPU); TensorRT gives the lowest latency on
NVIDIA hardware (including Jetson). Half-precision (--half) roughly halves the
engine size and boosts throughput on supported GPUs.

Usage
-----
    python export_model.py --weights best.pt --format onnx
    python export_model.py --weights best.pt --format engine --half   # TensorRT
"""
from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export a YOLO model")
    p.add_argument("--weights", required=True)
    p.add_argument("--format", default="onnx",
                   choices=["onnx", "engine", "openvino", "torchscript", "coreml"])
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--half", action="store_true", help="FP16 export")
    p.add_argument("--dynamic", action="store_true", help="dynamic input shapes")
    p.add_argument("--simplify", action="store_true", help="simplify ONNX graph")
    return p.parse_args()


def main() -> None:
    from ultralytics import YOLO

    args = parse_args()
    model = YOLO(args.weights)
    path = model.export(
        format=args.format,
        imgsz=args.imgsz,
        half=args.half,
        dynamic=args.dynamic,
        simplify=args.simplify,
    )
    print(f"\nExported model -> {path}")
    print("Point the backend at it via YOLO_MODEL in your .env.")


if __name__ == "__main__":
    main()
