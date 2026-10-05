from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import PERMISSIONS, get_current_user, require
from ..models import Role, User
from ..schemas import RoleOut, UserCreate, UserOut, UserUpdate
from ..security import hash_password
from ..services import audit

router = APIRouter(tags=["Users & Roles"])


@router.get("/roles", response_model=list[RoleOut], summary="List roles and their permissions")
def list_roles(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(Role).order_by(Role.id)).all()


@router.get("/permissions", summary="Permission catalogue")
def permissions(_: User = Depends(get_current_user)):
    return PERMISSIONS


@router.get("/users", response_model=list[UserOut], summary="List users")
def list_users(db: Session = Depends(get_db), _: User = Depends(require("users:manage"))):
    return db.scalars(select(User).order_by(User.id)).all()


@router.post("/users", response_model=UserOut, status_code=201, summary="Create a user")
def create_user(body: UserCreate, db: Session = Depends(get_db), actor: User = Depends(require("users:manage"))):
    if not db.get(Role, body.role_id):
        raise HTTPException(400, "Unknown role_id")
    if db.scalar(select(User).where((User.email == body.email) | (User.username == body.username))):
        raise HTTPException(409, "Email or username already exists")
    user = User(email=body.email, username=body.username, hashed_password=hash_password(body.password),
                role_id=body.role_id, is_active=body.is_active)
    db.add(user)
    db.flush()
    audit.log(db, actor, "create_user", "user", user.id, after={"username": user.username, "role_id": user.role_id})
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut, summary="Update a user")
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db),
                actor: User = Depends(require("users:manage"))):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    data = body.model_dump(exclude_unset=True)
    if user.id == actor.id and (data.get("is_active") is False or ("role_id" in data and data["role_id"] != user.role_id)):
        raise HTTPException(400, "You cannot deactivate or change the role of your own account")
    if "role_id" in data and not db.get(Role, data["role_id"]):
        raise HTTPException(400, "Unknown role_id")
    before = {"role_id": user.role_id, "is_active": user.is_active, "email": user.email}
    if data.get("password"):
        user.hashed_password = hash_password(data.pop("password"))
    for k, v in data.items():
        if v is not None:
            setattr(user, k, v)
    audit.log(db, actor, "update_user", "user", user.id, before=before,
              after={"role_id": user.role_id, "is_active": user.is_active, "email": user.email})
    db.commit()
    db.refresh(user)
    return user
