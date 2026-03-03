# Phase 2 - Advanced: Privacy-Preserving Employee Activity Tracker

## 📋 Overview

Phase 2 builds upon the MVP to add advanced analytics, alerting, and management features.

## 🎯 New Features in Phase 2

- ✅ **Department Analytics** - Compare departments, view aggregated stats
- ✅ **Alert System** - Rules-based alerts for idle time, camera off, low productivity
- ✅ **Advanced Rules & Overrides** - Department-specific domain classifications
- ✅ **Weekly Trends** - Historical data visualization and trends
- ✅ **Employee Comparisons** - Compare employee performance within departments

## 🏗️ Changes from Phase 1

### Backend Additions

```
backend/app/
├── models/
│   └── alerts.py              # NEW: Alert and AlertRule models
├── api/
│   ├── alerts.py              # NEW: Alerts API routes
│   └── department_analytics.py # NEW: Analytics API routes
└── services/
    └── alert_processor.py     # NEW: Background alert processor
```

### Manager Portal Additions

```
manager-portal/src/pages/
├── Alerts.jsx                 # NEW: Alert management page
└── DepartmentAnalytics.jsx    # NEW: Department analytics page
```

## 🚀 New API Endpoints

### Alerts API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/alerts/rules` | GET | List alert rules |
| `/api/v1/alerts/rules` | POST | Create alert rule |
| `/api/v1/alerts/rules/{id}` | PATCH | Toggle rule active |
| `/api/v1/alerts/` | GET | List alerts |
| `/api/v1/alerts/my` | GET | List my alerts |
| `/api/v1/alerts/{id}/acknowledge` | POST | Acknowledge alert |
| `/api/v1/alerts/stats` | GET | Alert statistics |

### Department Analytics API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analytics/departments/summary` | GET | All departments summary |
| `/api/v1/analytics/departments/{id}/details` | GET | Department details |
| `/api/v1/analytics/departments/comparison` | GET | Compare departments |
| `/api/v1/analytics/trends/weekly` | GET | Weekly trends |

## 🔔 Alert Types

| Type | Description | Default Threshold |
|------|-------------|-------------------|
| `excessive_idle` | Too much idle time | 2 hours |
| `camera_off_long` | Camera off extended | 1 hour |
| `low_productivity` | Low productive time | <30% |

## ⚙️ Alert Rule Configuration

```json
{
  "name": "High Idle Alert",
  "alert_type": "excessive_idle",
  "severity": "medium",
  "config_json": {
    "threshold_seconds": 7200
  },
  "notify_manager": true
}
```

## 📊 Running Alert Processor

Add a cron job or background task to run the alert processor:

```python
from app.services.alert_processor import run_alert_processor
from app.core.database import SessionLocal

# Run every 30 minutes
db = SessionLocal()
run_alert_processor(db, org_id=1)
db.close()
```

Or use Celery:

```python
@celery.task
def process_alerts():
    db = SessionLocal()
    orgs = db.query(Organization).all()
    for org in orgs:
        run_alert_processor(db, org.id)
    db.close()
```

## 🔧 Getting Started

Same as Phase 1, plus:

1. Apply new database migrations for alerts tables
2. Configure alert rules via manager portal
3. Set up background task for alert processing

## 📄 License

Proprietary - All rights reserved.
