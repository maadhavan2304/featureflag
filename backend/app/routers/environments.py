import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import has_permission, require
from ..models import Environment, User
from ..schemas import EnvironmentCreate, EnvironmentOut, EnvironmentUpdate
from ..services import audit
from ..services.rollouts import ensure_rollouts_for_env

router = APIRouter(prefix="/environments", tags=["Environments"])


def new_sdk_key(env_key: str) -> str:
    return f"sdk_{env_key}_{secrets.token_urlsafe(24)}"


def _out(env: Environment, user: User) -> EnvironmentOut:
    out = EnvironmentOut.model_validate(env, from_attributes=True)
    if not has_permission(user, "environments:manage"):
        out.sdk_key = None
    return out


@router.get("", response_model=list[EnvironmentOut], summary="List environments")
def list_environments(db: Session = Depends(get_db), user: User = Depends(require("environments:read"))):
    return [_out(e, user) for e in db.scalars(select(Environment).order_by(Environment.id)).all()]


@router.post("", response_model=EnvironmentOut, status_code=201, summary="Create an environment")
def create_environment(body: EnvironmentCreate, db: Session = Depends(get_db),
                       user: User = Depends(require("environments:manage"))):
    if db.scalar(select(Environment).where(Environment.key == body.key)):
        raise HTTPException(409, "Environment key already exists")
    env = Environment(name=body.name, key=body.key, description=body.description,
                      is_production=body.is_production, sdk_key=new_sdk_key(body.key))
    db.add(env)
    db.flush()
    ensure_rollouts_for_env(db, env)  # every existing flag gets a (disabled) rollout here
    audit.log(db, user, "create_environment", "environment", env.id, env=env, after={"key": env.key})
    db.commit()
    return _out(env, user)


@router.patch("/{env_id}", response_model=EnvironmentOut, summary="Update an environment")
def update_environment(env_id: int, body: EnvironmentUpdate, db: Session = Depends(get_db),
                       user: User = Depends(require("environments:manage"))):
    env = db.get(Environment, env_id)
    if not env:
        raise HTTPException(404, "Environment not found")
    before = {"name": env.name, "description": env.description, "is_production": env.is_production}
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(env, k, v)
    audit.log(db, user, "update_environment", "environment", env.id, env=env, before=before,
              after={"name": env.name, "description": env.description, "is_production": env.is_production})
    db.commit()
    return _out(env, user)


@router.post("/{env_id}/rotate-sdk-key", response_model=EnvironmentOut, summary="Generate a new SDK key")
def rotate_sdk_key(env_id: int, db: Session = Depends(get_db), user: User = Depends(require("environments:manage"))):
    env = db.get(Environment, env_id)
    if not env:
        raise HTTPException(404, "Environment not found")
    env.sdk_key = new_sdk_key(env.key)
    audit.log(db, user, "rotate_sdk_key", "environment", env.id, env=env)
    db.commit()
    return _out(env, user)
