"""Endpoints called by your applications (authenticated with an environment SDK key)."""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_sdk_environment
from ..models import Environment, FeatureFlag, FeatureRollout, UserAssignment
from ..schemas import EvaluateIn, EvaluateOut
from ..services import evaluation

router = APIRouter(prefix="/sdk", tags=["SDK (client applications)"])


@router.post("/evaluate", response_model=EvaluateOut, summary="Evaluate one flag for a user")
def evaluate(body: EvaluateIn, env: Environment = Depends(get_sdk_environment), db: Session = Depends(get_db)):
    cfg = evaluation.load_config(db, env.id, body.flag_key)
    enabled, reason = evaluation.evaluate_config(body.flag_key, cfg, body.user_id)
    if cfg:
        evaluation.record_usage(db, cfg["flag_id"], env.id, enabled)
    return EvaluateOut(flag_key=body.flag_key, enabled=enabled, reason=reason)


@router.get("/flags", summary="Evaluate every flag for a user in one call")
def evaluate_all(user_id: Optional[str] = None, env: Environment = Depends(get_sdk_environment),
                 db: Session = Depends(get_db)):
    flags = db.scalars(select(FeatureFlag).where(FeatureFlag.is_archived.is_(False))).unique().all()
    assigns: dict[int, dict[str, list[str]]] = {}
    for a in db.scalars(select(UserAssignment).where(UserAssignment.environment_id == env.id)).all():
        assigns.setdefault(a.flag_id, {"allow": [], "deny": []})[a.access].append(a.user_identifier)
    result = {}
    for f in flags:
        r = next((x for x in f.rollouts if x.environment_id == env.id), None)
        if not r:
            continue
        a = assigns.get(f.id, {"allow": [], "deny": []})
        cfg = {"flag_id": f.id, "archived": False, "enabled": r.enabled, "percentage": r.rollout_percentage, **a}
        enabled, _ = evaluation.evaluate_config(f.key, cfg, user_id)
        result[f.key] = enabled
        evaluation.record_usage(db, f.id, env.id, enabled)
    return {"environment": env.key, "user_id": user_id, "flags": result}
