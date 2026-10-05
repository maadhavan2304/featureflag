from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models import AuditLog, Environment, FeatureFlag, User


def log(db: Session, user: Optional[User], action: str, entity_type: str, entity_id: Optional[int] = None,
        flag: Optional[FeatureFlag] = None, env: Optional[Environment] = None,
        before: Any = None, after: Any = None) -> AuditLog:
    """Adds an audit row to the current transaction (caller commits)."""
    row = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "scheduler",
        action=action, entity_type=entity_type, entity_id=entity_id,
        flag_id=flag.id if flag else None, flag_key=flag.key if flag else None,
        environment_id=env.id if env else None, environment_key=env.key if env else None,
        before=before, after=after,
    )
    db.add(row)
    return row
