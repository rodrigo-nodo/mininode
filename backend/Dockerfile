FROM python:3.11-slim

# Fast, safe defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# System deps (OCR) — sin prompts de debconf ni warnings
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y -q --no-install-recommends \
      apt-utils \
      tesseract-ocr \
      tesseract-ocr-spa \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create virtualenv first (so pip doesn't warn about root) and install deps
RUN python -m venv "$VIRTUAL_ENV"
COPY requirements.txt ./requirements.txt
RUN "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install --no-cache-dir -r requirements.txt

# Copy source code
COPY src ./src

# Create non-root user and fix ownership
RUN useradd -m -u 10001 appuser \
 && chown -R appuser:appuser /app "$VIRTUAL_ENV"
USER appuser

# Expose default port (Render sets $PORT)
EXPOSE 8000

# Start the FastAPI app. Render provides $PORT; default to 8000 locally.
CMD ["sh","-c","uvicorn mininode_api.main:app --app-dir src --host 0.0.0.0 --port ${PORT:-8000}"]
