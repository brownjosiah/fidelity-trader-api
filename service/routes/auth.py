"""Authentication routes: login, logout, status, and credential management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from service.dependencies import get_session_manager
from service.models.requests import LoginRequest, CredentialStoreRequest
from service.models.responses import success
from service.session.manager import SessionManager

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/login")
async def login(
    body: LoginRequest,
    manager: SessionManager = Depends(get_session_manager),
):
    """Authenticate with Fidelity and establish a session."""
    result = await manager.login(
        username=body.username,
        password=body.password,
        totp_secret=body.totp_secret,
    )
    return success(result)


@router.post("/logout")
async def logout(manager: SessionManager = Depends(get_session_manager)):
    """Logout and tear down the Fidelity session."""
    await manager.logout()
    return success()


@router.get("/status")
async def status(manager: SessionManager = Depends(get_session_manager)):
    """Return current session state and authentication flag."""
    return success({
        "state": manager.state.value,
        "is_authenticated": manager.is_authenticated,
    })


@router.post("/credentials")
async def store_credentials(body: CredentialStoreRequest, request: Request):
    """Store encrypted credentials for later use."""
    store = request.app.state.store
    await store.save_credentials(
        username=body.username,
        password=body.password,
        totp_secret=body.totp_secret,
    )
    return success({"stored": True})


@router.delete("/credentials")
async def delete_credentials(request: Request):
    """Delete stored credentials."""
    store = request.app.state.store
    await store.delete_credentials()
    return success({"deleted": True})
