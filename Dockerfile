# ── Lahore Pulse AI — Railway Dockerfile ──────────────────────────────
# Explicit Node.js + Python build to avoid Nixpacks language-detection issues.

# ── 1. Build frontend ────────────────────────────────────────────────
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --prefer-offline
COPY frontend/ ./
RUN npm run build

# ── 2. Runtime image (Python + static frontend) ─────────────────────
FROM python:3.13-slim

# Prevent .pyc files and enable unbuffered logs (useful in Railway logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install backend Python dependencies first (layer caching)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ ./backend/

# Copy pre-built frontend into the static path served by FastAPI
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 8000

# Start FastAPI via uvicorn; $PORT is set by Railway at runtime
CMD ["sh", "-c", "cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
