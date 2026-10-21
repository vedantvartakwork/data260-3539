"""Dependency-free HS256 JWT authentication and role-based authorization."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from code.web_application.db import get_db
from code.web_application.models import User
from code.web_application.security import verify_password
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

JWT_ALGORITHM = "HS256"
JWT_TTL_SECONDS = 30 * 60
JWT_SECRET = os.getenv("JWT_SECRET", "s3539-hw7-local-secret-change-for-production")
bearer = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/auth", tags=["hw7-jwt-auth"])


class JWTLogin(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = JWT_TTL_SECONDS


class IdentityResponse(BaseModel):
    id: int
    username: str
    role: str


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_access_token(user: User, *, now: int | None = None) -> str:
    issued = int(time.time() if now is None else now)
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "iat": issued,
        "exp": issued + JWT_TTL_SECONDS,
    }
    unsigned = f"{_b64(json.dumps(header, separators=(',', ':')).encode())}.{_b64(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(JWT_SECRET.encode(), unsigned.encode(), hashlib.sha256).digest()
    return f"{unsigned}.{_b64(signature)}"


def decode_access_token(token: str, *, now: int | None = None) -> dict[str, Any]:
    try:
        header_text, payload_text, signature_text = token.split(".")
        unsigned = f"{header_text}.{payload_text}"
        expected = hmac.new(JWT_SECRET.encode(), unsigned.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _unb64(signature_text)):
            raise ValueError("signature")
        header = json.loads(_unb64(header_text))
        payload = json.loads(_unb64(payload_text))
        current = int(time.time() if now is None else now)
        if header.get("alg") != JWT_ALGORITHM or int(payload["exp"]) <= current:
            raise ValueError("expired")
        if payload.get("role") not in {"reader", "writer", "moderator"}:
            raise ValueError("role")
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_jwt_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    user = db.get(User, int(payload["sub"]))
    if user is None or user.username != payload.get("username") or user.role != payload.get("role"):
        raise HTTPException(status_code=401, detail="Token identity is no longer valid")
    return user


def require_roles(*allowed: str) -> Callable[..., User]:
    def dependency(user: User = Depends(require_jwt_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail=f"Role '{user.role}' is not allowed")
        return user

    return dependency


@router.post("/login", response_model=TokenResponse)
def login(payload: JWTLogin, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.username == payload.username.strip().lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenResponse(access_token=create_access_token(user))


@router.get("/me", response_model=IdentityResponse)
def me(user: User = Depends(require_jwt_user)) -> IdentityResponse:
    return IdentityResponse(id=user.id, username=user.username, role=user.role)
