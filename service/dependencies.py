"""FastAPI dependency injection helpers."""

from __future__ import annotations

from fastapi import HTTPException, Request

from fidelity_trader import FidelityClient
from service.config import Settings
from service.session.manager import SessionManager


def get_settings(request: Request) -> Settings:
    """Retrieve the Settings instance from app state."""
    return request.app.state.settings


def get_session_manager(request: Request) -> SessionManager:
    """Retrieve the SessionManager instance from app state."""
    return request.app.state.session_manager


def get_client(request: Request) -> FidelityClient:
    """Retrieve the active FidelityClient, or raise 401 if not authenticated."""
    manager: SessionManager = request.app.state.session_manager
    client = manager.get_client()
    if client is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Not authenticated"},
        )
    return client
