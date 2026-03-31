"""Tests for the composed FidelityClient."""

import httpx
import pytest
import respx

import fidelity_trader
from fidelity_trader import FidelityClient
from fidelity_trader.auth.session import AuthSession
from fidelity_trader.portfolio.positions import PositionsAPI
from fidelity_trader.portfolio.balances import BalancesAPI
from fidelity_trader.portfolio.option_summary import OptionSummaryAPI
from fidelity_trader.portfolio.transactions import TransactionsAPI
from fidelity_trader.orders.status import OrderStatusAPI
from fidelity_trader.orders.equity import EquityOrderAPI
from fidelity_trader.orders.options import MultiLegOptionOrderAPI
from fidelity_trader.orders.cancel import OrderCancelAPI
from fidelity_trader.research.data import ResearchAPI
from fidelity_trader.research.search import SearchAPI
from fidelity_trader.streaming.news import StreamingNewsAPI
from fidelity_trader.watchlists.watchlists import WatchlistAPI
from fidelity_trader._http import BASE_URL, AUTH_URL


# ---------------------------------------------------------------------------
# Module attribute tests
# ---------------------------------------------------------------------------

def test_client_has_all_module_attributes():
    client = FidelityClient()
    try:
        assert isinstance(client.positions, PositionsAPI)
        assert isinstance(client.balances, BalancesAPI)
        assert isinstance(client.option_summary, OptionSummaryAPI)
        assert isinstance(client.transactions, TransactionsAPI)
        assert isinstance(client.order_status, OrderStatusAPI)
        assert isinstance(client.equity_orders, EquityOrderAPI)
        assert isinstance(client.option_orders, MultiLegOptionOrderAPI)
        assert isinstance(client.cancel_order, OrderCancelAPI)
        assert isinstance(client.research, ResearchAPI)
        assert isinstance(client.search, SearchAPI)
        assert isinstance(client.streaming, StreamingNewsAPI)
        assert isinstance(client.watchlists, WatchlistAPI)
    finally:
        client.close()


def test_all_modules_share_same_http_client():
    client = FidelityClient()
    try:
        http = client._http
        assert client.positions._http is http
        assert client.balances._http is http
        assert client.option_summary._http is http
        assert client.transactions._http is http
        assert client.order_status._http is http
        assert client.equity_orders._http is http
        assert client.option_orders._http is http
        assert client.cancel_order._http is http
        assert client.research._http is http
        assert client.search._http is http
        assert client.streaming._http is http
        assert client.watchlists._http is http
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Context manager tests
# ---------------------------------------------------------------------------

def test_context_manager_returns_client():
    with FidelityClient() as client:
        assert isinstance(client, FidelityClient)


def test_context_manager_closes_http_on_exit():
    with FidelityClient() as client:
        http = client._http

    # After __exit__, the underlying httpx.Client should be closed
    assert http.is_closed


# ---------------------------------------------------------------------------
# is_authenticated property
# ---------------------------------------------------------------------------

def test_is_authenticated_false_before_login():
    with FidelityClient() as client:
        assert client.is_authenticated is False


# ---------------------------------------------------------------------------
# login / logout delegate to AuthSession
# ---------------------------------------------------------------------------

@respx.mock
def test_login_delegates_to_auth_session(fidelity_response):
    """FidelityClient.login() should run the full 7-step auth flow."""
    respx.get(f"{BASE_URL}/prgw/digital/login/atp").mock(
        return_value=httpx.Response(200, text="<html>login</html>")
    )
    respx.delete(f"{AUTH_URL}/user/session/login").mock(
        return_value=httpx.Response(204)
    )
    respx.get(f"{AUTH_URL}/user/identity/remember/username").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Identified"))
    )
    respx.post(f"{AUTH_URL}/user/identity/remember/username/1").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Identified"))
    )
    respx.post(f"{AUTH_URL}/user/factor/password/authentication").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Authenticated"))
    )
    respx.put(f"{AUTH_URL}/user/identity/remember/username").mock(
        return_value=httpx.Response(200, json=fidelity_response("OK"))
    )
    session_resp = fidelity_response("Session Created", authenticators=[])
    respx.post(f"{AUTH_URL}/user/session/login").mock(
        return_value=httpx.Response(200, json=session_resp)
    )

    with FidelityClient() as client:
        result = client.login("testuser", "testpass")

    assert result["responseBaseInfo"]["status"]["message"] == "Session Created"


@respx.mock
def test_logout_clears_authenticated_state(fidelity_response):
    """After logout(), is_authenticated should be False."""
    respx.get(f"{BASE_URL}/prgw/digital/login/atp").mock(
        return_value=httpx.Response(200, text="<html>login</html>")
    )
    respx.delete(f"{AUTH_URL}/user/session/login").mock(
        return_value=httpx.Response(204)
    )
    respx.get(f"{AUTH_URL}/user/identity/remember/username").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Identified"))
    )
    respx.post(f"{AUTH_URL}/user/identity/remember/username/1").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Identified"))
    )
    respx.post(f"{AUTH_URL}/user/factor/password/authentication").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Authenticated"))
    )
    respx.put(f"{AUTH_URL}/user/identity/remember/username").mock(
        return_value=httpx.Response(200, json=fidelity_response("OK"))
    )
    session_resp = fidelity_response("Session Created", authenticators=[])
    respx.post(f"{AUTH_URL}/user/session/login").mock(
        return_value=httpx.Response(200, json=session_resp)
    )

    with FidelityClient() as client:
        client.login("testuser", "testpass")
        assert client.is_authenticated is True
        client.logout()
        assert client.is_authenticated is False


# ---------------------------------------------------------------------------
# Package-level exports
# ---------------------------------------------------------------------------

def test_package_exports_fidelity_client():
    assert hasattr(fidelity_trader, "FidelityClient")
    assert fidelity_trader.FidelityClient is FidelityClient


def test_package_exports_exceptions():
    from fidelity_trader import (
        FidelityError,
        AuthenticationError,
        SessionExpiredError,
        CSRFTokenError,
        APIError,
    )
    assert issubclass(AuthenticationError, FidelityError)
    assert issubclass(SessionExpiredError, FidelityError)
    assert issubclass(CSRFTokenError, FidelityError)
    assert issubclass(APIError, FidelityError)


def test_package_version():
    assert fidelity_trader.__version__ == "0.1.0"
