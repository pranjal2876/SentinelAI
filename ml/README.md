# SentinelAI — Machine Learning

End-to-end training, evaluation and export tooling for the models used by
SentinelAI. All scripts are CLI-driven and log to stdout.

```
ml/
├── configs/            # YAML configs (YOLO data, hyperparameters)
├── datasets/           # dataset prep + annotation helpers
├── training/           # training scripts (YOLO, autoencoder, activity)
├── evaluation/         # metric computation + confusion matrices
├── export/             # ONNX / TensorRT export
└── notebooks/          # exploratory notebooks
```

## Typical workflow

```bash
# 1. Prepare a YOLO-format dataset (converts / verifies labels)
python datasets/prepare_yolo_dataset.py --src /data/raw --out /data/yolo

# 2. Fine-tune YOLOv8 on surveillance classes (transfer learning)
python training/train_yolo.py --data configs/surveillance.yaml --model yolov8s.pt --epochs 100

# 3. Train the video anomaly autoencoder on "normal" footage
python training/train_autoencoder.py --frames /data/normal_frames --epochs 30

# 4. Train the 3D-CNN activity recognizer
python training/train_activity.py --data /data/activity_clips --epochs 40

# 5. Evaluate
python evaluation/evaluate_yolo.py --weights runs/detect/train/weights/best.pt --data configs/surveillance.yaml

# 6. Export for deployment
python export/export_model.py --weights best.pt --format onnx
```

See [`docs/MODELS.md`](../docs/MODELS.md) for dataset sources, class definitions,
hyperparameters and benchmark results.
