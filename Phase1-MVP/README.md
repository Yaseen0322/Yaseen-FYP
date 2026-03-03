# Phase 1 - MVP: Privacy-Preserving Employee Activity Tracker

## 📋 Overview

This is the MVP (Minimum Viable Product) of the Privacy-Preserving Employee Activity + Presence Tracking system for software houses.

## 🎯 Features Included in Phase 1

- ✅ Employee agent auto-start on system boot
- ✅ App usage + idle time tracking
- ✅ Webcam presence detection (no image storage)
- ✅ Browser extension + domain tracking
- ✅ Basic productive/unproductive classification rules
- ✅ Employee dashboard (daily/weekly reports)
- ✅ Manager dashboard with employee reports

## 🏗️ Project Structure

```
Phase1-MVP/
├── backend/                 # FastAPI Backend Server
│   ├── app/
│   │   ├── api/            # API Routes
│   │   ├── core/           # Config, Security, Database
│   │   ├── models/         # SQLAlchemy Models
│   │   ├── schemas/        # Pydantic Schemas
│   │   └── main.py         # Application Entry
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── desktop-app/            # Electron + React Desktop App
│   ├── src/
│   │   ├── main/           # Electron Main Process
│   │   │   ├── modules/    # Tracking Modules
│   │   │   └── preload.js  # IPC Bridge
│   │   └── renderer/       # React Frontend
│   │       ├── components/
│   │       ├── pages/
│   │       └── stores/
│   └── package.json
│
├── webcam-service/         # Python Webcam Presence Detection
│   ├── main.py
│   └── requirements.txt
│
├── browser-extension/      # Chrome/Edge/Firefox Extension
│   ├── manifest.json
│   ├── background.js
│   ├── popup.html
│   └── popup.js
│
└── manager-portal/         # React Manager Web Portal
    ├── src/
    │   ├── components/
    │   ├── pages/
    │   ├── stores/
    │   └── utils/
    └── package.json
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ (for desktop app and manager portal)
- Python 3.10+ (for backend and webcam service)
- PostgreSQL 15+
- Redis 7+

### 1. Start Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env file and configure
cp env.example.txt .env
# Edit .env with your database credentials

# Run with Docker (recommended)
docker-compose up -d

# Or run directly
uvicorn app.main:app --reload --port 8000
```

### 2. Start Webcam Service

```bash
cd webcam-service

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run service
python main.py
# Runs on http://localhost:8001
```

### 3. Start Desktop App

```bash
cd desktop-app

# Install dependencies
npm install

# Run in development
npm run dev

# Build for production
npm run build:win   # Windows
npm run build:mac   # macOS
npm run build:linux # Linux
```

### 4. Start Manager Portal

```bash
cd manager-portal

# Install dependencies
npm install

# Run in development
npm run dev
# Opens on http://localhost:3000

# Build for production
npm run build
```

### 5. Install Browser Extension

1. Open Chrome/Edge and go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `browser-extension` folder

## 📊 API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔒 Privacy Features

**What we track:**
- Application names and usage time
- Idle intervals (no keystroke content)
- Presence status (present/absent/camera_off)
- Website domain names

**What we DO NOT track:**
- ❌ No screenshots
- ❌ No webcam images or videos
- ❌ No keystroke content
- ❌ No audio recording
- ❌ No document content

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Desktop App
```bash
cd desktop-app
npm test
```

## 📝 First-time Setup

1. Start the backend server
2. Register the first user (automatically becomes admin):
   ```
   POST /api/v1/auth/register
   {
     "email": "admin@company.com",
     "name": "Admin User",
     "password": "your-secure-password"
   }
   ```
3. Login to the manager portal
4. Create departments and add employees
5. Employees can then login to the desktop app

## 🔧 Configuration

### Environment Variables (Backend)

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | postgresql://... |
| SECRET_KEY | JWT secret key | (required) |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token expiry | 30 |
| DEFAULT_TIMEZONE | Org timezone | Asia/Karachi |

### Desktop App Settings

Settings are stored per-user and can be configured in the Settings page:
- Idle threshold (seconds)
- Window title storage (on/off)
- Sync interval

## 📄 License

Proprietary - All rights reserved.
