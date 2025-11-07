# Copilot Instructions - Automated Attendance System

## Architecture Overview

This is a **dual-stack face recognition attendance system** with React frontend (Vite) and Flask backend using FaceNet + MTCNN for facial recognition.

### System Components
- **Frontend**: React 19 + Vite (port 5173), React Router for navigation
- **Backend**: Flask (port 5000 local / 8080 Railway) with MTCNN face detection + FaceNet embeddings
- **Database**: SQLite with two tables: `students` (stores face embeddings) and `attendance` (daily logs)
- **Security**: HTTPS with self-signed certs (mkcert for local), bcrypt password hashing, localStorage-based auth (10min timeout)

### Project Structure (Railway Deployment)
```
Automated-Attendance/
├── backend/              # Flask application (moved from facenet/)
│   ├── app.py           # Flask initialization + serves static React build
│   ├── routes.py        # API endpoints
│   ├── database.py      # SQLAlchemy models
│   ├── requirements.txt
│   ├── data/
│   │   ├── admin.json
│   │   └── database/    # SQLite database location
│   └── static/          # Built React app (copied by Docker)
├── frontend/            # React application (moved from src/)
│   ├── package.json
│   ├── vite.config.js
│   ├── src/            # React components
│   └── dist/           # Vite build output
├── Dockerfile          # Multi-stage build (Node + Python)
├── railway.toml        # Railway configuration
└── .dockerignore
```

## Critical Workflows

### Development Setup (Local)
```bash
# Terminal 1 - Frontend
npm install && npm run dev

# Terminal 2 - Backend
cd facenet && pip install -r requirements.txt && python app.py
```

### Development Setup (Railway Structure)
```bash
# Terminal 1 - Frontend
cd frontend && npm install && npm run dev

# Terminal 2 - Backend
cd backend && pip install -r requirements.txt && python app.py
```

### SSL Configuration (Optional for Local Network)
- Generate certs: `mkcert {Your-IP}` (replace `{Yout IP}` placeholder in code)
- Update all instances of `{Yout IP}` in: `app.py`, `vite.config.js`, and all React component API calls
- For localhost-only development, use `http://localhost:5000` instead

### Deployment to Railway

#### Production-Level Multi-Stage Dockerfile
```dockerfile
# -----------------------
# Stage 1: Build Frontend
# -----------------------
FROM node:18-alpine AS frontend-builder

# Set working directory
WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies with clean install for reproducible builds
RUN npm ci --only=production

# Copy frontend source
COPY frontend/ .

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
COPY backend/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------
# Stage 3: Production Runtime
# -----------------------
FROM python:3.12-slim

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/backend/data/database && \
    chown -R appuser:appuser /app

# Install runtime dependencies (including OpenCV/cv2 requirements)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python packages from builder
COPY --from=backend-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy backend application
COPY --chown=appuser:appuser backend/ ./backend/

# Copy built frontend into Flask static folder
COPY --from=frontend-builder --chown=appuser:appuser /app/frontend/dist ./backend/static

# Switch to non-root user
USER appuser

# Environment variables
ENV PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/api/students-today', timeout=5)"

# Expose port
EXPOSE 8080

# Run with Gunicorn (production WSGI server)
CMD ["gunicorn", \
    "--chdir", "backend", \
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
```

#### Docker Compose for Local Development
```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    volumes:
      - ./backend/data:/app/backend/data
    environment:
      - PORT=8080
      - FLASK_ENV=development
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/students-today"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

#### .dockerignore for Optimized Builds
```
# Node modules and build artifacts
node_modules/
frontend/node_modules/
frontend/dist/
npm-debug.log*

# Python cache
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/

# Git
.git/
.gitignore

# Documentation
README.md
*.md
!backend/README.md

# SSL certificates (for local dev only)
*.pem
*.crt
*.key

# Data (will be mounted as volume)
backend/data/database/*.db
facenet/data/database/*.db

# OS files
.DS_Store
Thumbs.db
```

#### Key Railway Configuration
- **Environment Variables**: `PORT=8080` (auto-provided by Railway)
- **Database Path**: Use `backend/data/database/` for SQLite persistence
- **Static Files**: Flask serves React build from `backend/static/`
- **API Prefix**: No `/api` prefix needed - Flask handles both SPA routes and API routes
- **Workers**: Gunicorn with 4 workers + 2 threads per worker for concurrency
- **Security**: Non-root user, minimal attack surface, health checks enabled

#### Flask App Modifications for Production
```python
# backend/app.py - Production-ready Flask setup
import os
from flask import Flask, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static', static_url_path='')

# Security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# CORS configuration for production
if os.environ.get('FLASK_ENV') == 'production':
    CORS(app, resources={r"/api/*": {"origins": ["https://your-domain.railway.app"]}})
else:
    CORS(app)  # Allow all origins in development

# Serve React SPA with fallback routing
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# Health check endpoint for monitoring
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'service': 'attendance-system'}, 200

# Run with appropriate server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    if debug:
        # Development server with SSL
        app.run(host="0.0.0.0", port=port, debug=True, 
                ssl_context=("./{Yout IP}.pem", "./{Yout IP}-key.pem"))
    else:
        # Production (use Gunicorn in production, this is fallback)
        app.run(host="0.0.0.0", port=port, debug=False)
```

#### Building and Running Docker Locally
```bash
# Build the image
docker build -t attendance-system:latest .

# Run the container
docker run -p 8080:8080 \
  -v $(pwd)/backend/data:/app/backend/data \
  -e PORT=8080 \
  attendance-system:latest

# Or use Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

#### Production Deployment Checklist
- [ ] Update CORS origins to production domain
- [ ] Set strong admin password (not default `admin123`)
- [ ] Configure volume mount for database persistence
- [ ] Set up backup strategy for `backend/data/database/`
- [ ] Enable Railway automatic deployments from GitHub
- [ ] Configure health check endpoint monitoring
- [ ] Set up logging aggregation (Railway provides this)
- [ ] Review Gunicorn worker count based on CPU cores
- [ ] Add `.dockerignore` to reduce image size
- [ ] Test with `docker-compose` before Railway deployment

#### Common Deployment Issues & Solutions

**Issue 1: ImportError: libGL.so.1 cannot open shared object file**
- **Cause**: OpenCV (cv2) requires system graphics libraries not included in python:slim image
- **Solution**: Add these packages to Dockerfile Stage 3 runtime dependencies:
  ```dockerfile
  RUN apt-get update && apt-get install -y --no-install-recommends \
      libgomp1 \
      libgl1 \
      libglib2.0-0 \
      libsm6 \
      libxext6 \
      libxrender1 \
      && rm -rf /var/lib/apt/lists/*
  ```
- **Why**: keras_facenet imports cv2, which requires OpenGL/X11 libraries even in headless mode

**Issue 2: Health Check Failing / Worker Boot Timeout**
- **Cause**: ML models (MTCNN + FaceNet) take 40-60s to initialize
- **Solution**: Increase HEALTHCHECK `start-period` to 60s in Dockerfile
- **Alternative**: Use `/health` endpoint instead of ML-dependent routes for health checks

**Issue 3: Error: can't chdir to 'backend'**
- **Cause**: railway.toml `startCommand` overrides Dockerfile CMD with wrong directory
- **Solution**: Remove `startCommand` from railway.toml or ensure it matches actual directory (`facenet` not `backend`)

**Issue 4: Static Files Not Serving (404 on React Routes)**
- **Cause**: Flask route ordering - catch-all route registered before specific routes
- **Solution**: Ensure `/health` and API routes registered BEFORE the catch-all `/<path:path>` route in app.py

## Key Patterns & Conventions

### Backend Architecture (`facenet/` or `backend/`)
- **`app.py`**: Initializes Flask, CORS, FaceNet embedder, MTCNN detector, and registers routes
  - **Local dev**: Runs with SSL on port 5000
  - **Railway prod**: Serves React build from `static/` folder, runs on port 8080 with Gunicorn
- **`routes.py`**: All API endpoints with inline helper functions (admin password management, face updates)
- **`database.py`**: SQLAlchemy models with `PickleType` for storing NumPy embeddings
- **Face Recognition Flow**: 
  1. MTCNN detects faces → crop → FaceNet generates 128D embedding
  2. Compare with DB using Euclidean distance (threshold: 0.1)
  3. Auto-update attendance: first detection = intime, subsequent = outtime

### Frontend Architecture (`src/` or `frontend/src/`)
- **Routing**: `App.jsx` defines 4 routes: `/` (recognition), `/enroll`, `/admin`, `/dashboard` (protected)
- **Protected Routes**: `ProtectedRoute.jsx` checks localStorage auth with 10min auto-logout
- **API Integration**: 
  - **Local dev**: Direct calls to `https://{Yout IP}:5000` (SSL with mkcert)
  - **Railway prod**: Relative URLs (e.g., `/recognize`, `/api/verify`) - same-origin requests
- **State Management**: Local component state with `useState`/`useEffect` (no Redux/Context)

### Component Patterns
```jsx
// Inline styles with gradient backgrounds (no CSS modules)
style={{ background: "linear-gradient(135deg, #43e97b, #38f9d7)" }}

// Real-time data refresh pattern (used in dashboard cards)
useEffect(() => {
  fetchData();
  const interval = setInterval(fetchData, 60000); // 1min polling
  return () => clearInterval(interval);
}, []);

// Webcam processing loop (EnrollPage, HomePage)
const processFrame = async () => {
  if (isProcessing) return;
  isProcessing = true;
  // ... capture frame, send to /recognize, draw bounding boxes
  requestAnimationFrame(processFrame);
};
```

### Recognition vs Enrollment
- **`/recognize` endpoint**: Identifies faces, logs attendance (no DB insert for "Unknown")
- **`/enroll` endpoint**: Detects single face, checks for duplicates, prompts to update existing student
- **`/update-face` endpoint**: Updates existing student's embedding after confirmation

### Data Flow Example (Attendance Logging)
1. `HomePage.jsx` captures webcam frame every animation frame
2. POST to `/recognize` with base64 image
3. Backend: MTCNN detects → FaceNet embeds → compare with all students → return matches
4. If match found (distance < 0.1), upsert `Attendance` table (unique constraint on student+date)
5. Frontend shows green notification overlay for 1s with cooldown (2s per student)

## Project-Specific Notes

### Placeholder Convention
- Replace `{Yout IP}` with actual IP/domain when setting up SSL (appears in 8+ files)
- Default admin password: `admin123` (stored in `facenet/data/admin.json` with bcrypt)

### Face Detection Constraints
- Enrollment: Rejects if 0 or >1 faces detected (enforces single-face training data)
- Recognition: Processes all detected faces in frame (multi-person attendance)

### Dashboard Data Sources
- **TodayStudents**: Count of today's attendance records
- **AbsentToday**: Set difference between enrolled students and today's attendees
- **WeeklyAttendance**: Bar chart with week offset navigation (supports past/future weeks)
- **CSV Export**: Fetches all attendance records from `/api/attendance-all`

### Authentication Pattern
```javascript
// localStorage structure
{ authenticated: true, timestamp: 1699123456789 }
// Refreshed on protected route visits, cleared after 10min inactivity
```

### Styling Approach
- Inline styles with gradient backgrounds (no global CSS framework)
- Responsive media queries embedded in `<style>` tags within components
- Animation keyframes defined inline for card entrance effects

## Common Tasks

### Adding New API Endpoint
1. Add route function in `routes.py` within `register_routes()`
2. Access models via closure parameters: `app, db, Attendance, detector, embedder`
3. Frontend: 
   - **Local**: Call with full HTTPS URL (`https://{Yout IP}:5000/api/...`)
   - **Railway**: Use relative URL (`/api/...`)

### Environment Variables for Railway
- **`PORT`**: Auto-set by Railway to 8080 (Flask should read from `os.environ.get("PORT", 5000)`)
- **Database Path**: Use relative path `backend/data/database/` for SQLite persistence
- **CORS**: Configure based on deployment domain (Railway provides auto HTTPS)
- **API URLs in Frontend**: Use environment-based configuration:
  ```javascript
  const API_URL = import.meta.env.PROD ? '' : 'https://{Yout IP}:5000';
  // Then: fetch(`${API_URL}/api/verify`)
  ```

### Modifying Face Recognition Threshold
- Edit `THRESHOLD = 0.1` in `routes.py` `/recognize` endpoint
- Lower = stricter matching, higher = more lenient

### Adding Student Metadata
1. Add column to `Student` model in `database.py`
2. Update `/enroll` endpoint to accept new field
3. Add input field in `EnrollPage.jsx` (step 2 form)

### Debugging Recognition Issues
- Check console for distance logs: `[HH:MM:SS] Name: distance=0.XXX`
- Verify embeddings stored: Query `students` table for non-null `embedding` column
- Test MTCNN detection: Check `faces` array length in `/recognize` response
