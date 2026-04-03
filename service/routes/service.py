"""Bootstrap routes: /health and /service/info."""

from __future__ import annotations

from fastapi import APIRouter, Request

import fidelity_trader
import service as service_pkg
from service.models.responses import APIResponse, success
from service.models.schemas import HealthCheckData, ServiceInfoData

router = APIRouter()


@router.get("/health", response_model=APIResponse[HealthCheckData], response_model_by_alias=True)
async def health():
    """Basic health check."""
    return success(data={"status": "healthy"})


@router.get("/service/info", response_model=APIResponse[ServiceInfoData], response_model_by_alias=True)
async def service_info(request: Request):
    """Service version, SDK version, and session state."""
    manager = request.app.state.session_manager
    return success(data={
        "version": service_pkg.__version__,
        "sdk_version": fidelity_trader.__version__,
        "session_state": manager.state.value,
    })
