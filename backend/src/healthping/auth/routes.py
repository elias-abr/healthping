"""Auth API routes: signup, login, logout, me."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from healthping.auth.passwords import hash_password, verify_password
from healthping.auth.schemas import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from healthping.auth.tokens import create_access_token
from healthping.db.models.user import User
from healthping.settings import Settings

_COOKIE_NAME = "healthping_session"


def create_auth_router(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    get_current_user: Callable[..., Coroutine[Any, Any, User]],
) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.post("/signup", response_model=UserResponse, status_code=201)
    async def signup(body: SignupRequest) -> UserResponse:
        email = body.email.strip().lower()
        password_hash = hash_password(body.password)
        user = User(email=email, password_hash=password_hash)
        async with session_factory() as session:
            session.add(user)
            try:
                await session.commit()
                await session.refresh(user)
            except IntegrityError:
                await session.rollback()
                raise HTTPException(  # noqa: B904
                    status_code=409, detail="Email already registered"
                )
        return UserResponse(id=user.id, email=user.email, is_admin=user.is_admin)

    @router.post("/login", response_model=TokenResponse)
    async def login(body: LoginRequest, response: Response) -> TokenResponse:
        email = body.email.strip().lower()
        async with session_factory() as session:
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
        if user is None or not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        token = create_access_token(
            user_id=user.id,
            email=user.email,
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
            expiry_days=settings.jwt_expiry_days,
        )
        response.set_cookie(
            key=_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            secure=False,  # set True behind HTTPS in production
            max_age=settings.jwt_expiry_days * 86400,
        )
        return TokenResponse(access_token=token)

    @router.post("/logout", status_code=204)
    async def logout(response: Response) -> None:
        response.delete_cookie(_COOKIE_NAME)

    @router.get("/me", response_model=UserResponse)
    async def me(
        current_user: User = Depends(get_current_user),  # noqa: B008
    ) -> UserResponse:
        return UserResponse(
            id=current_user.id,
            email=current_user.email,
            is_admin=current_user.is_admin,
        )

    return router
