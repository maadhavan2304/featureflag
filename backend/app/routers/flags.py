from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require
from ..models import AuditLog, Environment, FeatureFlag, User
from ..schemas import AuditOut, EvaluateOut, FlagCreate, FlagOut, FlagUpdate
from ..services import audit, evaluation
from ..services.rollouts import ensure_rollouts_for_flag, flag_out

router = APIRouter(prefix="/flags", tags=["Feature Flags"])


@router.get("", response_model=list[FlagOut], summary="List flags with per-environment state")
def list_flags(search: Optional[str] = None, include_archived: bool = False, db: Session = Depends(get_db),
               _: User = Depends(require("flags:read"))):
    q = select(FeatureFlag).order_by(FeatureFlag.created_at.desc())
    if not include_archived:
        q = q.where(FeatureFlag.is_archived.is_(False))
    if search:
        like = f"%{search}%"
        q = q.where(or_(FeatureFlag.key.like(like), FeatureFlag.name.like(like)))
    return [flag_out(f) for f in db.scalars(q).unique().all()]


@router.post("", response_model=FlagOut, status_code=201, summary="Create a flag")
def create_flag(body: FlagCreate, db: Session = Depends(get_db), user: User = Depends(require("flags:write"))):
    if db.scalar(select(FeatureFlag).where(FeatureFlag.key == body.key)):
        raise HTTPException(409, "A flag with this key already exists")
    flag = FeatureFlag(key=body.key, name=body.name, description=body.description, created_by=user.id)
    db.add(flag)
    db.flush()
    ensure_rollouts_for_flag(db, flag)
    audit.log(db, user, "create_flag", "flag", flag.id, flag=flag, after={"key": flag.key, "name": flag.name})
    db.commit()
    db.refresh(flag)
    return flag_out(flag)


@router.get("/{flag_id}", response_model=FlagOut, summary="Get a flag")
def get_flag(flag_id: int, db: Session = Depends(get_db), _: User = Depends(require("flags:read"))):
    flag = db.get(FeatureFlag, flag_id)
    if not flag:
        raise HTTPException(404, "Flag not found")
    return flag_out(flag)


@router.patch("/{flag_id}", response_model=FlagOut, summary="Edit or archive/unarchive a flag")
def update_flag(flag_id: int, body: FlagUpdate, db: Session = Depends(get_db),
                user: User = Depends(require("flags:write"))):
    flag = db.get(FeatureFlag, flag_id)
    if not flag:
        raise HTTPException(404, "Flag not found")
    before = {"name": flag.name, "description": flag.description, "is_archived": flag.is_archived}
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(flag, k, v)
    after = {"name": flag.name, "description": flag.description, "is_archived": flag.is_archived}
    action = "archive_flag" if after["is_archived"] and not before["is_archived"] else \
             "unarchive_flag" if before["is_archived"] and not after["is_archived"] else "update_flag"
    audit.log(db, user, action, "flag", flag.id, flag=flag, before=before, after=after)
    db.commit()
    evaluation.invalidate(None, flag.key)
    db.refresh(flag)
    return flag_out(flag)


@router.delete("/{flag_id}", status_code=204, summary="Permanently delete a flag")
def delete_flag(flag_id: int, db: Session = Depends(get_db), user: User = Depends(require("flags:write"))):
    flag = db.get(FeatureFlag, flag_id)
    if not flag:
        raise HTTPException(404, "Flag not found")
    audit.log(db, user, "delete_flag", "flag", flag.id, flag=flag,
              before={"key": flag.key, "name": flag.name, "description": flag.description})
    key = flag.key
    db.delete(flag)
    db.commit()
    evaluation.invalidate(None, key)


@router.get("/{flag_id}/history", response_model=list[AuditOut], summary="Change history for one flag")
def flag_history(flag_id: int, limit: int = Query(100, le=500), db: Session = Depends(get_db),
                 _: User = Depends(require("audit:read"))):
    q = select(AuditLog).where(AuditLog.flag_id == flag_id).order_by(AuditLog.id.desc()).limit(limit)
    return db.scalars(q).all()


@router.get("/{flag_id}/test-evaluate", response_model=EvaluateOut,
            summary="Dry-run evaluation (not counted in analytics)")
def test_evaluate(flag_id: int, environment_id: int, user_id: Optional[str] = None, db: Session = Depends(get_db),
                  _: User = Depends(require("flags:read"))):
    flag = db.get(FeatureFlag, flag_id)
    env = db.get(Environment, environment_id)
    if not flag or not env:
        raise HTTPException(404, "Flag or environment not found")
    enabled, reason = evaluation.evaluate_config(flag.key, evaluation.load_config(db, env.id, flag.key), user_id)
    return EvaluateOut(flag_key=flag.key, enabled=enabled, reason=reason)
