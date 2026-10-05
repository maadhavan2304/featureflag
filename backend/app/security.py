from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings


# ---------------------------------------------------------
# Password
# ---------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode()[:72],
        bcrypt.gensalt(),
    ).decode()


def verify_password(
    password: str,
    hashed: str,
) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode()[:72],
            hashed.encode(),
        )
    except ValueError:
        return False


# ---------------------------------------------------------
# JWT
# ---------------------------------------------------------

def create_token(
    subject: int,
    token_type: str,
    expires: timedelta,
) -> str:

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(user_id: int) -> str:
    return create_token(
        user_id,
        "access",
        timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )


def create_refresh_token(user_id: int) -> str:
    return create_token(
        user_id,
        "refresh",
        timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        ),
    )


def decode_token(
    token: str,
    expected_type: str,
) -> int:

    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )

    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(
            "wrong token type"
        )

    return int(payload["sub"])


# ---------------------------------------------------------
# Swagger / Bearer Authentication
# ---------------------------------------------------------

bearer_scheme = HTTPBearer()


def get_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),
) -> str:

    return credentials.credentials


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),
) -> int:

    token = credentials.credentials

    try:
        user_id = decode_token(
            token,
            "access",
        )

        return user_id

    except (jwt.PyJWTError, ValueError, KeyError):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )