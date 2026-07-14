"""Auth and publish-safety helpers for workflow API."""

from __future__ import annotations

import hmac
import os
from typing import Any

from src.core.config import config

# Real publish (dry_run=false) requires this exact confirmation string in params.
PUBLISH_CONFIRM_PHRASE = "I_CONFIRM_PUBLISH"


def effective_api_token() -> str:
    """Return API token from ``REDNOTE_API_TOKEN`` or ``security.api_token``."""
    env = (os.environ.get("REDNOTE_API_TOKEN") or "").strip()
    if env:
        return env
    nested = (os.environ.get("REDNOTE_SECURITY__API_TOKEN") or "").strip()
    if nested:
        return nested
    return (config.security.api_token or "").strip()


def auth_required() -> bool:
    token = effective_api_token()
    if token:
        return True
    return bool(config.security.require_token)


def verify_bearer_token(provided: str | None) -> bool:
    expected = effective_api_token()
    if not expected:
        # No token configured: only OK when require_token is false.
        return not config.security.require_token
    if not provided:
        return False
    return hmac.compare_digest(provided.strip(), expected)


def extract_token_from_headers(
    authorization: str | None = None,
    x_api_token: str | None = None,
) -> str | None:
    if x_api_token and x_api_token.strip():
        return x_api_token.strip()
    if authorization:
        parts = authorization.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        return authorization.strip()
    return None


def guard_workflow_params(workflow: str, params: dict[str, Any]) -> dict[str, Any]:
    """Apply publish safety rules; return sanitized params.

    - ``publish.now`` defaults to dry_run=True
    - Real publish requires params.confirm_publish == I_CONFIRM_PUBLISH
    """
    merged = dict(params)
    if workflow != "publish.now":
        return merged

    dry_run = merged.get("dry_run", True)
    # Accept string/bool loosely from JSON.
    if isinstance(dry_run, str):
        dry_run = dry_run.strip().lower() not in {"false", "0", "no"}
    dry_run = bool(dry_run)

    if dry_run:
        merged["dry_run"] = True
        return merged

    confirm = str(merged.get("confirm_publish") or "").strip()
    if confirm != PUBLISH_CONFIRM_PHRASE:
        raise ValueError(
            "Real publish blocked: set dry_run=true (default) or pass "
            f'confirm_publish="{PUBLISH_CONFIRM_PHRASE}" with dry_run=false'
        )
    merged["dry_run"] = False
    return merged
