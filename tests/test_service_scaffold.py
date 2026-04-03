"""Tests for the Phase 1 service skeleton."""

from __future__ import annotations

import hashlib
import os
import tempfile

import pytest
from httpx import AsyncClient, ASGITransport

from service.config import Settings
from service.models.responses import APIResponse, ErrorDetail, success, error_response
from service.session.manager import SessionManager, SessionState
from service.session.store import SessionStore
from service.auth.api_key import generate_api_key, hash_api_key
from service.app import create_app

pytestmark = pytest.mark.anyio

# Restrict to asyncio only (aiosqlite does not support trio)
@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


# ── Helpers ──────────────────────────────────────────────────────────

async def _init_app_state(app):
    """Manually initialize app.state the same way lifespan would.

    ASGITransport does not trigger FastAPI lifespan events, so tests
    that hit routes need this to set up session_manager, store, etc.
    """
    settings = app.state.settings
    app.state.session_manager = SessionManager(settings)
    # Use a temp db so tests don't collide
    tmp = tempfile.mktemp(suffix=".db")
    app.state.store = SessionStore(tmp, settings.encryption_key)
    await app.state.store.initialize()


# ── Settings ─────────────────────────────────────────────────────────

class TestSettings:
    def test_defaults(self):
        s = Settings(encryption_key="test")
        assert s.host == "127.0.0.1"
        assert s.port == 8787
        assert s.api_key_required is True
        assert s.live_trading is False
        assert s.session_keepalive_interval == 300
        assert s.log_level == "INFO"

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("FTSERVICE_HOST", "0.0.0.0")
        monkeypatch.setenv("FTSERVICE_PORT", "9999")
        monkeypatch.setenv("FTSERVICE_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("FTSERVICE_LIVE_TRADING", "true")
        s = Settings()
        assert s.host == "0.0.0.0"
        assert s.port == 9999
        assert s.log_level == "DEBUG"
        assert s.live_trading is True


# ── Response Envelope ────────────────────────────────────────────────

class TestResponseEnvelope:
    def test_success_envelope(self):
        resp = success(data={"foo": "bar"})
        assert resp["ok"] is True
        assert resp["data"] == {"foo": "bar"}
        assert resp["error"] is None

    def test_success_empty(self):
        resp = success()
        assert resp["ok"] is True
        assert resp["data"] is None

    def test_error_response(self):
        resp = error_response("TEST_ERROR", "Something broke", status_code=400)
        assert resp.status_code == 400
        import json
        body = json.loads(resp.body.decode())
        assert body["ok"] is False
        assert body["error"]["code"] == "TEST_ERROR"
        assert body["error"]["message"] == "Something broke"

    def test_api_response_model(self):
        r = APIResponse(ok=True, data={"x": 1})
        assert r.ok is True
        assert r.data == {"x": 1}
        assert r.error is None

    def test_api_response_error_model(self):
        r = APIResponse(ok=False, error=ErrorDetail(code="E", message="fail"))
        assert r.ok is False
        assert r.error.code == "E"


# ── SessionManager State Transitions ────────────────────────────────

class TestSessionManagerStates:
    def test_initial_state(self):
        settings = Settings(api_key_required=False)
        mgr = SessionManager(settings)
        assert mgr.state == SessionState.DISCONNECTED
        assert mgr.is_authenticated is False
        assert mgr.get_client() is None

    def test_state_to_authenticated(self):
        settings = Settings(api_key_required=False)
        mgr = SessionManager(settings)
        mgr.state = SessionState.AUTHENTICATED
        assert mgr.state == SessionState.AUTHENTICATED
        assert mgr.is_authenticated is True

    def test_state_to_expired(self):
        settings = Settings(api_key_required=False)
        mgr = SessionManager(settings)
        mgr.state = SessionState.AUTHENTICATED
        mgr.state = SessionState.EXPIRED
        assert mgr.state == SessionState.EXPIRED
        assert mgr.is_authenticated is False
        assert mgr.get_client() is None

    def test_state_back_to_disconnected(self):
        settings = Settings(api_key_required=False)
        mgr = SessionManager(settings)
        mgr.state = SessionState.EXPIRED
        mgr.state = SessionState.DISCONNECTED
        assert mgr.state == SessionState.DISCONNECTED

    async def test_extend_session_no_client(self):
        settings = Settings(api_key_required=False)
        mgr = SessionManager(settings)
        result = await mgr.extend_session()
        assert result is False

    async def test_logout_when_disconnected(self):
        settings = Settings(api_key_required=False)
        mgr = SessionManager(settings)
        await mgr.logout()
        assert mgr.state == SessionState.DISCONNECTED


# ── API Key ──────────────────────────────────────────────────────────

class TestAPIKey:
    def test_generate_key_length(self):
        key = generate_api_key()
        assert len(key) > 20

    def test_generate_unique(self):
        k1 = generate_api_key()
        k2 = generate_api_key()
        assert k1 != k2

    def test_hash_deterministic(self):
        key = "test-key-abc"
        h1 = hash_api_key(key)
        h2 = hash_api_key(key)
        assert h1 == h2
        assert h1 == hashlib.sha256(key.encode()).hexdigest()


# ── Exception Handlers ──────────────────────────────────────────────

class TestExceptionHandlers:
    @pytest.fixture
    async def app(self):
        os.environ["FTSERVICE_API_KEY_REQUIRED"] = "false"
        a = create_app()
        await _init_app_state(a)
        yield a
        os.environ.pop("FTSERVICE_API_KEY_REQUIRED", None)

    async def test_auth_error_handler(self, app):
        from fidelity_trader.exceptions import AuthenticationError

        @app.get("/test-auth-err")
        async def raise_auth():
            raise AuthenticationError("Login failed")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/test-auth-err")
        assert resp.status_code == 401
        body = resp.json()
        assert body["ok"] is False
        assert body["error"]["code"] == "AUTH_REQUIRED"

    async def test_session_expired_handler(self, app):
        from fidelity_trader.exceptions import SessionExpiredError

        @app.get("/test-session-exp")
        async def raise_exp():
            raise SessionExpiredError("Session gone")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/test-session-exp")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "SESSION_EXPIRED"

    async def test_dry_run_handler(self, app):
        from fidelity_trader.exceptions import DryRunError

        @app.get("/test-dry-run")
        async def raise_dry():
            raise DryRunError("Blocked")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/test-dry-run")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "LIVE_TRADING_DISABLED"

    async def test_fidelity_error_handler(self, app):
        from fidelity_trader.exceptions import FidelityError

        @app.get("/test-fidelity-err")
        async def raise_fid():
            raise FidelityError("Something failed")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/test-fidelity-err")
        assert resp.status_code == 502
        assert resp.json()["error"]["code"] == "FIDELITY_ERROR"

    async def test_api_error_handler(self, app):
        from fidelity_trader.exceptions import APIError

        @app.get("/test-api-err")
        async def raise_api():
            raise APIError("Bad response", status_code=500, response_body={"detail": "oops"})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/test-api-err")
        assert resp.status_code == 502
        body = resp.json()
        assert body["error"]["code"] == "FIDELITY_ERROR"
        assert body["error"]["details"] == {"detail": "oops"}


# ── Route Tests ──────────────────────────────────────────────────────

@pytest.fixture
async def app_no_auth():
    os.environ["FTSERVICE_API_KEY_REQUIRED"] = "false"
    a = create_app()
    await _init_app_state(a)
    yield a
    os.environ.pop("FTSERVICE_API_KEY_REQUIRED", None)


@pytest.fixture
async def client(app_no_auth):
    transport = ASGITransport(app=app_no_auth)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    async def test_health_returns_200(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["status"] == "healthy"


class TestServiceInfoEndpoint:
    async def test_service_info(self, client):
        resp = await client.get("/service/info")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "version" in body["data"]
        assert "sdk_version" in body["data"]
        assert body["data"]["session_state"] == "disconnected"


# ── Auth Middleware Tests ────────────────────────────────────────────

class TestAuthMiddleware:
    async def test_blocks_without_key(self):
        """When api_key_required=True, requests without a key get 403."""
        os.environ["FTSERVICE_API_KEY_REQUIRED"] = "true"
        app = create_app()
        await _init_app_state(app)
        os.environ.pop("FTSERVICE_API_KEY_REQUIRED", None)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/service/info")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "API_KEY_INVALID"

    async def test_health_bypasses_auth(self):
        """Health endpoint should work even when auth is required."""
        os.environ["FTSERVICE_API_KEY_REQUIRED"] = "true"
        app = create_app()
        await _init_app_state(app)
        os.environ.pop("FTSERVICE_API_KEY_REQUIRED", None)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/health")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    async def test_passes_with_valid_key(self):
        """When a valid API key is provided, the request goes through."""
        os.environ["FTSERVICE_API_KEY_REQUIRED"] = "true"
        app = create_app()
        await _init_app_state(app)
        os.environ.pop("FTSERVICE_API_KEY_REQUIRED", None)

        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)
        await app.state.store.save_api_key_hash(key_hash)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(
                "/service/info",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    async def test_rejects_invalid_key(self):
        """An invalid API key gets 403."""
        os.environ["FTSERVICE_API_KEY_REQUIRED"] = "true"
        app = create_app()
        await _init_app_state(app)
        os.environ.pop("FTSERVICE_API_KEY_REQUIRED", None)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(
                "/service/info",
                headers={"Authorization": "Bearer bogus-key-that-doesnt-exist"},
            )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "API_KEY_INVALID"

    async def test_passes_without_key_when_not_required(self, client):
        """When api_key_required=False, no key needed."""
        resp = await client.get("/service/info")
        assert resp.status_code == 200
