# SentinelAI — Installation Guide

Covers Docker (recommended), local Windows, local Linux, NVIDIA GPU, and cloud.

---

## 0. Prerequisites

| Tool | Version | Needed for |
|---|---|---|
| Docker + Compose | 24+ | containerized deployment |
| Python | 3.10–3.11 | local backend / ML |
| Node.js | 20+ | local frontend |
| PostgreSQL | 14+ | local DB (or use the Docker one) |
| NVIDIA driver + CUDA 12 | optional | GPU acceleration |

Clone and configure:

```bash
git clone https://github.com/pranjal2876/SentinelAI.git
cd SentinelAI
cp .env.example .env      # edit SECRET_KEY, DB creds, alert channels
```

---

## 1. Docker (recommended)

```bash
docker compose -f infra/docker/docker-compose.yml up --build
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:5173 |
| API docs | http://localhost:8000/docs |
| Grafana | http://localhost:3000 (admin/admin) |
| Prometheus | http://localhost:9090 |

Default login: **admin / admin123** (change immediately — see User Guide).

Stop: `docker compose -f infra/docker/docker-compose.yml down`
(add `-v` to also wipe volumes).

---

## 2. Local — Windows

```powershell
# Backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Ensure PostgreSQL is running and .env DB settings match
uvicorn app.main:app --reload --port 8000
```

```powershell
# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Quick demo without the API (webcam through the pipeline):

```powershell
cd backend
python run_local.py --source 0 --demo-zone
```

---

## 3. Local — Linux / macOS

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd ../frontend && npm install && npm run dev
```

Install system libs for OpenCV if missing:
`sudo apt install -y libgl1 libglib2.0-0 ffmpeg`.

---

## 4. NVIDIA GPU acceleration

1. Install the NVIDIA driver + CUDA 12.x and `nvidia-container-toolkit`.
2. Install the CUDA PyTorch wheel **before** `requirements.txt`:

   ```bash
   pip install torch==2.3.1 torchvision==0.18.1 --index-url https://download.pytorch.org/whl/cu121
   pip install -r requirements.txt
   ```

3. Set `DEVICE=cuda` in `.env`.
4. For Docker GPU, uncomment the `deploy.resources` block for `backend` in
   `docker-compose.yml` and build the image with a CUDA base:

   ```bash
   docker build --build-arg BASE_IMAGE=nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04 \
     -t sentinelai-backend ./backend
   ```

Verify: `GET /api/v1/system/info` should report `"device": "cuda:0"`.

---

## 5. Cloud (generic VM)

1. Provision a VM (e.g. AWS g4dn for GPU, or any 4-core CPU box).
2. Install Docker + Compose, open ports 5173/8000 (or put nginx/Caddy in front
   with TLS).
3. `git clone`, set a strong `SECRET_KEY` and DB password in `.env`.
4. `docker compose ... up -d --build`.
5. Point cameras via RTSP URLs in the Cameras page.

For managed Postgres, set `DATABASE_URL` in `.env` and drop the `db` service.

---

## 6. Database migrations

Local dev auto-creates tables on startup. For controlled environments:

```bash
cd backend
alembic revision --autogenerate -m "init"
alembic upgrade head
```

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `Could not open source` | Check RTSP URL/credentials; test with `ffplay <url>` |
| Slow FPS on CPU | Use `yolov8n.pt`, raise `FRAME_STRIDE`, lower `MAX_INFERENCE_FPS` |
| CUDA not detected | `python -c "import torch;print(torch.cuda.is_available())"` |
| WS not connecting | Confirm the Vite proxy / nginx `/ws/` block and CORS origins |
| First inference slow | Ultralytics downloads weights on first run; pre-bake into the image |
