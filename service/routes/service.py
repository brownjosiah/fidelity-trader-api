"""Bootstrap routes: /health and /service/info."""

from __future__ import annotations

from fastapi import APIRouter, Request

import fidelity_trader
import service as service_pkg
from service.models.responses import success

router = APIRouter()


@router.get("/health")
async def health():
    """Basic health check."""
    return success(data={"status": "healthy"})


@router.get("/service/info")
async def service_info(request: Request):
    """Service version, SDK version, and session state."""
    manager = request.app.state.session_manager
    return success(data={
        "version": service_pkg.__version__,
        "sdk_version": fidelity_trader.__version__,
        "session_state": manager.state.value,
    })
