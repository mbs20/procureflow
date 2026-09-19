from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from procureflow.config import get_settings
from procureflow.database import get_db
from procureflow.utils.actor import sanitize_actor_string

__all__ = ["get_db", "verify_api_key", "get_safe_principal", "sanitize_actor"]

settings = get_settings()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_safe_principal(token: str | None) -> str:
    """Map raw API key / credential token to a safe principal label to prevent leaking secrets."""
    return sanitize_actor_string(token)


def sanitize_actor(actor: str | None) -> str:
    """Sanitize any actor/principal string so credentials/secrets are never exposed."""
    return sanitize_actor_string(actor)


async def verify_api_key(
    api_key_header_val: str | None = Security(api_key_header),
    authorization: str | None = Header(None),
) -> str:
    """Validate API key from X-API-Key or Authorization Bearer header."""
    # In test environment, allow bypassing if configured
    if settings.environment == "test" and not settings.api_key:
        return "test-user"

    token = api_key_header_val
    if not token and authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:].strip()
        else:
            token = authorization.strip()

    if not token or token != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Provide valid key in X-API-Key or Authorization: Bearer <key>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

