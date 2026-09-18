"""
procureflow.utils.actor
~~~~~~~~~~~~~~~~~~~~~~~
Shared principal/actor sanitization logic.

Used by:
  - procureflow.api.deps  (get_safe_principal, sanitize_actor)
  - Pydantic field_validators across all response schemas

Rule: raw API key / credential-like tokens must NEVER appear in any
serialized response, audit log, or rendered UI string.
"""
from __future__ import annotations

from typing import Any

__all__ = ["sanitize_actor_string"]

# Patterns that identify the shared dev API key principal
_DEV_PATTERNS = ("dev_api_key", "procureflow_dev")

# Patterns that identify a non-dev but still credential-like API key
_AUTH_PREFIXES = ("sk_", "pk_", "procureflow_sec")
_AUTH_SUBSTR = ("api_key",)


def sanitize_actor_string(v: Any) -> str:
    """Map a raw API key / credential token to a safe display label.

    Returns a human-readable label that never exposes the raw secret value.
    Non-credential identifiers (regular user IDs) are returned unchanged.
    """
    if not v or not isinstance(v, str):
        return "System User"

    # Dev / test credentials
    if any(pat in v for pat in _DEV_PATTERNS):
        return "Development API Principal"

    # Generic credential-like API keys
    if any(v.startswith(pfx) for pfx in _AUTH_PREFIXES) or any(
        pat in v for pat in _AUTH_SUBSTR
    ):
        return "Authenticated API Principal"

    # Regular user identifier — pass through unchanged
    return v
