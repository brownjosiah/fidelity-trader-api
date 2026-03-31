"""Tests for the available markets API models and AvailableMarketsAPI client."""
import pytest
import httpx
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.available_market import (
    MarketHours,
    OrderTypeSupported,
    AvailableMarket,
    SecurityInfo,
    AvailableMarketsResponse,
)
from fidelity_trader.reference.markets import AvailableMarketsAPI


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_AVAILABLE_MARKETS_URL = (
    f"{DPSERVICE_URL}/ftgw/dp/reference/security/stock/availablemarket/v1"
)


def _make_market_hours(
    market_opening: str = "93000",
    market_closing: str = "160000",
    short_sell_opening: str = "93000",
    short_sell_closing: str = "160000",
    order_opening: str = "0",
    order_closing: str = "0",
    order_accept_from: str = "0",
    order_accept_to: str = "0",
) -> dict:
    return {
        "marketOpeningHours": market_opening,
        "marketClosingHours": market_closing,
        "shortSellOpeningHours": short_sell_opening,
        "shortSellClosingHours": short_sell_closing,
        "marketOrderOpeningHours": order_opening,
        "marketOrderClosingHours": order_closing,
        "marketOrderAcceptFromHours": order_accept_from,
        "marketOrderAcceptToHours": order_accept_to,
    }


def _make_order_type_supported(
    fill_or_kill: bool = True,
    immediate_or_cancel: bool = True,
    all_or_none: bool = True,
    not_held: bool = True,
    do_not_reduce: bool = True,
    cash_settle: bool = True,
    next_day: bool = True,
    stop_limit: bool = True,
    short_sell: bool = True,
    pegged: bool = False,
    discretion: bool = False,
    limit: bool = True,
    market: bool = True,
    trail_limit: bool = True,
    trail_stop: bool = True,
    cancel_replace: bool = True,
    hidden: bool = False,
    regular_session: bool = False,
    pre_market_session: bool = False,
    after_hours_session: bool = False,
) -> dict:
    return {
        "fillOrKillInd": fill_or_kill,
        "immediateOrCancelInd": immediate_or_cancel,
        "allOrNoneInd": all_or_none,
        "notHeldInd": not_held,
        "doNotReduceInd": do_not_reduce,
        "cashSettleInd": cash_settle,
        "nextDayInd": next_day,
        "stopLimitInd": stop_limit,
        "shortSellInd": short_sell,
        "peggedInd": pegged,
        "discretionInd": discretion,
        "limitInd": limit,
        "marketInd": market,
        "trailLimitInd": trail_limit,
        "trailStopInd": trail_stop,
        "cancelReplaceInd": cancel_replace,
        "hiddenInd": hidden,
        "regularSessionInd": regular_session,
        "preMarketSessionInd": pre_market_session,
        "afterHoursSessionInd": after_hours_session,
    }


def _make_available_market(
    marketplace: str = "AUTO",
    routing_code: str = "#O",
    name: str = "AUTO",
    exchange_symbol: str = None,
    display_quantity_min: str = "0.00000",
    market_hours: dict = None,
    order_type_supported: dict = None,
) -> dict:
    return {
        "marketplace": marketplace,
        "routingCode": routing_code,
        "name": name,
        "exchangeSymbol": exchange_symbol,
        "marketHours": market_hours or _make_market_hours(),
        "orderTypeSupported": order_type_supported or _make_order_type_supported(),
        "displayQuantityMin": display_quantity_min,
    }


def _make_security_info(
    symbol: str = "LGVN",
    avail_mkt_cnt: int = 9,
    avail_shares: float = None,
    cusip: str = "54303L203",
) -> dict:
    return {
        "symbol": symbol,
        "availMktCnt": avail_mkt_cnt,
        "availShares": avail_shares,
        "cusip": cusip,
    }


def _make_api_response(
    symbol: str = "LGVN",
    markets: list[dict] = None,
    avail_mkt_cnt: int = 9,
) -> dict:
    if markets is None:
        markets = [_make_available_market()]
    return {
        "security": _make_security_info(symbol=symbol, avail_mkt_cnt=avail_mkt_cnt),
        "availableMarkets": markets,
    }


# ---------------------------------------------------------------------------
# MarketHours
# ---------------------------------------------------------------------------

class TestMarketHours:
    def test_parses_all_fields(self):
        mh = MarketHours.model_validate(_make_market_hours(
            market_opening="93000",
            market_closing="160000",
            short_sell_opening="93000",
            short_sell_closing="160000",
            order_opening="0",
            order_closing="0",
            order_accept_from="0",
            order_accept_to="0",
        ))
        assert mh.market_opening_hours == "93000"
        assert mh.market_closing_hours == "160000"
        assert mh.short_sell_opening_hours == "93000"
        assert mh.short_sell_closing_hours == "160000"
        assert mh.market_order_opening_hours == "0"
        assert mh.market_order_closing_hours == "0"
        assert mh.market_order_accept_from_hours == "0"
        assert mh.market_order_accept_to_hours == "0"

    def test_iex_market_hours(self):
        mh = MarketHours.model_validate(_make_market_hours(
            market_opening="80000",
            market_closing="155959",
            short_sell_opening="80000",
            short_sell_closing="155930",
        ))
        assert mh.market_opening_hours == "80000"
        assert mh.market_closing_hours == "155959"
        assert mh.short_sell_closing_hours == "155930"

    def test_alias_access(self):
        raw = _make_market_hours()
        mh = MarketHours.model_validate(raw)
        # Access via Python name
        assert mh.market_opening_hours == raw["marketOpeningHours"]


# ---------------------------------------------------------------------------
# OrderTypeSupported
# ---------------------------------------------------------------------------

class TestOrderTypeSupported:
    def test_parses_all_true_indicators(self):
        ots = OrderTypeSupported.model_validate(_make_order_type_supported())
        assert ots.fill_or_kill_ind is True
        assert ots.immediate_or_cancel_ind is True
        assert ots.all_or_none_ind is True
        assert ots.not_held_ind is True
        assert ots.do_not_reduce_ind is True
        assert ots.cash_settle_ind is True
        assert ots.next_day_ind is True
        assert ots.stop_limit_ind is True
        assert ots.short_sell_ind is True
        assert ots.limit_ind is True
        assert ots.market_ind is True
        assert ots.trail_limit_ind is True
        assert ots.trail_stop_ind is True
        assert ots.cancel_replace_ind is True

    def test_parses_false_indicators(self):
        ots = OrderTypeSupported.model_validate(_make_order_type_supported())
        assert ots.pegged_ind is False
        assert ots.discretion_ind is False
        assert ots.hidden_ind is False
        assert ots.regular_session_ind is False
        assert ots.pre_market_session_ind is False
        assert ots.after_hours_session_ind is False

    def test_iex_order_type_supported(self):
        raw = _make_order_type_supported(
            fill_or_kill=False,
            immediate_or_cancel=False,
            all_or_none=False,
            stop_limit=False,
            discretion=True,
            trail_limit=False,
            trail_stop=False,
        )
        ots = OrderTypeSupported.model_validate(raw)
        assert ots.fill_or_kill_ind is False
        assert ots.immediate_or_cancel_ind is False
        assert ots.all_or_none_ind is False
        assert ots.stop_limit_ind is False
        assert ots.discretion_ind is True
        assert ots.trail_limit_ind is False
        assert ots.trail_stop_ind is False


# ---------------------------------------------------------------------------
# AvailableMarket
# ---------------------------------------------------------------------------

class TestAvailableMarket:
    def test_parses_auto_market(self):
        am = AvailableMarket.model_validate(_make_available_market())
        assert am.marketplace == "AUTO"
        assert am.routing_code == "#O"
        assert am.name == "AUTO"
        assert am.exchange_symbol is None
        assert am.display_quantity_min == "0.00000"

    def test_nested_market_hours(self):
        am = AvailableMarket.model_validate(_make_available_market())
        assert isinstance(am.market_hours, MarketHours)
        assert am.market_hours.market_opening_hours == "93000"

    def test_nested_order_type_supported(self):
        am = AvailableMarket.model_validate(_make_available_market())
        assert isinstance(am.order_type_supported, OrderTypeSupported)
        assert am.order_type_supported.fill_or_kill_ind is True

    def test_iex_market(self):
        am = AvailableMarket.model_validate(_make_available_market(
            marketplace="IEX",
            routing_code="QV",
            name="IEX",
            market_hours=_make_market_hours(
                market_opening="80000",
                market_closing="155959",
            ),
            order_type_supported=_make_order_type_supported(
                fill_or_kill=False,
                discretion=True,
            ),
        ))
        assert am.marketplace == "IEX"
        assert am.routing_code == "QV"
        assert am.market_hours.market_opening_hours == "80000"
        assert am.order_type_supported.fill_or_kill_ind is False
        assert am.order_type_supported.discretion_ind is True

    def test_exchange_symbol_when_present(self):
        am = AvailableMarket.model_validate(
            _make_available_market(exchange_symbol="XNAS")
        )
        assert am.exchange_symbol == "XNAS"


# ---------------------------------------------------------------------------
# SecurityInfo
# ---------------------------------------------------------------------------

class TestSecurityInfo:
    def test_parses_all_fields(self):
        si = SecurityInfo.model_validate(_make_security_info())
        assert si.symbol == "LGVN"
        assert si.avail_mkt_cnt == 9
        assert si.avail_shares is None
        assert si.cusip == "54303L203"

    def test_avail_shares_when_present(self):
        si = SecurityInfo.model_validate(_make_security_info(avail_shares=100.0))
        assert si.avail_shares == pytest.approx(100.0)

    def test_different_symbol(self):
        si = SecurityInfo.model_validate(_make_security_info(symbol="AAPL", cusip="037833100"))
        assert si.symbol == "AAPL"
        assert si.cusip == "037833100"


# ---------------------------------------------------------------------------
# AvailableMarketsResponse — full integration parsing
# ---------------------------------------------------------------------------

class TestAvailableMarketsResponse:
    def test_parses_single_market(self):
        raw = _make_api_response(markets=[_make_available_market()])
        resp = AvailableMarketsResponse.from_api_response(raw)
        assert resp.security.symbol == "LGVN"
        assert resp.security.avail_mkt_cnt == 9
        assert len(resp.available_markets) == 1
        assert resp.available_markets[0].marketplace == "AUTO"

    def test_parses_multiple_markets(self):
        markets = [
            _make_available_market("AUTO", "#O", "AUTO"),
            _make_available_market(
                "IEX", "QV", "IEX",
                market_hours=_make_market_hours(market_opening="80000", market_closing="155959"),
                order_type_supported=_make_order_type_supported(fill_or_kill=False, discretion=True),
            ),
        ]
        raw = _make_api_response(markets=markets, avail_mkt_cnt=2)
        resp = AvailableMarketsResponse.from_api_response(raw)
        assert len(resp.available_markets) == 2
        assert resp.available_markets[0].marketplace == "AUTO"
        assert resp.available_markets[1].marketplace == "IEX"
        assert resp.available_markets[1].routing_code == "QV"

    def test_security_info_nested(self):
        raw = _make_api_response()
        resp = AvailableMarketsResponse.from_api_response(raw)
        assert isinstance(resp.security, SecurityInfo)
        assert resp.security.cusip == "54303L203"

    def test_market_hours_nested_in_response(self):
        raw = _make_api_response()
        resp = AvailableMarketsResponse.from_api_response(raw)
        mh = resp.available_markets[0].market_hours
        assert isinstance(mh, MarketHours)
        assert mh.market_opening_hours == "93000"
        assert mh.market_closing_hours == "160000"

    def test_order_type_supported_nested_in_response(self):
        raw = _make_api_response()
        resp = AvailableMarketsResponse.from_api_response(raw)
        ots = resp.available_markets[0].order_type_supported
        assert isinstance(ots, OrderTypeSupported)
        assert ots.limit_ind is True
        assert ots.market_ind is True

    def test_empty_available_markets(self):
        raw = _make_api_response(markets=[])
        resp = AvailableMarketsResponse.from_api_response(raw)
        assert resp.available_markets == []

    def test_avail_shares_none(self):
        raw = _make_api_response()
        resp = AvailableMarketsResponse.from_api_response(raw)
        assert resp.security.avail_shares is None


# ---------------------------------------------------------------------------
# AvailableMarketsAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestAvailableMarketsAPI:
    @respx.mock
    def test_get_available_markets_makes_correct_request(self):
        raw_response = _make_api_response()
        route = respx.post(_AVAILABLE_MARKETS_URL).mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = AvailableMarketsAPI(client)
        result = api.get_available_markets("LGVN", ["Z21772945"])

        assert route.called
        assert isinstance(result, AvailableMarketsResponse)
        assert result.security.symbol == "LGVN"
        assert len(result.available_markets) == 1

    @respx.mock
    def test_get_available_markets_request_body_shape(self):
        raw_response = _make_api_response()
        route = respx.post(_AVAILABLE_MARKETS_URL).mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = AvailableMarketsAPI(client)
        api.get_available_markets("LGVN", ["Z21772945"])

        import json
        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["symbol"] == "LGVN"
        assert sent_body["accounts"] == ["Z21772945"]
        assert sent_body["requestType"] == ""
        assert sent_body["isCheckShares"] is False

    @respx.mock
    def test_get_available_markets_multiple_accounts(self):
        raw_response = _make_api_response()
        route = respx.post(_AVAILABLE_MARKETS_URL).mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = AvailableMarketsAPI(client)
        api.get_available_markets("LGVN", ["Z21772945", "Z33359950"])

        import json
        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["accounts"] == ["Z21772945", "Z33359950"]

    @respx.mock
    def test_get_available_markets_returns_all_markets(self):
        markets = [
            _make_available_market("AUTO", "#O", "AUTO"),
            _make_available_market("IEX", "QV", "IEX"),
            _make_available_market("NYSE", "N", "NYSE"),
        ]
        raw_response = _make_api_response(markets=markets, avail_mkt_cnt=3)
        respx.post(_AVAILABLE_MARKETS_URL).mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = AvailableMarketsAPI(client)
        result = api.get_available_markets("LGVN", ["Z21772945"])

        assert len(result.available_markets) == 3
        assert result.available_markets[2].marketplace == "NYSE"

    @respx.mock
    def test_get_available_markets_raises_on_http_error(self):
        respx.post(_AVAILABLE_MARKETS_URL).mock(
            return_value=httpx.Response(401)
        )
        client = httpx.Client()
        api = AvailableMarketsAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_available_markets("LGVN", ["Z21772945"])

    @respx.mock
    def test_get_available_markets_different_symbol(self):
        raw_response = _make_api_response(symbol="AAPL")
        raw_response["security"]["symbol"] = "AAPL"
        respx.post(_AVAILABLE_MARKETS_URL).mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = AvailableMarketsAPI(client)
        result = api.get_available_markets("AAPL", ["Z21772945"])

        assert result.security.symbol == "AAPL"
