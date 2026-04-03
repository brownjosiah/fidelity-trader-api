"""Response envelope and error schemas for the service API."""

from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from fastapi.responses import JSONResponse
from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None


class APIResponse(BaseModel, Generic[T]):
    ok: bool = True
    data: Optional[T] = None
    error: ErrorDetail | None = None


def success(data: Any = None) -> dict:
    """Build a success envelope dict."""
    return {"ok": True, "data": data, "error": None}


def error_response(code: str, message: str, status_code: int = 500, details: dict | None = None) -> JSONResponse:
    """Build a JSONResponse with the standard error envelope."""
    body = {
        "ok": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    }
    return JSONResponse(status_code=status_code, content=body)
