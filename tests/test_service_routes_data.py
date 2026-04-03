"""Tests for service data routes: market data, research, watchlists, preferences, reference."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from service.app import create_app
from service.dependencies import get_client

pytestmark = pytest.mark.anyio


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


# ── Helpers ──────────────────────────────────────────────────────────

def _make_app_with_mock_client(mock_client):
    """Create an app with dependency override and manual state init."""
    os.environ["FTSERVICE_API_KEY_REQUIRED"] = "false"
    app = create_app()

    # Register the new routers (not registered in app.py per instructions)
    from service.routes.market_data import router as market_data_router
    from service.routes.research import router as research_router
    from service.routes.watchlists import router as watchlists_router
    from service.routes.preferences import router as preferences_router
    from service.routes.reference import router as reference_router

    app.include_router(market_data_router)
    app.include_router(research_router)
    app.include_router(watchlists_router)
    app.include_router(preferences_router)
    app.include_router(reference_router)

    # Override the get_client dependency to return our mock
    app.dependency_overrides[get_client] = lambda: mock_client

    return app


async def _init_app_state(app):
    """Manually initialize app.state for testing (lifespan doesn't run)."""
    import tempfile
    from service.config import Settings
    from service.session.manager import SessionManager
    from service.session.store import SessionStore

    settings = app.state.settings
    app.state.session_manager = SessionManager(settings)
    tmp = tempfile.mktemp(suffix=".db")
    app.state.store = SessionStore(tmp, settings.encryption_key)
    await app.state.store.initialize()


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
async def mock_client():
    """Create a mock FidelityClient with all needed sub-modules."""
    client = MagicMock()
    return client


@pytest.fixture
async def app(mock_client):
    app = _make_app_with_mock_client(mock_client)
    await _init_app_state(app)
    yield app
    os.environ.pop("FTSERVICE_API_KEY_REQUIRED", None)


@pytest.fixture
async def http(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Market Data: Chain ───────────────────────────────────────────────

class TestOptionChainEndpoint:
    async def test_option_chain_returns_data(self, http, mock_client):
        # Set up the mock to return a dataclass-like response
        from fidelity_trader.models.fastquote import OptionChainResponse

        mock_response = OptionChainResponse(symbol="AAPL", calls=[], puts=[])
        mock_client.option_chain.get_option_chain.return_value = mock_response

        resp = await http.get("/api/v1/market-data/chain/AAPL")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["symbol"] == "AAPL"
        assert body["data"]["calls"] == []
        assert body["data"]["puts"] == []
        mock_client.option_chain.get_option_chain.assert_called_once_with("AAPL")


# ── Market Data: Chart ───────────────────────────────────────────────

class TestChartEndpoint:
    async def test_chart_returns_data(self, http, mock_client):
        from fidelity_trader.models.chart import ChartResponse, ChartSymbolInfo, ChartBar

        symbol_info = ChartSymbolInfo(
            identifier="SPY",
            description="SPDR S&P 500 ETF",
            last_trade=450.0,
            trade_date="2024/01/15",
            day_open=449.5,
            day_high=450.5,
            day_low=449.0,
            net_change=1.0,
            net_change_pct=0.22,
            previous_close=449.0,
        )
        bar = ChartBar(
            timestamp="2024/01/15-10:00:00",
            open=449.5,
            high=450.5,
            low=449.0,
            close=450.0,
            volume=100000,
        )
        mock_response = ChartResponse(symbol_info=symbol_info, bars=[bar])
        mock_client.chart.get_chart.return_value = mock_response

        resp = await http.get(
            "/api/v1/market-data/chart/SPY",
            params={
                "start_date": "2024/01/15-09:30:00",
                "end_date": "2024/01/15-16:00:00",
                "bar_width": "5",
                "extended_hours": "true",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["symbol_info"]["identifier"] == "SPY"
        assert len(body["data"]["bars"]) == 1
        assert body["data"]["bars"][0]["open"] == 449.5
        mock_client.chart.get_chart.assert_called_once_with(
            "SPY", "2024/01/15-09:30:00", "2024/01/15-16:00:00", "5", True
        )


# ── Research: Earnings ───────────────────────────────────────────────

class TestEarningsEndpoint:
    async def test_earnings_returns_data(self, http, mock_client):
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "earnings": [
                {"secDetail": {"symbol": "AAPL"}, "quarters": []}
            ]
        }
        mock_client.research.get_earnings.return_value = mock_response

        resp = await http.get(
            "/api/v1/research/earnings",
            params={"symbols": ["AAPL"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert len(body["data"]["earnings"]) == 1
        assert body["data"]["earnings"][0]["secDetail"]["symbol"] == "AAPL"
        mock_client.research.get_earnings.assert_called_once_with(["AAPL"])


# ── Research: Search ─────────────────────────────────────────────────

class TestSearchEndpoint:
    async def test_search_returns_data(self, http, mock_client):
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "count": 1,
            "suggestions": [
                {"symbol": "AAPL", "desc": "Apple Inc"}
            ],
        }
        mock_client.search.autosuggest.return_value = mock_response

        resp = await http.get("/api/v1/research/search", params={"q": "AAPL"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["count"] == 1
        assert body["data"]["suggestions"][0]["symbol"] == "AAPL"
        mock_client.search.autosuggest.assert_called_once_with("AAPL")


# ── Watchlists: Get ──────────────────────────────────────────────────

class TestWatchlistsEndpoint:
    async def test_get_watchlists(self, http, mock_client):
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "watchlists": [
                {
                    "watchListName": "Buys",
                    "watchListId": "uuid-123",
                    "securityDetails": [],
                }
            ]
        }
        mock_client.watchlists.get_watchlists.return_value = mock_response

        resp = await http.get("/api/v1/watchlists")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert len(body["data"]["watchlists"]) == 1
        assert body["data"]["watchlists"][0]["watchListName"] == "Buys"
        mock_client.watchlists.get_watchlists.assert_called_once()


# ── Alerts: Price Triggers List ──────────────────────────────────────

class TestPriceTriggersEndpoint:
    async def test_list_price_triggers(self, http, mock_client):
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "priceTrigger": {
                "totalAccount": 10,
                "availableAccount": 8,
                "offset": 0,
                "triggers": [],
            }
        }
        mock_client.price_triggers.get_price_triggers.return_value = mock_response

        resp = await http.get(
            "/api/v1/alerts/price-triggers",
            params={"symbol": "QS"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["priceTrigger"]["totalAccount"] == 10
        mock_client.price_triggers.get_price_triggers.assert_called_once_with(
            "QS", "active", 0
        )


# ── Preferences: Get ────────────────────────────────────────────────

class TestPreferencesEndpoint:
    async def test_get_preferences(self, http, mock_client):
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "preferences": [
                {"preferencePath": "user/", "prefValues": {"theme": "dark"}}
            ]
        }
        mock_client.preferences.get_preferences.return_value = mock_response

        resp = await http.get("/api/v1/preferences")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["preferences"][0]["prefValues"]["theme"] == "dark"
        mock_client.preferences.get_preferences.assert_called_once_with("user/", None)


# ── Reference: Holiday Calendar ─────────────────────────────────────

class TestHolidayCalendarEndpoint:
    async def test_get_holiday_calendar(self, http, mock_client):
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "holidays": [
                {
                    "countryCode": "US",
                    "date": 1735689600,
                    "holidayDesc": "New Year's Day",
                    "holidayType": "H",
                    "earlyCloseTm": None,
                }
            ]
        }
        mock_client.holiday_calendar.get_holidays.return_value = mock_response

        resp = await http.get("/api/v1/reference/holiday-calendar")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert len(body["data"]["holidays"]) == 1
        assert body["data"]["holidays"][0]["holidayDesc"] == "New Year's Day"
        mock_client.holiday_calendar.get_holidays.assert_called_once_with("US")
