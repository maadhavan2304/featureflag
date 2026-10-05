# Flagship — Feature Flag & Environment Management System

A central console for controlling application features **without redeploying**. Admins flip flags, roll features out to a percentage of users, schedule launches, and undo mistakes. Client apps ask the API whether a feature is on for a given user.

| Layer | Stack |
|---|---|
| Backend | Python 3.14, FastAPI, SQLAlchemy 2, Alembic, PyJWT, Redis |
| Frontend | React (Vite) + TypeScript, Material UI, Axios, React Router, Chart.js |
| Database | MySQL 8.0 |

## Features

| Requirement | Where it lives |
|---|---|
| Secure login, JWT | `POST /auth/login` (access + refresh tokens, bcrypt hashes), `POST /auth/refresh`; the React app refreshes tokens automatically |
| Role-based access control | Roles hold permission strings (`flags:write`, `production:write`, …). Seeded roles: **admin**, **developer**, **viewer** |
| Flag creation and management | `/flags` CRUD, archive/restore, per-flag history |
| Enable / disable | `PUT /rollouts/{id}` `{"enabled": true}` |
| Scheduled activation | `scheduled_enable_at` / `scheduled_disable_at`; a background worker applies them (every 30 s) and logs them |
| Environments | Development, Testing, Production seeded; add more. Each has its own flag state and SDK key |
| Percentage rollouts | `rollout_percentage` 0–100, deterministic per user (SHA-256 of `flag_key:user_id`), so a user never flip-flops |
| User-specific access | Per-user **allow** (overrides off / percentage) and **deny** lists |
| Usage analytics | Every SDK evaluation is counted (Redis counters flushed to MySQL), charted per flag and on the dashboard |
| Rollback | Every rollout change stores before/after. "Undo last change" or undo any specific entry |
| Audit logs | All writes, scheduler actions, and logins; filterable, with before/after JSON |
| Dashboard | Totals, flags per environment, rollout distribution, 7-day usage, top flags, recent changes |

**Evaluation order:** archived → user deny → user allow → global switch → percentage rollout.
A percentage rollout needs a `user_id`; without one the flag evaluates to off unless it is at 100%.

**Production guard:** changes to an environment marked `is_production` need the `production:write` permission (admin only by default). Developers can freely work in dev and testing.

## Project layout

```
backend/
  app/
    main.py  config.py  database.py  models.py  schemas.py  security.py  deps.py
    redis_client.py  scheduler.py  seed.py
    routers/   auth users environments flags rollouts assignments audit_logs analytics sdk
    services/  evaluation.py (rules + cache + usage)  rollouts.py  audit.py
  alembic/     migrations (0001 creates all tables)
  tests/       pytest API tests (SQLite, no Redis needed)
frontend/      React + Vite + TypeScript
postman/       feature-flag.postman_collection.json (+ build.py that generates it)
docs/          openapi.json (export of the Swagger spec)
database/      init.sql (only if you are not using Docker)
docker-compose.yml   MySQL 8.0 + Redis 7
```

## Database

Seven required tables plus one for analytics:

`users`, `roles`, `feature_flags`, `environments`, `feature_rollouts`, `user_assignments`, `audit_logs` — and `feature_usage` (daily evaluation counters).

`feature_rollouts` holds one row per flag **per environment** (enabled, percentage, schedule, version). Creating a flag or environment creates the missing rows automatically.

## Setup

Prerequisites: Python 3.14, Node 20+, Docker (or a local MySQL 8.0 and Redis).

### 1. Database and Redis

```bash
docker compose up -d
```

No Docker? Run `database/init.sql` in MySQL Workbench and start Redis yourself. Redis is optional: without it the API still works, just uncached.

### 2. Backend

```bash
cd backend
python3.14 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # set JWT_SECRET to a long random string (32+ chars)
alembic upgrade head            # create tables
python -m app.seed              # roles, 3 environments, admin user, 3 demo flags
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs (click **Authorize**, log in with the admin account)
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health

Default admin: `admin` / `Admin@12345` (change via `.env` before seeding, and change the password afterwards).

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env            # VITE_API_URL=http://localhost:8000/api/v1
npm run dev                     # http://localhost:5173
```

### 4. Tests

```bash
cd backend && pytest -q
```

Covers login, RBAC, production guard, sticky percentage bucketing, allow/deny, rollback, scheduling, and analytics.

## Using flags from an application

Copy an environment's SDK key from the **Environments** page, then:

```bash
curl -X POST http://localhost:8000/api/v1/sdk/evaluate \
  -H "X-SDK-Key: sdk_production_..." -H "Content-Type: application/json" \
  -d '{"flag_key": "new-checkout", "user_id": "user-123"}'
# {"flag_key":"new-checkout","enabled":true,"reason":"in_rollout"}

curl "http://localhost:8000/api/v1/sdk/flags?user_id=user-123" -H "X-SDK-Key: sdk_production_..."
# {"environment":"production","user_id":"user-123","flags":{"new-checkout":true,"dark-mode":false}}
```

Rotate a key any time; the old key stops working immediately.

## Postman

Import `postman/feature-flag.postman_collection.json`. Run **Auth → Login** first; it stores the tokens. **Environments → List** stores an SDK key for the SDK requests. Creating a flag stores `flagId` and `rolloutId` for the following requests.

## Roles and permissions

| Permission | admin | developer | viewer |
|---|:-:|:-:|:-:|
| View flags, environments, analytics, audit | ✔ | ✔ | ✔ |
| Create / edit / archive / delete flags | ✔ | ✔ | |
| Toggle, percentage, schedule (non-production) | ✔ | ✔ | |
| Roll back, manage user access | ✔ | ✔ | |
| Anything in production (`production:write`) | ✔ | | |
| Manage environments, view SDK keys | ✔ | | |
| Manage users | ✔ | | |

Roles are rows in the `roles` table, so you can add custom ones by inserting a role with a permission list.

## Design notes and production checklist

- **Caching:** each flag/environment config is cached in Redis for 60 s and invalidated on every change. Usage counters use `HINCRBY` and are flushed to MySQL by the scheduler.
- **Scheduler:** runs inside the API process. A Redis lock stops several workers from applying the same change. Without Redis, run a single worker.
- **Schedule times:** stored in UTC; the UI shows and edits them in the browser's local time.
- **Rollback** restores enabled / percentage / schedule. It does not restore flag name or user allow/deny lists (those are visible in the audit log).
- Before going live: set a strong `JWT_SECRET`, restrict `CORS_ORIGINS`, serve over HTTPS, and add rate limiting on `/auth/login` and `/sdk/*` at your gateway.
