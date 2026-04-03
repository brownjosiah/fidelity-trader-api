"""Request body schemas for the service API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_secret: str | None = None


class CredentialStoreRequest(BaseModel):
    username: str
    password: str
    totp_secret: str | None = None


class CancelOrderRequest(BaseModel):
    """Body for the cancel endpoint (conf_num comes from the URL path)."""
    acct_num: str = Field(alias="acctNum")
    action_code: str = Field(alias="actionCode")

    model_config = {"populate_by_name": True}


class OrderPlaceRequest(BaseModel):
    """Generic place-order wrapper: the previewed order dict + confirmation number."""
    order: dict[str, Any]
    conf_num: str = Field(alias="confNum")

    model_config = {"populate_by_name": True}


class ConditionalPlaceRequest(BaseModel):
    """Place-order wrapper for conditional orders which use multiple conf nums."""
    order: dict[str, Any]
    conf_nums: list[str] = Field(alias="confNums")

    model_config = {"populate_by_name": True}
