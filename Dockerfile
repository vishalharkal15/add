# -----------------------
# Stage 1: Build Frontend
# -----------------------
FROM node:20-alpine AS frontend-builder

# Set working directory
WORKDIR /app

# Copy package files (from root directory)
COPY package*.json ./

# Install ALL dependencies (including devDependencies for build)
RUN npm ci

# Copy frontend source (src/, public/, config files)
COPY src/ ./src/
COPY public/ ./public/
COPY index.html ./
COPY vite.config.js ./
COPY eslint.config.js ./

# Build optimized production bundle
RUN npm run build

# -----------------------
# Stage 2: Backend Setup
# -----------------------
FROM python:3.12-slim AS backend-builder

# Set working directory
WORKDIR /app

# Install system dependencies for ML libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY facenet/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------
# Stage 3: Production Runtime
# -----------------------
FROM python:3.12-slim

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/facenet/data/database && \
    chown -R appuser:appuser /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python packages from builder
COPY --from=backend-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy backend application (facenet directory)
COPY --chown=appuser:appuser facenet/ ./facenet/

# Copy built frontend into Flask static folder
COPY --from=frontend-builder --chown=appuser:appuser /app/dist ./facenet/static

# Switch to non-root user
USER appuser

# Environment variables
ENV PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production

# Health check (commented out until requests is added to requirements.txt)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD python -c "import requests; requests.get('http://localhost:8080/api/students-today', timeout=5)"

# Expose port
EXPOSE 8080

# Run with Gunicorn (production WSGI server)
CMD ["gunicorn", \
    "--chdir", "facenet", \
    "--bind", "0.0.0.0:8080", \
    "--workers", "4", \
    "--threads", "2", \
    "--worker-class", "gthread", \
    "--worker-tmp-dir", "/dev/shm", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "--log-level", "info", \
    "--timeout", "120", \
    "app:app"]
