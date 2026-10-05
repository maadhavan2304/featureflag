import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import analytics, assignments, audit_logs, auth, environments, flags, rollouts, sdk, users
from .scheduler import run_forever

DESCRIPTION = """
Centralised feature flag and environment management.

**Admin API** (JWT): authenticate via `POST /api/v1/auth/login`, then click **Authorize** above.

**SDK API** (`/api/v1/sdk/*`): used by your applications; authenticated with the `X-SDK-Key` header of an environment.

Evaluation order: archived → user deny list → user allow list → global switch → percentage rollout.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(run_forever()) if settings.ENABLE_SCHEDULER else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="Feature Flag & Environment Management API", version="1.0.0",
              description=DESCRIPTION, lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

for module in (auth, users, environments, flags, rollouts, assignments, audit_logs, analytics, sdk):
    app.include_router(module.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health():
    from .redis_client import get_redis
    return {"status": "ok", "redis": "up" if get_redis() else "down (running without cache)"}
