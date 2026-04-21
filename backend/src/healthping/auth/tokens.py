"""JWT access token creation and decoding."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt


def create_access_token(
    user_id: int,
    email: str,
    secret: str,
    algorithm: str,
    expiry_days: int,
) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(UTC) + timedelta(days=expiry_days),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(
    token: str,
    secret: str,
    algorithm: str,
) -> dict[str, object] | None:
    """Decode and validate a JWT. Returns the payload dict, or None if invalid."""
    try:
        decoded: dict[str, object] = jwt.decode(token, secret, algorithms=[algorithm])
        return decoded
    except jwt.PyJWTError:
        return None
