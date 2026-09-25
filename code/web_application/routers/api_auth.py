"""Database-backed authentication endpoints for the React client."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from code.web_application.db import get_db
from code.web_application.models import SessionRecord, User
from code.web_application.schemas import LoginRequest, UserResponse
from code.web_application.security import verify_password


router = APIRouter(prefix="/api/v1/auth", tags=["hw4-auth"])
SESSION_TTL_MINUTES = 30
COOKIE_NAME = "hw4_session"


def utc_now() -> datetime:
    return datetime.utcnow()


def require_user(
    hw4_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not hw4_session:
        raise HTTPException(status_code=401, detail="Login required")

    row = db.scalar(
        select(SessionRecord).where(SessionRecord.id == hw4_session)
    )
    if row is None or row.expires_at <= utc_now():
        if row is not None:
            db.delete(row)
            db.commit()
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    user = db.get(User, row.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Session user was not found")
    return user


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    user = db.scalar(
        select(User).where(User.email == payload.email.lower())
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    db.execute(delete(SessionRecord).where(SessionRecord.user_id == user.id))
    session = SessionRecord(
        id=secrets.token_hex(32),
        user_id=user.id,
        expires_at=utc_now() + timedelta(minutes=SESSION_TTL_MINUTES),
    )
    db.add(session)
    db.commit()

    secure_cookie = os.getenv("SESSION_COOKIE_SECURE", "false").lower() in {
        "1",
        "true",
        "yes",
    }
    response.set_cookie(
        key=COOKIE_NAME,
        value=session.id,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=SESSION_TTL_MINUTES * 60,
        path="/",
    )
    return user


@router.get("/me", response_model=UserResponse)
def current_user(user: User = Depends(require_user)) -> User:
    return user


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    hw4_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> None:
    if hw4_session:
        db.execute(delete(SessionRecord).where(SessionRecord.id == hw4_session))
        db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
