from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import guard_production, require
from ..models import AuditLog, FeatureRollout, User
from ..schemas import RollbackIn, RolloutOut, RolloutUpdate
from ..services import audit, evaluation
from ..services.rollouts import apply_snapshot, rollout_out, snapshot

router = APIRouter(prefix="/rollouts", tags=["Rollouts"])

ROLLBACKABLE = ("toggle", "update_rollout", "scheduled_activation", "scheduled_deactivation", "rollback")


def _get(db: Session, rollout_id: int) -> FeatureRollout:
    r = db.get(FeatureRollout, rollout_id)
    if not r:
        raise HTTPException(404, "Rollout not found")
    return r


@router.put("/{rollout_id}", response_model=RolloutOut,
            summary="Update enabled / percentage / schedule for a flag in one environment")
def update_rollout(rollout_id: int, body: RolloutUpdate, db: Session = Depends(get_db),
                   user: User = Depends(require("rollouts:write"))):
    r = _get(db, rollout_id)
    guard_production(user, r.environment)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(400, "No fields supplied")
    before = snapshot(r)
    if changes.get("enabled") is not None:
        r.enabled = changes["enabled"]
    if changes.get("rollout_percentage") is not None:
        r.rollout_percentage = changes["rollout_percentage"]
    for f in ("scheduled_enable_at", "scheduled_disable_at"):
        if f in changes:
            setattr(r, f, changes[f])
    if r.scheduled_enable_at and r.scheduled_disable_at and r.scheduled_disable_at <= r.scheduled_enable_at:
        raise HTTPException(422, "scheduled_disable_at must be after scheduled_enable_at")
    after = snapshot(r)
    if before == after:
        return rollout_out(r)
    r.version += 1
    r.updated_by = user.id
    only_toggle = set(k for k in after if after[k] != before[k]) == {"enabled"}
    audit.log(db, user, "toggle" if only_toggle else "update_rollout", "rollout", r.id, r.flag, r.environment,
              before, after)
    db.commit()
    evaluation.invalidate(r.environment_id, r.flag.key)
    return rollout_out(r)


@router.post("/{rollout_id}/rollback", response_model=RolloutOut,
             summary="Undo a change (defaults to the most recent change)")
def rollback(rollout_id: int, body: RollbackIn, db: Session = Depends(get_db),
             user: User = Depends(require("rollouts:rollback"))):
    r = _get(db, rollout_id)
    guard_production(user, r.environment)
    q = select(AuditLog).where(AuditLog.entity_type == "rollout", AuditLog.entity_id == r.id,
                               AuditLog.action.in_(ROLLBACKABLE))
    if body.audit_log_id:
        entry = db.scalar(q.where(AuditLog.id == body.audit_log_id))
    else:
        entry = db.scalar(q.order_by(AuditLog.id.desc()).limit(1))
    if not entry or not entry.before:
        raise HTTPException(404, "No change available to roll back")
    current = snapshot(r)
    apply_snapshot(r, entry.before)
    r.version += 1
    r.updated_by = user.id
    audit.log(db, user, "rollback", "rollout", r.id, r.flag, r.environment, current, snapshot(r))
    db.commit()
    evaluation.invalidate(r.environment_id, r.flag.key)
    return rollout_out(r)
