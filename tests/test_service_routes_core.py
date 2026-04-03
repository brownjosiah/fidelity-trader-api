"""Tests for auth, accounts, and orders routes."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from service.app import create_app
from service.dependencies import get_client, get_session_manager
from service.session.manager import SessionManager, SessionState
from service.session.store import SessionStore

pytestmark = pytest.mark.anyio


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


# ── Helpers ──────────────────────────────────────────────────────────

async def _init_app_state(app):
    """Manually initialize app.state the same way lifespan would."""
    settings = app.state.settings
    app.state.session_manager = SessionManager(settings)
    tmp = tempfile.mktemp(suffix=".db")
    app.state.store = SessionStore(tmp, settings.encryption_key)
    await app.state.store.initialize()


def _make_mock_client():
    """Build a MagicMock that stands in for FidelityClient."""
    client = MagicMock()

    # Portfolio modules — each method returns a mock with model_dump
    for attr in (
        "accounts", "positions", "balances", "transactions",
        "option_summary", "closed_positions", "loaned_securities", "tax_lots",
    ):
        module = MagicMock()
        setattr(client, attr, module)

    # Order modules
    for attr in (
        "order_status", "staged_orders",
        "equity_orders", "single_option_orders", "option_orders",
        "cancel_order", "cancel_replace", "conditional_orders",
    ):
        module = MagicMock()
        setattr(client, attr, module)

    return client


def _mock_response(**data):
    """Create a MagicMock with a model_dump method returning data."""
    resp = MagicMock()
    resp.model_dump.return_value = data
    return resp


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
async def app():
    os.environ["FTSERVICE_API_KEY_REQUIRED"] = "false"
    a = create_app()
    # Register route files that are NOT in app.py yet
    from service.routes.auth import router as auth_router
    from service.routes.accounts import router as accounts_router
    from service.routes.orders import router as orders_router
    a.include_router(auth_router)
    a.include_router(accounts_router)
    a.include_router(orders_router)

    await _init_app_state(a)
    yield a
    os.environ.pop("FTSERVICE_API_KEY_REQUIRED", None)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_client(app):
    """Override get_client to return a mock FidelityClient."""
    mc = _make_mock_client()
    app.dependency_overrides[get_client] = lambda: mc
    yield mc
    app.dependency_overrides.pop(get_client, None)


# ── Auth Routes ──────────────────────────────────────────────────────

class TestAuthLogin:
    async def test_login_success(self, app, client):
        mock_mgr = MagicMock(spec=SessionManager)
        mock_mgr.login = AsyncMock(return_value={"status": "authenticated"})
        app.dependency_overrides[get_session_manager] = lambda: mock_mgr

        resp = await client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["status"] == "authenticated"
        mock_mgr.login.assert_awaited_once_with(
            username="testuser", password="testpass", totp_secret=None,
        )
        app.dependency_overrides.pop(get_session_manager, None)

    async def test_login_with_totp(self, app, client):
        mock_mgr = MagicMock(spec=SessionManager)
        mock_mgr.login = AsyncMock(return_value={"status": "authenticated"})
        app.dependency_overrides[get_session_manager] = lambda: mock_mgr

        resp = await client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass",
            "totp_secret": "JBSWY3DPEHPK3PXP",
        })
        assert resp.status_code == 200
        mock_mgr.login.assert_awaited_once_with(
            username="testuser", password="testpass", totp_secret="JBSWY3DPEHPK3PXP",
        )
        app.dependency_overrides.pop(get_session_manager, None)


class TestAuthLogout:
    async def test_logout_success(self, app, client):
        mock_mgr = MagicMock(spec=SessionManager)
        mock_mgr.logout = AsyncMock()
        app.dependency_overrides[get_session_manager] = lambda: mock_mgr

        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        mock_mgr.logout.assert_awaited_once()
        app.dependency_overrides.pop(get_session_manager, None)


class TestAuthStatus:
    async def test_status_disconnected(self, app, client):
        mock_mgr = MagicMock(spec=SessionManager)
        mock_mgr.state = SessionState.DISCONNECTED
        mock_mgr.is_authenticated = False
        app.dependency_overrides[get_session_manager] = lambda: mock_mgr

        resp = await client.get("/api/v1/auth/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["state"] == "disconnected"
        assert body["data"]["is_authenticated"] is False
        app.dependency_overrides.pop(get_session_manager, None)

    async def test_status_authenticated(self, app, client):
        mock_mgr = MagicMock(spec=SessionManager)
        mock_mgr.state = SessionState.AUTHENTICATED
        mock_mgr.is_authenticated = True
        app.dependency_overrides[get_session_manager] = lambda: mock_mgr

        resp = await client.get("/api/v1/auth/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["state"] == "authenticated"
        assert body["data"]["is_authenticated"] is True
        app.dependency_overrides.pop(get_session_manager, None)


# ── Account Routes ──────────────────────────────────────────────────

class TestAccountsEndpoint:
    async def test_discover_accounts(self, client, mock_client):
        mock_client.accounts.discover_accounts.return_value = _mock_response(
            accounts=[{"acctNum": "Z12345678"}]
        )
        resp = await client.get("/api/v1/accounts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["accounts"][0]["acctNum"] == "Z12345678"


class TestPositionsEndpoint:
    async def test_get_positions(self, client, mock_client):
        mock_client.positions.get_positions.return_value = _mock_response(
            positions=[{"symbol": "AAPL", "qty": 100}]
        )
        resp = await client.get("/api/v1/accounts/Z12345678/positions")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["positions"][0]["symbol"] == "AAPL"
        mock_client.positions.get_positions.assert_called_once_with(["Z12345678"])


class TestBalancesEndpoint:
    async def test_get_balances(self, client, mock_client):
        mock_client.balances.get_balances.return_value = _mock_response(
            total_value=50000.0
        )
        resp = await client.get("/api/v1/accounts/Z12345678/balances")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["total_value"] == 50000.0
        mock_client.balances.get_balances.assert_called_once_with(["Z12345678"])


# ── Order Routes ─────────────────────────────────────────────────────

class TestOrderStatusEndpoint:
    async def test_get_order_status(self, client, mock_client):
        mock_client.order_status.get_order_status.return_value = _mock_response(
            orders=[{"confNum": "ABC123", "status": "OPEN"}]
        )
        resp = await client.get("/api/v1/orders/status?acct_ids=Z12345678")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["orders"][0]["confNum"] == "ABC123"
        mock_client.order_status.get_order_status.assert_called_once_with(["Z12345678"])

    async def test_get_order_status_multiple_accounts(self, client, mock_client):
        mock_client.order_status.get_order_status.return_value = _mock_response(orders=[])
        resp = await client.get("/api/v1/orders/status?acct_ids=Z111,Z222")
        assert resp.status_code == 200
        mock_client.order_status.get_order_status.assert_called_once_with(["Z111", "Z222"])


class TestEquityPreviewEndpoint:
    async def test_preview_equity_order(self, client, mock_client):
        mock_client.equity_orders.preview_order.return_value = _mock_response(
            confNum="CONF123", acctNum="Z12345678"
        )
        resp = await client.post("/api/v1/orders/equity/preview", json={
            "acctNum": "Z12345678",
            "symbol": "AAPL",
            "orderActionCode": "B",
            "qty": 10,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["confNum"] == "CONF123"
        mock_client.equity_orders.preview_order.assert_called_once()


class TestCancelEndpoint:
    async def test_cancel_order(self, client, mock_client):
        mock_client.cancel_order.cancel_order.return_value = _mock_response(
            is_accepted=True
        )
        resp = await client.post("/api/v1/orders/CONF123/cancel", json={
            "acctNum": "Z12345678",
            "actionCode": "B",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["is_accepted"] is True
        mock_client.cancel_order.cancel_order.assert_called_once_with(
            "CONF123", "Z12345678", "B"
        )


# ── Unauthenticated Access ──────────────────────────────────────────

class TestUnauthenticatedAccess:
    async def test_positions_requires_auth(self, client):
        """Endpoints using get_client should return 401 when no session exists."""
        resp = await client.get("/api/v1/accounts/Z12345678/positions")
        assert resp.status_code == 401
        body = resp.json()
        assert body["detail"]["code"] == "AUTH_REQUIRED"

    async def test_order_status_requires_auth(self, client):
        resp = await client.get("/api/v1/orders/status?acct_ids=Z12345678")
        assert resp.status_code == 401

    async def test_equity_preview_requires_auth(self, client):
        resp = await client.post("/api/v1/orders/equity/preview", json={
            "acctNum": "Z12345678",
            "symbol": "AAPL",
            "orderActionCode": "B",
            "qty": 10,
        })
        assert resp.status_code == 401

    async def test_accounts_requires_auth(self, client):
        resp = await client.get("/api/v1/accounts")
        assert resp.status_code == 401
