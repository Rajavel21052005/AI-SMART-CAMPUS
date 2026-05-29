# ============================================================
# Dockerfile — Smart Campus AI System
# Multi-stage: builder installs deps, final is lean runtime
# ============================================================

FROM python:3.11-slim AS builder

# Install OS-level build dependencies for OpenCV + dlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake libopencv-dev libboost-python-dev \
    libsm6 libxext6 libxrender-dev libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Runtime stage ──────────────────────────────────────────
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsm6 libxext6 libxrender-dev libglib2.0-0 libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Create required directories
RUN mkdir -p logs ai_models \
    app/static/images/uploads \
    app/static/images/security

# Expose Flask port
EXPOSE 5000

# Default command
CMD ["python", "run.py"]
