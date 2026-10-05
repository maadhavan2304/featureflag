from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require
from ..models import AuditLog, User
from ..schemas import AuditPage

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=AuditPage, summary="Search the audit trail")
def list_audit_logs(flag_id: Optional[int] = None, environment_id: Optional[int] = None,
                    user_id: Optional[int] = None, action: Optional[str] = None,
                    limit: int = Query(25, ge=1, le=200), offset: int = Query(0, ge=0),
                    db: Session = Depends(get_db), _: User = Depends(require("audit:read"))):
    q = select(AuditLog)
    for col, val in ((AuditLog.flag_id, flag_id), (AuditLog.environment_id, environment_id),
                     (AuditLog.user_id, user_id), (AuditLog.action, action)):
        if val is not None:
            q = q.where(col == val)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.order_by(AuditLog.id.desc()).limit(limit).offset(offset)).all()
    return AuditPage(items=items, total=total)
