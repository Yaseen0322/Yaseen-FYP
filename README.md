# Privacy-Preserving Employee Activity + Presence Tracking System

## 🎯 Project Overview

A desktop-based productivity monitoring system for software houses that tracks employee work activity, idle time, webcam-based presence, and browser usage — **without taking screenshots or storing camera images/video**.

### Key Features

- **Auto-start on boot** - Tracking begins when PC starts
- **App usage tracking** - Monitor which applications are used
- **Idle detection** - Track inactive periods
- **Presence detection** - Webcam-based face detection (no images stored)
- **Browser tracking** - Productive vs unproductive websites
- **Employee dashboard** - Personal daily/weekly reports
- **Manager dashboard** - Team analytics and reports

### Privacy-First Design

| ✅ What We Track | ❌ What We DON'T Track |
|-----------------|----------------------|
| App names | Screenshots |
| Time durations | Camera images/video |
| Idle intervals | Keystroke content |
| Presence status | Audio recordings |
| Domain names | Document content |

---

## 📁 Project Structure

```
Yaseen FYP/
├── SRS/                        # Original requirements document
│   └── project stack.docx
│
├── Phase1-MVP/                 # Minimum Viable Product
│   ├── backend/                # FastAPI Backend
│   ├── desktop-app/            # Electron + React Desktop App
│   ├── webcam-service/         # Python Presence Detection
│   ├── browser-extension/      # Chrome/Edge Extension
│   ├── manager-portal/         # React Web Manager Dashboard
│   └── README.md
│
├── Phase2-Advanced/            # Advanced Features
│   ├── (all Phase 1 components)
│   ├── + Department Analytics
│   ├── + Alert System
│   ├── + Weekly Trends
│   └── README.md
│
├── Phase3-Complete/            # Integrated release-candidate system
│   ├── (all Phase 2 components)
│   ├── + Slack Integration
│   ├── + Jira Integration
│   ├── + Google/Microsoft SSO
│   ├── + ML Classification
│   └── README.md
│
└── README.md                   # This file
```

---

## 🚀 Phase Breakdown

### Phase 1: MVP (Minimum Viable Product)

| Component | Description |
|-----------|-------------|
| Backend | FastAPI + PostgreSQL + Redis |
| Desktop App | Electron + React (employee UI) |
| Webcam Service | Python + MediaPipe (presence detection) |
| Browser Extension | Chrome/Edge/Firefox (domain tracking) |
| Manager Portal | React web app |

**Features:**
- Employee agent auto-start
- App usage + idle tracking
- Webcam presence detection
- Browser domain tracking
- Basic productivity classification
- Employee personal dashboard
- Manager dashboard with reports

### Phase 2: Advanced

**New Features:**
- Department-level analytics
- Cross-department comparisons
- Configurable alert rules
- Excessive idle alerts
- Camera-off alerts
- Low productivity alerts
- Weekly trend visualization
- Historical data analysis

### Phase 3: Integrated Release Candidate

**New Features:**
- **Slack Integration APIs/UI**: Configuration, connectivity testing, and worker-driven alert delivery
- **Jira Integration APIs/UI**: Configuration and connectivity testing for future exports
- **Google SSO**: Single sign-on with Google Workspace
- **Microsoft SSO**: Single sign-on with Microsoft 365
- **ML Classification Review**: Suggested classifications are generated from uncategorized ingest and reviewed by managers

---

## 💻 Tech Stack

### Frontend
- **React.js** - UI framework
- **Electron** - Desktop app shell
- **TailwindCSS** - Styling
- **Recharts** - Charts and visualization
- **Zustand** - State management

### Backend
- **FastAPI** - Python web framework
- **PostgreSQL** - Primary database
- **Redis** - Caching and queues
- **SQLAlchemy** - ORM

### Desktop Agent
- **Node.js** - Runtime in Electron
- **active-win** - Window detection
- **Python** - Webcam service
- **MediaPipe** - Face detection

### Browser Extension
- **Manifest V3** - Modern extension format
- **Service Worker** - Background processing

---

## 🔧 Quick Start

### Prerequisites

- Node.js 18+
- Python 3.10+
- PostgreSQL 15+
- Redis 7+

### 1. Start Backend (Phase 3)

```bash
cd "/home/yaseen/Downloads/Yaseen FYP/Yaseen FYP/Phase3-Complete/backend"

# Using Docker (recommended)
docker-compose up -d

# Or manually
python -m venv venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

#### New commands to run backend
1:
cd "/home/yaseen/Downloads/Yaseen FYP/Yaseen FYP"
source .venv/bin/activate
2:
cd "/home/yaseen/Downloads/Yaseen FYP/Yaseen FYP/Phase3-Complete/backend"
uvicorn app.main:app --reload


### 2. Start Webcam Service

```bash
cd "/home/yaseen/Downloads/Yaseen FYP/Yaseen FYP/Phase3-Complete/webcam-service"
python -m venv venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
#### New commands to run webcam
cd "/home/yaseen/Downloads/Yaseen FYP/Yaseen FYP/Phase3-Complete/webcam-service"
.venv/bin/python main.py

cd "/home/yaseen/Downloads/Yaseen FYP/Yaseen FYP/Phase3-Complete/webcam-service"
.venv/bin/python main.py



### 3. Start Desktop App

```bash
cd "/home/yaseen/Downloads/Yaseen FYP/Yaseen FYP/Phase3-Complete/desktop-app"
npm install
npm run dev
```

#### New Commands to run desktop App:

cd "/home/yaseen/Downloads/Yaseen FYP/Yaseen FYP/Phase3-Complete/desktop-app"
npm run dev


### 4. Start Manager Portal

```bash
cd "/home/yaseen/Downloads/Yaseen FYP/Yaseen FYP/Phase3-Complete/manager-portal"
npm install
npm run dev
```

### 5. Start Alert Worker

```bash
cd Phase3-Complete/backend
python -m app.workers.operational_jobs --interval 300
```

### 6. Install Browser Extension

1. Go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select `Phase3-Complete/browser-extension`

### 7. Local Demo Bootstrap

For a supervised local demo, the validated startup order is:

1. Backend migration
2. Backend API
3. Alert worker
4. Webcam service
5. Manager portal
6. Desktop app
7. Browser extension

There is a helper script for this flow:

```bash
cd Phase3-Complete
./run-demo.sh --reset-demo-db
```

Stop the stack with:

```bash
./stop-demo.sh
```

Headless-safe validation path:

```bash
./run-demo.sh --reset-demo-db --skip-desktop
```

Notes:
- The helper uses an isolated demo database at `Phase3-Complete/backend/demo_staging.db`
- The current “today” and date-picker behavior follows UTC ISO day strings used by the desktop and manager UIs
- See `Phase3-Complete/DEMO_RUNBOOK.md` for the validated demo scenario and recovery steps

---

## 📊 API Documentation

Once backend is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🔐 User Roles

| Role | Access |
|------|--------|
| **Employee** | Personal dashboard, own reports |
| **Manager** | Team members, department analytics |
| **Admin** | Organization settings, integrations |
| **Super Admin** | Multi-org, all settings |

---

## 📈 Data Model Overview

```
Organizations
└── Departments
    └── Users (employees/managers)
        └── Devices
            ├── App Usage
            ├── Idle Intervals
            ├── Presence Intervals
            └── Browser Usage

Domain Rules (org-level classification)
Alert Rules (org-level configuration)
Daily Summaries (pre-computed)
```

---

## 🛡️ Security Features

- JWT authentication with refresh tokens
- Role-based access control (RBAC)
- TLS/HTTPS encryption
- Password hashing (bcrypt)
- Configurable data retention
- Audit logging (optional)

---

## 📝 License

Proprietary - All rights reserved.

---

## 👩‍💻 Developer

**Yaseen** - Final Year Project

---

## 🙏 Acknowledgments

- FastAPI for the excellent Python web framework
- Electron for cross-platform desktop apps
- MediaPipe for efficient face detection
- React ecosystem for frontend development
