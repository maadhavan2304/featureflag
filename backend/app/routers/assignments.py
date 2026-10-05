from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import guard_production, require
from ..models import Environment, FeatureFlag, User, UserAssignment
from ..schemas import AssignmentCreate, AssignmentOut
from ..services import audit, evaluation

router = APIRouter(tags=["User Assignments"])


@router.get("/flags/{flag_id}/assignments", response_model=list[AssignmentOut],
            summary="List user-specific allow/deny entries")
def list_assignments(flag_id: int, environment_id: Optional[int] = None, db: Session = Depends(get_db),
                     _: User = Depends(require("flags:read"))):
    q = select(UserAssignment).where(UserAssignment.flag_id == flag_id).order_by(UserAssignment.id.desc())
    if environment_id:
        q = q.where(UserAssignment.environment_id == environment_id)
    return db.scalars(q).all()


@router.post("/flags/{flag_id}/assignments", response_model=AssignmentOut, status_code=201,
             summary="Allow or deny a specific user (upsert)")
def upsert_assignment(flag_id: int, body: AssignmentCreate, db: Session = Depends(get_db),
                      user: User = Depends(require("assignments:write"))):
    flag, env = db.get(FeatureFlag, flag_id), db.get(Environment, body.environment_id)
    if not flag or not env:
        raise HTTPException(404, "Flag or environment not found")
    guard_production(user, env)
    row = db.scalar(select(UserAssignment).where(
        UserAssignment.flag_id == flag_id, UserAssignment.environment_id == env.id,
        UserAssignment.user_identifier == body.user_identifier))
    before = {"access": row.access} if row else None
    if row:
        row.access = body.access
    else:
        row = UserAssignment(flag_id=flag_id, environment_id=env.id, user_identifier=body.user_identifier,
                             access=body.access, created_by=user.id)
        db.add(row)
        db.flush()
    audit.log(db, user, "assign_user", "assignment", row.id, flag, env, before,
              {"user": row.user_identifier, "access": row.access})
    db.commit()
    evaluation.invalidate(env.id, flag.key)
    return row


@router.delete("/assignments/{assignment_id}", status_code=204, summary="Remove a user-specific entry")
def delete_assignment(assignment_id: int, db: Session = Depends(get_db),
                      user: User = Depends(require("assignments:write"))):
    row = db.get(UserAssignment, assignment_id)
    if not row:
        raise HTTPException(404, "Assignment not found")
    flag, env = db.get(FeatureFlag, row.flag_id), db.get(Environment, row.environment_id)
    guard_production(user, env)
    audit.log(db, user, "unassign_user", "assignment", row.id, flag, env,
              {"user": row.user_identifier, "access": row.access}, None)
    db.delete(row)
    db.commit()
    evaluation.invalidate(env.id, flag.key)
