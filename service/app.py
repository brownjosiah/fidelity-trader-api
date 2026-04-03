"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from fidelity_trader.exceptions import (
    AuthenticationError,
    SessionExpiredError,
    CSRFTokenError,
    APIError,
    DryRunError,
    FidelityError,
)

from service.config import Settings
from service.session.manager import SessionManager
from service.session.store import SessionStore
from service.session.keepalive import KeepAliveTask
from service.auth.middleware import APIKeyMiddleware
from service.models.responses import error_response
from service.routes.service import router as service_router
from service.routes.auth import router as auth_router
from service.routes.accounts import router as accounts_router
from service.routes.orders import router as orders_router
from service.routes.market_data import router as market_data_router
from service.routes.research import router as research_router
from service.routes.watchlists import router as watchlists_router
from service.routes.preferences import router as preferences_router
from service.routes.reference import router as reference_router
from service.routes.streaming import router as streaming_control_router
from service.streaming.sse import router as sse_router
from service.streaming.ws import router as ws_router
from service.streaming.manager import MDDSManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle for the service."""
    settings: Settings = app.state.settings
    session_manager = SessionManager(settings)
    store = SessionStore(settings.db_path, settings.encryption_key)
    keepalive = KeepAliveTask(session_manager, interval=settings.session_keepalive_interval)

    await store.initialize()

    mdds_manager = MDDSManager()

    app.state.session_manager = session_manager
    app.state.store = store
    app.state.keepalive = keepalive
    app.state.mdds_manager = mdds_manager

    logger.info("Service started")
    yield

    # Shutdown
    await mdds_manager.stop()
    await keepalive.stop()
    await session_manager.logout()
    logger.info("Service stopped")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = Settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app = FastAPI(
        title="Fidelity Trader API Service",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Store settings on app.state so lifespan and middleware can read them
    app.state.settings = settings

    # ── Exception Handlers ───────────────────────────────────────

    @app.exception_handler(AuthenticationError)
    async def handle_auth_error(request: Request, exc: AuthenticationError):
        return error_response("AUTH_REQUIRED", str(exc), status_code=401)

    @app.exception_handler(SessionExpiredError)
    async def handle_session_expired(request: Request, exc: SessionExpiredError):
        return error_response("SESSION_EXPIRED", str(exc), status_code=401)

    @app.exception_handler(CSRFTokenError)
    async def handle_csrf_error(request: Request, exc: CSRFTokenError):
        return error_response("FIDELITY_ERROR", str(exc), status_code=502)

    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError):
        details = None
        if hasattr(exc, "response_body") and exc.response_body:
            details = exc.response_body
        return error_response("FIDELITY_ERROR", str(exc), status_code=502, details=details)

    @app.exception_handler(DryRunError)
    async def handle_dry_run_error(request: Request, exc: DryRunError):
        return error_response("LIVE_TRADING_DISABLED", str(exc), status_code=403)

    @app.exception_handler(FidelityError)
    async def handle_fidelity_error(request: Request, exc: FidelityError):
        return error_response("FIDELITY_ERROR", str(exc), status_code=502)

    @app.exception_handler(httpx.HTTPStatusError)
    async def handle_httpx_error(request: Request, exc: httpx.HTTPStatusError):
        return error_response(
            "FIDELITY_ERROR",
            f"Upstream HTTP error: {exc.response.status_code}",
            status_code=502,
        )

    # ── Middleware ────────────────────────────────────────────────

    app.add_middleware(APIKeyMiddleware)

    # ── Routes ───────────────────────────────────────────────────

    app.include_router(service_router)
    app.include_router(auth_router)
    app.include_router(accounts_router)
    app.include_router(orders_router)
    app.include_router(market_data_router)
    app.include_router(research_router)
    app.include_router(watchlists_router)
    app.include_router(preferences_router)
    app.include_router(reference_router)
    app.include_router(streaming_control_router)
    app.include_router(sse_router)
    app.include_router(ws_router)

    return app
