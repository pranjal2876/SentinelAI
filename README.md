<div align="center">

# 🛰️ SentinelAI

### AI-Based Threat Detection & Intelligent Surveillance System

*Real-time, multi-camera object detection, tracking, threat analysis, anomaly detection, and human-activity recognition — with a modern React operations dashboard.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)]()
[![PyTorch](https://img.shields.io/badge/PyTorch-2.3-ee4c2c)]()
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-purple)]()
[![React](https://img.shields.io/badge/React-18-61dafb)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)]()

</div>

---

## 📌 Overview

**SentinelAI** ingests live CCTV / IP-camera (RTSP) / webcam / video-file streams and, in
real time, detects potential security threats using deep learning and classical CV.
It combines **object detection (YOLOv8)**, **multi-object tracking (ByteTrack-style)**,
a **modular rule-based threat engine**, **unsupervised anomaly detection**, and
**human-activity recognition**, surfacing everything through a **FastAPI** backend
(REST + WebSockets) and a **React + TypeScript** dashboard.

It is engineered as a flagship **DRDO AI/ML internship project** — modular, scalable,
research-oriented, and production-deployable (Docker, GPU + CPU fallback, CI).

## ✨ Key Capabilities

| Module | What it does |
|---|---|
| 🎥 **Real-time ingestion** | Webcam, RTSP/IP camera, video files, multiple concurrent streams, threaded low-latency capture |
| 🎯 **Object detection** | YOLOv8 — people, vehicles, bikes, trucks, buses, bags/backpacks/suitcases (+ optional weapons) |
| 🧭 **Multi-object tracking** | Persistent IDs, Kalman motion model, two-stage IoU association, trajectories, entry/exit counting, heatmaps |
| 🚨 **Threat engine** | Intrusion, tripwire crossing, loitering, abandoned object, crowd/density, running, wrong-direction, vehicle-in-zone, multiple intruders, camera tampering |
| 🧠 **Anomaly detection** | IsolationForest over scene-motion features + a conv-autoencoder for offline video anomaly |
| 🏃 **Activity recognition** | Heuristic kinematics (walk/run/stand/loiter/fall/crawl) + 3D-CNN (R3D-18) for fighting/violence/falling |
| 🔔 **Alerts** | Dashboard, desktop, Email (SMTP), Telegram — with snapshot, clip & metadata |
| 📊 **Dashboard** | Live feeds, threat timeline, camera status, statistics, heatmaps, history, dark mode |
| 🔍 **Explainable AI** | Grad-CAM + structured per-event rationale (why it fired, contributing factors, confidence) |
| 📈 **Analytics** | Daily reports, threat trends, object stats, PDF & Excel export |
| ⚙️ **MLOps** | Docker Compose, env-config, CI, logging, monitoring, GPU support, CPU fallback |

## 🏗️ Architecture

```
                         ┌────────────────────────────────────────────┐
   RTSP / Webcam ─────▶  │  CameraWorker (thread)                      │
   Video file    ─────▶  │    └─ SurveillancePipeline                  │
                         │        detect → track → heatmap → threats   │
                         │        → anomaly → tampering → activity      │
                         └───────────────┬────────────────────────────┘
                                         │ FrameResult / ThreatEvent
                                         ▼
                    ┌──────────────────────────────────────┐
                    │  FastAPI backend                       │
                    │   REST API · WebSocket hub · Auth      │
                    │   EventBus → Alerts (mail/telegram)    │
                    │   SQLAlchemy async → PostgreSQL        │
                    │   Redis (pub/sub, cache)               │
                    └───────────────┬───────────────────────┘
                                    │ JSON / MJPEG / WS
                                    ▼
                    ┌──────────────────────────────────────┐
                    │  React + TypeScript Dashboard          │
                    │   Live view · Timeline · Analytics     │
                    └──────────────────────────────────────┘
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design.

## 📂 Repository Layout

```
SentinelAI/
├── backend/            # FastAPI app: vision pipeline, API, DB, services
│   └── app/
│       ├── core/       # config, logging, security
│       ├── vision/     # detection, tracking, threat, anomaly, activity, explain
│       ├── db/         # SQLAlchemy models + session
│       ├── schemas/    # Pydantic request/response models
│       ├── services/   # camera manager, event bus, alerts, analytics
│       ├── api/        # REST endpoints (v1)
│       └── websocket/  # live streaming + event push
├── frontend/           # React + TypeScript + Vite dashboard
├── ml/                 # dataset prep, training, evaluation, export, notebooks
├── infra/              # docker, nginx, prometheus, grafana
├── docs/               # architecture, install, API, user & dev guides
└── scripts/            # helper scripts
```

## 🚀 Quick Start (Docker)

```bash
git clone https://github.com/pranjal2876/SentinelAI.git
cd SentinelAI
cp .env.example .env          # then edit secrets
docker compose -f infra/docker/docker-compose.yml up --build
```

* Dashboard → http://localhost:5173
* API docs (Swagger) → http://localhost:8000/docs

## 🧑‍💻 Local Development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Full platform-specific instructions (Windows / Linux / NVIDIA GPU / Cloud) live in
[`docs/INSTALLATION.md`](docs/INSTALLATION.md).

## 📚 Documentation

* [Architecture](docs/ARCHITECTURE.md) · [Installation](docs/INSTALLATION.md)
* [API Reference](docs/API.md) · [User Manual](docs/USER_GUIDE.md)
* [Developer Guide](docs/DEVELOPER_GUIDE.md) · [Model Docs](docs/MODELS.md)

## 🛡️ Responsible Use

SentinelAI is intended for **authorized, defensive physical-security monitoring**
(perimeter protection, restricted-area enforcement, safety analytics). Deploy it only
where you have the legal right to record and analyze, comply with local privacy law,
and prefer privacy-preserving configurations (e.g. disable face recognition where not
permitted).

## 📄 License

MIT — see [LICENSE](LICENSE).
