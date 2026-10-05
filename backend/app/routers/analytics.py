from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require
from ..models import AuditLog, Environment, FeatureFlag, FeatureRollout, FeatureUsage, User
from ..schemas import AuditOut
from ..services import evaluation

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _series(db: Session, days: int, flag_id: Optional[int] = None, env_id: Optional[int] = None):
    evaluation.flush_usage(db)
    start = date.today() - timedelta(days=days - 1)
    q = select(FeatureUsage).where(FeatureUsage.usage_date >= start)
    if flag_id:
        q = q.where(FeatureUsage.flag_id == flag_id)
    if env_id:
        q = q.where(FeatureUsage.environment_id == env_id)
    rows = db.scalars(q).all()
    per_day = defaultdict(lambda: [0, 0])
    for r in rows:
        per_day[r.usage_date][0] += r.evaluations
        per_day[r.usage_date][1] += r.enabled_count
    points = []
    for i in range(days):
        d = start + timedelta(days=i)
        points.append({"date": d.isoformat(), "evaluations": per_day[d][0], "enabled_count": per_day[d][1]})
    return rows, points


@router.get("/usage", summary="Evaluation counts per day")
def usage(flag_id: Optional[int] = None, environment_id: Optional[int] = None, days: int = Query(7, ge=1, le=90),
          db: Session = Depends(get_db), _: User = Depends(require("analytics:read"))):
    rows, points = _series(db, days, flag_id, environment_id)
    total = sum(p["evaluations"] for p in points)
    on = sum(p["enabled_count"] for p in points)
    return {"series": points, "total_evaluations": total, "enabled_evaluations": on,
            "enabled_rate": round(on / total * 100, 1) if total else 0}


@router.get("/dashboard", summary="Numbers for the dashboard")
def dashboard(db: Session = Depends(get_db), _: User = Depends(require("analytics:read"))):
    flags = db.scalars(select(FeatureFlag)).unique().all()
    envs = db.scalars(select(Environment).order_by(Environment.id)).all()
    rollouts = db.scalars(select(FeatureRollout)).unique().all()
    archived_ids = {f.id for f in flags if f.is_archived}
    live = [r for r in rollouts if r.flag_id not in archived_ids]

    per_env = []
    for e in envs:
        rs = [r for r in live if r.environment_id == e.id]
        on = [r for r in rs if r.enabled]
        per_env.append({
            "environment_id": e.id, "key": e.key, "name": e.name, "is_production": e.is_production,
            "enabled": len(on), "disabled": len(rs) - len(on),
            "partial": len([r for r in on if r.rollout_percentage < 100]),
        })

    buckets = {"0%": 0, "1-25%": 0, "26-50%": 0, "51-99%": 0, "100%": 0}
    for r in live:
        if not r.enabled:
            continue
        p = r.rollout_percentage
        key = "0%" if p == 0 else "1-25%" if p <= 25 else "26-50%" if p <= 50 else "51-99%" if p < 100 else "100%"
        buckets[key] += 1

    _, points = _series(db, 7)
    rows, _ = _series(db, 7)
    by_flag = defaultdict(int)
    for r in rows:
        by_flag[r.flag_id] += r.evaluations
    names = {f.id: f for f in flags}
    top = [{"flag_id": fid, "key": names[fid].key, "name": names[fid].name, "evaluations": n}
           for fid, n in sorted(by_flag.items(), key=lambda x: -x[1])[:5] if fid in names]

    recent = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(8)).all()
    return {
        "totals": {
            "flags": len(flags) - len(archived_ids),
            "archived": len(archived_ids),
            "enabled_somewhere": len({r.flag_id for r in live if r.enabled}),
            "scheduled": len([r for r in live if r.scheduled_enable_at or r.scheduled_disable_at]),
            "partial_rollouts": len([r for r in live if r.enabled and r.rollout_percentage < 100]),
            "environments": len(envs),
        },
        "environments": per_env,
        "rollout_distribution": buckets,
        "usage_7d": points,
        "top_flags": top,
        "recent_activity": [AuditOut.model_validate(a).model_dump(mode="json") for a in recent],
    }
