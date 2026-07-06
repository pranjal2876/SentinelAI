"""
Standalone local runner — process a single video source through the full
SurveillancePipeline and display the annotated output in a window. Handy for
demos and debugging without the API/DB stack.

Usage
-----
    python run_local.py --source 0                 # webcam
    python run_local.py --source path/to/video.mp4
    python run_local.py --source rtsp://user:pass@ip:554/stream
"""
from __future__ import annotations

import argparse
import sys
import time

import cv2

# Allow running from the backend/ directory.
sys.path.insert(0, ".")

from app.core.logging import setup_logging  # noqa: E402
from app.vision.pipeline import SurveillancePipeline  # noqa: E402
from app.vision.threat import Zone, ZoneType  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SentinelAI local pipeline runner")
    p.add_argument("--source", default="0", help="webcam index, file path, or RTSP URL")
    p.add_argument("--camera-id", default="local-cam")
    p.add_argument("--no-display", action="store_true", help="run headless")
    p.add_argument("--demo-zone", action="store_true",
                   help="add a demo restricted zone in the frame center")
    return p.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    source = int(args.source) if args.source.isdigit() else args.source

    zones = []
    if args.demo_zone:
        zones.append(Zone(
            id="demo", name="Restricted", type=ZoneType.RESTRICTED,
            points=[(0.35, 0.35), (0.65, 0.35), (0.65, 0.75), (0.35, 0.75)],
        ))

    pipeline = SurveillancePipeline(args.camera_id, zones=zones)
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"ERROR: cannot open source '{source}'")
        return

    print("Running SentinelAI pipeline. Press 'q' to quit.")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        result = pipeline.process(frame)
        for t in result.threats:
            print(f"[{time.strftime('%H:%M:%S')}] THREAT {t.severity.value.upper()}: "
                  f"{t.category.value} — {t.message}")
        if not args.no_display and result.annotated_frame is not None:
            cv2.imshow("SentinelAI", result.annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
