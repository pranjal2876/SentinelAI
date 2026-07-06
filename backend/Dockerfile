# ==========================================================================
# SentinelAI Backend image.
# CPU build by default. For GPU, build with:
#   --build-arg BASE_IMAGE=nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04
# and install the CUDA torch wheel (see docs/INSTALLATION.md).
# ==========================================================================
ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# System deps for OpenCV + video decoding.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender1 libgl1 ffmpeg curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Non-root user.
RUN useradd -m sentinel && chown -R sentinel:sentinel /app
USER sentinel

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/system/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
