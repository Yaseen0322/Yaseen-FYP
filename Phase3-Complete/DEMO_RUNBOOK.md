# Demo Runbook

## Startup Order

Validated local staging order:

1. `cd Phase3-Complete`
2. `./run-demo.sh --reset-demo-db`
3. Load the browser extension from `Phase3-Complete/browser-extension`
4. Launch the desktop app on a machine with a GUI session

Headless validation path used in this environment:

```bash
cd Phase3-Complete
./run-demo.sh --reset-demo-db --skip-desktop
```

Stop everything with:

```bash
./stop-demo.sh
```

## Validated Demo Scenario

This flow was executed successfully against the live local stack with the isolated demo database.

1. Register the first admin user through `POST /api/v1/auth/register`
2. Log in as admin through `POST /api/v1/auth/login`
3. Verify paginated user listing with `GET /api/v1/users/?limit=1&offset=0`
4. Create one employee through `POST /api/v1/users/`
5. Verify paginated employee listing with `GET /api/v1/manager/employees?limit=1&offset=0`
6. Create and edit one domain rule through `/api/v1/manager/domain-rules`
7. Log in as the employee
8. Register one device through `POST /api/v1/devices/register`
9. Ingest app usage, idle time, and browser usage through `/api/v1/ingest/*`
10. Verify employee summary through `GET /api/v1/me/summary`
11. Verify manager employee summary and paginated timeline through `/api/v1/manager/employees/{id}/*`
12. Create an alert rule through `POST /api/v1/alerts/rules`
13. Trigger alert evaluation through `POST /api/v1/alerts/process`
14. Verify paginated alert visibility through `GET /api/v1/alerts/?limit=1&offset=0`
15. Mark the alert as read
16. Verify the manager portal responds on `http://127.0.0.1:3000`

## Expected Outcomes

- Backend health: `{"status":"healthy"}`
- Webcam health: `{"status":"healthy","detection_running":true}`
- Manager portal: HTTP `200`
- Employee summary after ingest:
  - `focus_sec = 600`
  - `idle_sec = 120`
  - `unproductive_sec = 300`
- Manager employee summary matches employee focus time
- Manager timeline is paginated and returned `total = 2` in the validated scenario
- Alert processing created `1` alert
- Alerts listing returned `total = 1`

## Important Demo Notes

- `run-demo.sh` uses an isolated SQLite file at `Phase3-Complete/backend/demo_staging.db`
- Use `--reset-demo-db` before a clean demo run
- The current client-facing day boundary follows `DEFAULT_TIMEZONE` (`Asia/Karachi` by default):
  - desktop dashboard and timeline request the local calendar date
  - manager employee detail uses the same local date picker behavior
  - backend default “today” summary behavior follows the configured timezone
- Desktop dashboard and timeline include live local activity, idle, presence, and browser-extension data before the next backend sync.
- Jira automatic sync/worklog export is intentionally not part of the demo
- Slack alert delivery requires the worker to be running and valid Slack credentials configured

## Recovery Steps

- Backend fails to start:
  - run `./stop-demo.sh`
  - rerun `./run-demo.sh --reset-demo-db`
  - inspect `.demo-logs/backend.log`
- Worker fails:
  - inspect `.demo-logs/alert-worker.log`
  - restart with `./run-demo.sh --reset-demo-db`
- Webcam service fails:
  - inspect `.demo-logs/webcam.log`
  - rerun with `--skip-webcam` if webcam presence is not part of the demo
- Manager portal fails:
  - inspect `.demo-logs/manager-portal.log`
  - verify `npm install` has completed in `manager-portal`
- Desktop app fails in a headless environment:
  - rerun with `--skip-desktop`
  - present the manager portal and API-backed flow only

## Not Validated Here

- Manual Electron desktop interaction in a real GUI session
- Manual browser-extension capture inside Chrome/Edge during a live browsing session
- Real Slack webhook delivery over the network
