import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import Environment, User
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Permission catalogue. Roles store a list of these strings ("*" = everything).
PERMISSIONS = {
    "flags:read": "View flags and rollout state",
    "flags:write": "Create, edit, archive and delete flags",
    "rollouts:write": "Toggle flags, change percentages and schedules (non-production)",
    "rollouts:rollback": "Roll back a rollout change",
    "assignments:write": "Manage user-specific access",
    "production:write": "Change anything in production environments",
    "environments:read": "View environments",
    "environments:manage": "Create/edit environments and view SDK keys",
    "analytics:read": "View dashboard and usage analytics",
    "audit:read": "View audit logs and change history",
    "users:manage": "Manage users",
}

DEFAULT_ROLES = {
    "admin": ("Full access", ["*"]),
    "developer": (
        "Manage flags and rollouts outside production",
        ["flags:read", "flags:write", "rollouts:write", "rollouts:rollback", "assignments:write",
         "environments:read", "analytics:read", "audit:read"],
    ),
    "viewer": ("Read-only access", ["flags:read", "environments:read", "analytics:read", "audit:read"]),
}


def has_permission(user: User, perm: str) -> bool:
    perms = user.role.permissions or []
    return "*" in perms or perm in perms


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    err = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    try:
        user_id = decode_token(token, "access")
    except (jwt.PyJWTError, ValueError):
        raise err
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise err
    return user


def require(perm: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user, perm):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Missing permission: {perm}")
        return user
    return checker


def guard_production(user: User, env: Environment) -> None:
    if env.is_production and not has_permission(user, "production:write"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only users with production:write can change production")


def get_sdk_environment(x_sdk_key: str = Header(..., description="Environment SDK key"),
                        db: Session = Depends(get_db)) -> Environment:
    env = db.scalar(select(Environment).where(Environment.sdk_key == x_sdk_key))
    if not env:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid SDK key")
    return env
