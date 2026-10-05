from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Environment, FeatureFlag, FeatureRollout, User
from ..schemas import FlagOut, RolloutOut
from . import audit


def iso(d: Optional[datetime]) -> Optional[str]:
    return d.isoformat() if d else None


def snapshot(r: FeatureRollout) -> dict:
    return {
        "enabled": r.enabled,
        "rollout_percentage": r.rollout_percentage,
        "scheduled_enable_at": iso(r.scheduled_enable_at),
        "scheduled_disable_at": iso(r.scheduled_disable_at),
    }


def apply_snapshot(r: FeatureRollout, snap: dict) -> None:
    r.enabled = bool(snap["enabled"])
    r.rollout_percentage = int(snap["rollout_percentage"])
    r.scheduled_enable_at = datetime.fromisoformat(snap["scheduled_enable_at"]) if snap.get("scheduled_enable_at") else None
    r.scheduled_disable_at = datetime.fromisoformat(snap["scheduled_disable_at"]) if snap.get("scheduled_disable_at") else None


def rollout_out(r: FeatureRollout) -> RolloutOut:
    e = r.environment
    return RolloutOut(
        id=r.id, flag_id=r.flag_id, environment_id=r.environment_id, environment_key=e.key,
        environment_name=e.name, is_production=e.is_production, enabled=r.enabled,
        rollout_percentage=r.rollout_percentage, scheduled_enable_at=r.scheduled_enable_at,
        scheduled_disable_at=r.scheduled_disable_at, version=r.version, updated_at=r.updated_at,
    )


def flag_out(f: FeatureFlag) -> FlagOut:
    rollouts = sorted(f.rollouts, key=lambda r: r.environment_id)
    return FlagOut(
        id=f.id, key=f.key, name=f.name, description=f.description, is_archived=f.is_archived,
        created_by=f.creator.username if f.creator else None, created_at=f.created_at,
        updated_at=f.updated_at, rollouts=[rollout_out(r) for r in rollouts],
    )


def ensure_rollouts_for_flag(db: Session, flag: FeatureFlag) -> None:
    for env in db.scalars(select(Environment)).all():
        db.add(FeatureRollout(flag=flag, environment_id=env.id, enabled=False, rollout_percentage=100))


def ensure_rollouts_for_env(db: Session, env: Environment) -> None:
    for flag in db.scalars(select(FeatureFlag)).all():
        db.add(FeatureRollout(flag_id=flag.id, environment_id=env.id, enabled=False, rollout_percentage=100))
