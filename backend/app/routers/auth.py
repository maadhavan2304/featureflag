import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import RefreshIn, TokenOut, UserOut
from ..security import (create_access_token, create_refresh_token, decode_token, verify_password)
from ..services import audit

router = APIRouter(prefix="/auth", tags=["Auth"])


def _tokens(user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.id), refresh_token=create_refresh_token(user.id),
                    user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut, summary="Log in with email or username")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(or_(User.email == form.username, User.username == form.username)))
    if not user or not user.is_active or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect credentials")
    audit.log(db, user, "login", "user", user.id)
    db.commit()
    return _tokens(user)


@router.post("/refresh", response_model=TokenOut, summary="Exchange a refresh token for new tokens")
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    try:
        user = db.get(User, decode_token(body.refresh_token, "refresh"))
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    return _tokens(user)


@router.get("/me", response_model=UserOut, summary="Current user")
def me(user: User = Depends(get_current_user)):
    return user
