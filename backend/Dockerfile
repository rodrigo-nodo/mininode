FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (better layer caching)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY backend/src ./src

# Expose default port (Render will set $PORT)
EXPOSE 8000

# Start the FastAPI app. Render provides $PORT; default to 8000 locally.
CMD ["sh","-c","uvicorn mininode_api.main:app --app-dir src --host 0.0.0.0 --port ${PORT:-8000}"]

