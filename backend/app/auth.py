from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from app.config import Settings, get_settings


def require_mock_customer(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    prefix = settings.mock_auth_prefix
    if not token.startswith(prefix):
        raise HTTPException(status_code=401, detail="Expected mock:<customerId> token")
    customer_id = token[len(prefix) :]
    if len(customer_id) != 7 or not customer_id.isdigit():
        raise HTTPException(status_code=422, detail="Customer ID must be 7 digits")
    return customer_id


def require_admin(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Admin credential required")
