# Phase 3 - Integrated Release Candidate: Privacy-Preserving Employee Activity Tracker

## 📋 Overview

Phase 3 is the integrated release-candidate version. Core tracking, reporting, dashboards, SSO, and admin flows are present, while third-party integrations and ML-assisted classification still require deployment-specific configuration and operational hardening before a true production rollout.

## 🎯 Complete Feature Set

### From Phase 1 (MVP)
- ✅ Employee agent auto-start
- ✅ App usage + idle tracking
- ✅ Webcam presence detection
- ✅ Browser extension + domain tracking
- ✅ Employee dashboard
- ✅ Manager dashboard

### From Phase 2 (Advanced)
- ✅ Department analytics & comparisons
- ✅ Alert system with rules and manual/worker execution
- ✅ Weekly trends

### Phase 3 (Integrated)
- ✅ **Slack Integration APIs/UI** - Configure, test, and deliver alert notifications when the worker is running
- ⚠️ **Jira Integration APIs/UI** - Configure and test Jira connectivity; automatic sync/export is not enabled in this release
- ✅ **Google SSO** - Single sign-on with Google Workspace
- ✅ **Microsoft SSO** - Single sign-on with Microsoft 365
- ✅ **ML Classification Review** - Unrecognized browser domains and desktop apps now generate review suggestions during ingest

## 🏗️ New in Phase 3

### Backend Additions

```
backend/app/
├── models/
│   └── integrations.py       # Integration, SSOProvider, MLClassification models
├── api/
│   ├── integrations.py       # Integration management API
│   └── sso_auth.py           # SSO authentication endpoints
└── services/
    ├── ml_classifier.py      # ML-based classification service
    ├── slack_notifier.py     # Slack notification service
    └── jira_integration.py   # Jira sync service
```

### Manager Portal Additions

```
manager-portal/src/pages/
├── Integrations.jsx          # Integration management UI
└── MLClassifications.jsx     # ML classification approval UI
```

## 🔗 Integrations

### Slack Integration

Send alert notifications to Slack channels.

**Configuration:**
```json
{
  "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
}
```

**Features:**
- Alert notifications from generated rules
- Connection testing from the admin UI
- Custom message formatting

**Runtime requirement:**

Run the operational worker to evaluate rules and send Slack notifications:

```bash
cd backend
python -m app.workers.operational_jobs --interval 300
```

### Jira Integration

Store Jira credentials securely and test API connectivity.

**Configuration:**
```json
{
  "api_url": "https://your-domain.atlassian.net",
  "email": "admin@company.com",
  "api_token": "your-api-token"
}
```

**Current release scope:**
- Admin configuration and connection tests
- Internal service hooks for future exports
- No automatic issue sync or worklog export in this release candidate

## 🔐 SSO Authentication

### Google SSO

**Configuration:**
1. Create OAuth 2.0 credentials in Google Cloud Console
2. Configure redirect URIs
3. Add client ID and secret to SSO provider

```json
{
  "client_id": "your-client-id.apps.googleusercontent.com",
  "client_secret": "your-client-secret",
  "domain": "company.com"  // Optional: restrict to domain
}
```

### Microsoft SSO

**Configuration:**
1. Register app in Azure AD
2. Configure redirect URIs
3. Add client ID, secret, and tenant ID

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "tenant_id": "your-tenant-id"
}
```

## 🤖 ML Classification

The ML classifier now generates review suggestions for uncategorized browser domains and desktop app names during ingest.

### How It Works

1. Browser/domain ingest checks explicit organization rules first
2. Unknown domains and app names are classified by the ML pattern service
3. Managers can review and approve or reject suggestions
4. Approved classifications are reused on future ingest

### Classification Categories

| Label | Description | Examples |
|-------|-------------|----------|
| Productive | Work-related | GitHub, VS Code, Slack |
| Unproductive | Entertainment | YouTube, Netflix, Games |
| Neutral | Undetermined | Unknown sites |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ml/classifications` | GET | List classifications |
| `/api/v1/ml/classifications/{id}/approve` | POST | Approve/correct |

## 🚀 Complete API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Email/password login
- `POST /api/v1/auth/register` - Register first user
- `GET /api/v1/sso/google/login` - Initiate Google SSO
- `GET /api/v1/sso/microsoft/login` - Initiate Microsoft SSO

### Integrations
- `GET /api/v1/integrations/` - List integrations
- `POST /api/v1/integrations/` - Create integration
- `POST /api/v1/integrations/{id}/toggle` - Enable/disable
- `POST /api/v1/integrations/{id}/test` - Test connection
- `GET /api/v1/integrations/sso` - List SSO providers
- `POST /api/v1/integrations/sso` - Create SSO provider

## 📦 Deployment Notes

### Example Docker Compose (Full Stack + Alert Worker)

```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
      - SECRET_KEY=...
    ports:
      - "8000:8000"

  alert-worker:
    build: ./backend
    command: python -m app.workers.operational_jobs --interval 300
    environment:
      - DATABASE_URL=postgresql://...
      - SECRET_KEY=...
  
  webcam-service:
    build: ./webcam-service
    ports:
      - "8001:8001"
  
  manager-portal:
    build: ./manager-portal
    ports:
      - "3000:80"
  
  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
```

### Environment Variables

```bash
# Core
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
SECRET_KEY=your-secret-key

# SSO (Optional)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
MICROSOFT_TENANT_ID=...
```

### Database Migrations

The backend no longer creates tables automatically on startup. Apply migrations before starting the API:

```bash
cd backend
alembic upgrade head
```

## 🔧 Setup Checklist

1. ☐ Deploy backend with PostgreSQL and Redis
2. ☐ Configure first admin user
3. ☐ Create departments
4. ☐ Add employees
5. ☐ Configure domain rules
6. ☐ (Optional) Set up Slack integration
7. ☐ (Optional) Set up Jira integration
8. ☐ (Optional) Configure SSO providers
9. ☐ Deploy desktop app to employees
10. ☐ Install browser extension
11. ☐ Run the alert worker for rule processing and Slack delivery

## 🧪 Local Staging Runbook

Use this order for supervised demo or internal staging on one machine:

1. Start PostgreSQL and Redis if you are not using the backend's local SQLite development mode.
2. Apply backend migrations before starting the API:

```bash
cd backend
alembic upgrade head
```

3. Start the backend API:

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

4. Start the alert worker in a separate terminal:

```bash
cd backend
python -m app.workers.operational_jobs --interval 30
```

5. Start the webcam service:

```bash
cd webcam-service
python main.py
```

6. Start the manager portal:

```bash
cd manager-portal
npm run dev -- --host 127.0.0.1 --port 3000
```

7. Start the desktop app in development mode:

```bash
cd desktop-app
npm run dev
```

8. Load the browser extension from `Phase3-Complete/browser-extension` after the desktop app is already running, so the local browser-usage receiver on `127.0.0.1:8080` is available.

For a one-command local demo bootstrap, use:

```bash
cd Phase3-Complete
./run-demo.sh --reset-demo-db
```

Stop the demo stack with:

```bash
./stop-demo.sh
```

Headless-safe validation path:

```bash
./run-demo.sh --reset-demo-db --skip-desktop
```

Notes:
- The helper script uses an isolated SQLite file at `backend/demo_staging.db`.
- Use `--reset-demo-db` before a clean demo run.
- The current client-facing date boundary is the UTC ISO day used by the desktop and manager UIs.
- For supervised demos, prefer `desktop-app` development mode over packaged installers. Packaged build assets are not part of the validated local demo path.
- Slack alert delivery requires the worker to be running.
- Jira remains configuration/test-only in this release candidate.

See [DEMO_RUNBOOK.md](./DEMO_RUNBOOK.md) for the validated smoke scenario, expected outcomes, and recovery steps.

## 📊 Monitoring

### Health Checks

- Backend: `GET /health`
- Webcam Service: `GET /health`

### Logs

All services log to stdout. Use your preferred log aggregation (ELK, CloudWatch, etc.)

## 🔒 Security Considerations

1. **Secrets Management**: Use environment variables or secret managers
2. **HTTPS**: Always use HTTPS in production
3. **CORS**: Configure allowed origins properly
4. **Rate Limiting**: Implement rate limiting for APIs
5. **Data Encryption**: Enable encryption at rest for database

## 📄 License

Proprietary - All rights reserved.

---

## 🎉 Congratulations!

You now have an integrated release candidate with:

- **Desktop tracking** - App usage, idle time, presence detection
- **Browser tracking** - Domain usage with privacy (no content)
- **Dashboards** - Employee personal + Manager team views
- **Analytics** - Department comparisons, trends, reports
- **Alerts** - Configurable rules with manual and worker-driven processing
- **Integrations** - Slack alert delivery, Jira connectivity testing, and SSO
- **AI Classification** - ML-assisted review suggestions for domains and apps

The system is designed with privacy as a core principle - no screenshots, no camera images, no keystroke content, just the essential metrics for productivity insights.
