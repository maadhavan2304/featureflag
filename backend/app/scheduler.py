"""Background loop: applies scheduled activations/deactivations and flushes usage counters."""
import asyncio
import logging

from sqlalchemy import or_, select

from .config import settings
from .database import SessionLocal
from .models import FeatureRollout, utcnow
from .services import audit, evaluation
from .services.rollouts import snapshot
from . import redis_client as rc

log = logging.getLogger("scheduler")


def apply_due_schedules(db) -> int:
    now = utcnow()
    due = db.scalars(select(FeatureRollout).where(
        or_(FeatureRollout.scheduled_enable_at <= now, FeatureRollout.scheduled_disable_at <= now)
    )).all()
    for r in due:
        before = snapshot(r)
        events = []
        if r.scheduled_enable_at and r.scheduled_enable_at <= now:
            events.append((r.scheduled_enable_at, True))
        if r.scheduled_disable_at and r.scheduled_disable_at <= now:
            events.append((r.scheduled_disable_at, False))
        events.sort(key=lambda e: e[0])  # if both are overdue, the later one wins
        r.enabled = events[-1][1]
        if r.scheduled_enable_at and r.scheduled_enable_at <= now:
            r.scheduled_enable_at = None
        if r.scheduled_disable_at and r.scheduled_disable_at <= now:
            r.scheduled_disable_at = None
        r.version += 1
        r.updated_by = None
        audit.log(db, None, "scheduled_activation" if r.enabled else "scheduled_deactivation", "rollout",
                  r.id, r.flag, r.environment, before, snapshot(r))
    if due:
        db.commit()
        for r in due:
            evaluation.invalidate(r.environment_id, r.flag.key)
    return len(due)


def tick() -> None:
    redis = rc.get_redis()
    if redis:  # simple distributed lock so only one worker runs the tick
        try:
            if not redis.set("ff:scheduler:lock", "1", nx=True, ex=max(5, settings.SCHEDULER_INTERVAL_SECONDS - 2)):
                return
        except Exception:
            pass
    db = SessionLocal()
    try:
        n = apply_due_schedules(db)
        if n:
            log.info("applied %d scheduled rollout change(s)", n)
        evaluation.flush_usage(db)
    except Exception:
        log.exception("scheduler tick failed")
        db.rollback()
    finally:
        db.close()


async def run_forever() -> None:
    while True:
        await asyncio.to_thread(tick)
        await asyncio.sleep(settings.SCHEDULER_INTERVAL_SECONDS)
