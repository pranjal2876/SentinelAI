# SentinelAI — Model Documentation

## 1. Object detection — YOLOv8

* **Backbone**: Ultralytics YOLOv8 (n/s/m/l/x). Default `yolov8n.pt` (CPU-friendly);
  use `s`/`m` on GPU for higher accuracy.
* **Classes used** (COCO subset + optional custom): person, bicycle, car,
  motorcycle, bus, truck, backpack, handbag, suitcase, (optional) weapon.
* **Transfer learning**: fine-tune from COCO weights on a labelled surveillance
  set with `ml/training/train_yolo.py`.
* **Inputs**: BGR frames, letterboxed to `imgsz` (default 640).
* **Outputs**: boxes (xyxy), class ids, confidences → filtered to the allow-list.

### Suggested datasets
- COCO (person/vehicle/bag baseline)
- VisDrone / UA-DETRAC (aerial + traffic)
- Domain footage from the target site (best results; label with CVAT/Roboflow)
- For weapons: publicly available weapon-detection datasets (verify licensing)

### Benchmarks (fill in after training)
| Model | imgsz | mAP50 | mAP50-95 | FPS (GPU) | FPS (CPU) |
|---|---|---|---|---|---|
| yolov8n | 640 | — | — | — | — |
| yolov8s | 640 | — | — | — | — |

## 2. Multi-object tracking — ByteTrack-style

* Constant-velocity **Kalman filter** per target (`vision/tracking/kalman.py`).
* **Two-stage IoU association** (high- then low-confidence detections) via the
  Hungarian algorithm (`scipy.optimize.linear_sum_assignment`).
* Tracks survive `max_age` missed frames (occlusion bridging) and must reach
  `min_hits` before emission. Outputs persistent IDs, trajectory, and smoothed
  foot-point speed (px/s).
* No appearance embedding by default (motion-only). DeepSORT-style Re-ID can be
  added as an extra association stage.

## 3. Anomaly detection

* **IsolationForest** (runtime): fits online over a rolling buffer of scene-motion
  features `[n_objects, mean_speed, speed_std, log_area, heading_entropy]`; flags
  frames with a high z-deviation. Retrains periodically to adapt to scene drift.
* **Conv Autoencoder** (offline, `vision/anomaly/autoencoder.py`): trained on
  *normal* frames; reconstruction error thresholded at the p99 of a held-out
  split (`ml/training/train_autoencoder.py`). Suits static-camera video anomaly.

## 4. Human activity recognition

* **Heuristic** (default, real-time): kinematics from track bbox aspect ratio,
  center height, and speed → standing/walking/running/loitering/falling/crawling.
* **Deep (R3D-18)**: 3D-CNN clip classifier fine-tuned from Kinetics-400 for
  fighting/violence/falling (`ml/training/train_activity.py`), `clip_len=16`,
  112×112. Falls back to the heuristic if no checkpoint is present.

## 5. Camera tampering

Model-free frame statistics: variance-of-Laplacian (blur), dark-pixel ratio
(occlusion), and running-background mean-absolute-difference (scene change), with
persistence hysteresis to avoid flicker.

## 6. Explainability

* **Grad-CAM** (`vision/explain/gradcam.py`) for CNN backbones — class-activation
  heatmaps over the input frame.
* **Rule rationale** — every event carries a human-readable "why" plus the numeric
  contributing factors, surfaced in the dashboard's Explain panel and the
  `/threats/{id}/explain` endpoint.

## 7. Export & deployment

`ml/export/export_model.py` exports YOLO to ONNX / TensorRT / OpenVINO /
TorchScript. For edge (Jetson), export a FP16 TensorRT engine and set
`YOLO_MODEL` to the `.engine` file. `DEVICE=auto` picks CUDA when available and
falls back to CPU otherwise.

## 8. Reproducibility

Hyperparameters live in `ml/configs/hyperparameters.yaml`; training seeds are set
where applicable. Log training with TensorBoard (Ultralytics writes to
`runs/detect/...`). Record dataset version + commit hash with each trained model.
