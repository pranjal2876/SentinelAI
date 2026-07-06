# SentinelAI — Architecture

## 1. Overview

SentinelAI is a modular, real-time video-analytics platform. It is split into
four cooperating tiers:

1. **Vision / Inference tier** — per-camera pipelines that turn raw frames into
   structured detections, tracks, and threat events.
2. **Application tier (FastAPI)** — REST + WebSocket API, authentication,
   persistence, alerting, analytics.
3. **Data tier** — PostgreSQL (durable state) and Redis (cache / pub-sub).
4. **Presentation tier (React)** — the operations dashboard.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION TIER                              │
│   React + TS dashboard  (live view, timeline, analytics, admin)         │
└───────────────▲───────────────────────────────▲────────────────────────┘
                │ REST/JSON, WS events           │ WS/MJPEG frames
┌───────────────┴───────────────────────────────┴────────────────────────┐
│                          APPLICATION TIER (FastAPI)                     │
│  Auth(JWT) · Cameras · Threats · Zones · Analytics · Reports · System   │
│  ConnectionManager (WS hub) · EventBus · Alert dispatch                 │
└───────▲───────────────────────▲───────────────────────▲────────────────┘
        │ ORM (async)           │ publish_threat()       │ pub/sub, cache
┌───────┴──────────┐   ┌────────┴─────────┐     ┌────────┴─────────┐
│   PostgreSQL     │   │  Camera workers  │     │      Redis        │
│ users, cameras,  │   │  (threads)       │     └───────────────────┘
│ threat_logs,     │   │   └ Pipeline     │
│ zones, config    │   │      detect→track│
└──────────────────┘   │      →threat→...  │
                       └────────▲──────────┘
                                │ frames
                   RTSP / Webcam / File sources
```

## 2. Vision pipeline (per camera)

Each `CameraWorker` (a daemon thread) owns one `SurveillancePipeline`:

```
frame
  │
  ├─▶ ObjectDetector (YOLOv8)         → detections
  ├─▶ MultiObjectTracker (ByteTrack)  → tracks (persistent IDs, trajectory, speed)
  ├─▶ HeatmapAccumulator              → occupancy heatmap
  ├─▶ ThreatEngine (rules)            → threat events
  ├─▶ MotionAnomalyDetector (IForest) → anomaly events
  ├─▶ TamperingDetector               → tamper events
  ├─▶ ActivityRecognizer              → activities (annotate threats)
  └─▶ annotate_frame                  → JPEG for streaming
```

**Why threads, not asyncio, for capture?** OpenCV capture + PyTorch inference are
blocking, CPU/GPU-bound calls. Running each camera in its own thread keeps the
event loop free and isolates each pipeline's stateful detectors. Threads hand
results back to the loop through the thread-safe `EventBus`
(`asyncio.run_coroutine_threadsafe`).

## 3. Threat engine design

The engine is a collection of independent, individually-testable rules operating
on the tracked-object list plus configurable **zones** (normalized polygons /
lines). Each rule returns a normalized score in `[0,1]`; severity buckets are
derived from the score. A per-`(category, key)` **cooldown** deduplicates alerts.

| Rule | Signal |
|---|---|
| Intrusion | person foot-point inside a RESTRICTED polygon |
| Tripwire | trajectory segment crosses a TRIPWIRE line |
| Loitering | dwell ≥ threshold and near-stationary |
| Abandoned object | carriable object static + no person nearby, ≥ timeout |
| Crowd | person count ≥ threshold within a compact region |
| Running | smoothed foot-point speed ≥ threshold |
| Wrong direction | motion vector opposes a DIRECTIONAL corridor |
| Vehicle-in-zone | vehicle inside excluded/restricted zone |
| Multiple intruders | ≥2 people inside a restricted zone |
| Camera tampering | blur/occlusion/scene-change persistence |
| Anomaly | IsolationForest z-score over scene-motion features |

## 4. Data model

* **users** — accounts + RBAC (admin/operator/viewer).
* **cameras** — source, status, fps, per-camera thresholds.
* **threat_logs** — one row per raised event (indexed on camera+time,
  category+time), snapshot path, JSON metadata.
* **zones** — persisted ROIs, synced to live workers on change.
* **system_config** — key/value runtime settings.

## 5. Real-time transport

* `/ws/events` — JSON threat push to all dashboard clients.
* `/ws/stream/{camera_id}` — annotated JPEG frames (binary).
* `/stream/{camera_id}.mjpg` — MJPEG HTTP fallback for simple `<img>` viewers.

## 6. Scalability path

* **Vertical**: batch inference, larger YOLO variant, TensorRT export, FP16.
* **Horizontal**: run camera workers as separate processes/containers publishing
  events to Redis; the API tier becomes stateless behind a load balancer. The
  `EventBus` abstraction is the seam where an in-process hand-off is swapped for
  a Redis Stream / Kafka topic.
* **Edge**: deploy the pipeline on NVIDIA Jetson with a TensorRT engine; only
  threat events (not raw video) traverse the network.

## 7. Security

* JWT access + refresh tokens, bcrypt password hashing, RBAC dependencies.
* CORS allow-list, non-root container user, secrets via environment only.
* Snapshots and recordings stored outside the web root; served through
  authenticated endpoints in production.
