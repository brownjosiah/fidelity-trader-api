"""Tests for the historical chart data API and models."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from fidelity_trader._http import FASTQUOTE_URL
from fidelity_trader.models.chart import ChartBar, ChartSymbolInfo, ChartResponse
from fidelity_trader.market_data.chart import ChartAPI, _unwrap_jsonp, _make_callback

_CHART_URL = f"{FASTQUOTE_URL}/service/marketdata/historical/chart/json"

# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

_SYMBOL_DICT = {
    "Identifier": "SPY",
    "Description": "STATE STREET SPDR S&P 500 ETF TRUST",
    "LastTrade": "648.56",
    "TradeDate": "03/31/2026",
    "DayOpen": "638.94",
    "DayHigh": "649.46",
    "DayLow": "637.98",
    "NetChange": "16.59",
    "NetChangePercent": "2.6251",
    "PreviousClose": "631.97",
    "BarList": {
        "BarRecord": [
            {
                "lt": "2026/03/30-04:00:00",
                "op": "636.88",
                "cl": "636.82",
                "hi": "637.07",
                "lo": "634.1",
                "v": "112744",
            },
            {
                "lt": "2026/03/30-04:05:00",
                "op": "636.84",
                "cl": "637.08",
                "hi": "637.22",
                "lo": "636.66",
                "v": "27237",
            },
        ]
    },
}

_CHART_DATA = {"Symbol": [_SYMBOL_DICT]}

_CALLBACK = "jsonp_1743379200000_1"
_JSONP_BODY = f"{_CALLBACK}({json.dumps(_CHART_DATA)})"


# ---------------------------------------------------------------------------
# ChartBar
# ---------------------------------------------------------------------------


class TestChartBar:
    def test_parses_all_fields(self):
        record = {
            "lt": "2026/03/30-04:00:00",
            "op": "636.88",
            "cl": "636.82",
            "hi": "637.07",
            "lo": "634.1",
            "v": "112744",
        }
        bar = ChartBar.from_dict(record)
        assert bar.timestamp == "2026/03/30-04:00:00"
        assert bar.open == pytest.approx(636.88)
        assert bar.close == pytest.approx(636.82)
        assert bar.high == pytest.approx(637.07)
        assert bar.low == pytest.approx(634.1)
        assert bar.volume == 112744

    def test_missing_fields_default(self):
        bar = ChartBar.from_dict({})
        assert bar.timestamp == ""
        assert bar.open == pytest.approx(0.0)
        assert bar.close == pytest.approx(0.0)
        assert bar.high == pytest.approx(0.0)
        assert bar.low == pytest.approx(0.0)
        assert bar.volume == 0

    def test_volume_is_int(self):
        bar = ChartBar.from_dict({"v": "99999"})
        assert isinstance(bar.volume, int)
        assert bar.volume == 99999

    def test_float_fields_are_float(self):
        bar = ChartBar.from_dict({"op": "1.5", "cl": "2.5", "hi": "3.5", "lo": "0.5"})
        assert isinstance(bar.open, float)
        assert isinstance(bar.close, float)
        assert isinstance(bar.high, float)
        assert isinstance(bar.low, float)


# ---------------------------------------------------------------------------
# ChartSymbolInfo
# ---------------------------------------------------------------------------


class TestChartSymbolInfo:
    def test_parses_all_fields(self):
        info = ChartSymbolInfo.from_dict(_SYMBOL_DICT)
        assert info.identifier == "SPY"
        assert info.description == "STATE STREET SPDR S&P 500 ETF TRUST"
        assert info.last_trade == pytest.approx(648.56)
        assert info.trade_date == "03/31/2026"
        assert info.day_open == pytest.approx(638.94)
        assert info.day_high == pytest.approx(649.46)
        assert info.day_low == pytest.approx(637.98)
        assert info.net_change == pytest.approx(16.59)
        assert info.net_change_pct == pytest.approx(2.6251)
        assert info.previous_close == pytest.approx(631.97)

    def test_missing_fields_default(self):
        info = ChartSymbolInfo.from_dict({})
        assert info.identifier == ""
        assert info.description == ""
        assert info.last_trade == pytest.approx(0.0)
        assert info.trade_date == ""
        assert info.previous_close == pytest.approx(0.0)

    def test_numeric_fields_are_float(self):
        info = ChartSymbolInfo.from_dict(_SYMBOL_DICT)
        assert isinstance(info.last_trade, float)
        assert isinstance(info.day_open, float)
        assert isinstance(info.day_high, float)
        assert isinstance(info.day_low, float)
        assert isinstance(info.net_change, float)
        assert isinstance(info.net_change_pct, float)
        assert isinstance(info.previous_close, float)


# ---------------------------------------------------------------------------
# ChartResponse
# ---------------------------------------------------------------------------


class TestChartResponse:
    def test_parses_symbol_info(self):
        resp = ChartResponse.from_dict(_CHART_DATA)
        assert resp.symbol_info.identifier == "SPY"
        assert resp.symbol_info.description == "STATE STREET SPDR S&P 500 ETF TRUST"

    def test_parses_bars_count(self):
        resp = ChartResponse.from_dict(_CHART_DATA)
        assert len(resp.bars) == 2

    def test_first_bar_fields(self):
        resp = ChartResponse.from_dict(_CHART_DATA)
        bar = resp.bars[0]
        assert bar.timestamp == "2026/03/30-04:00:00"
        assert bar.open == pytest.approx(636.88)
        assert bar.close == pytest.approx(636.82)
        assert bar.high == pytest.approx(637.07)
        assert bar.low == pytest.approx(634.1)
        assert bar.volume == 112744

    def test_second_bar_fields(self):
        resp = ChartResponse.from_dict(_CHART_DATA)
        bar = resp.bars[1]
        assert bar.timestamp == "2026/03/30-04:05:00"
        assert bar.open == pytest.approx(636.84)
        assert bar.volume == 27237

    def test_empty_symbol_list_raises(self):
        with pytest.raises(ValueError, match="Symbol"):
            ChartResponse.from_dict({"Symbol": []})

    def test_missing_symbol_key_raises(self):
        with pytest.raises(ValueError, match="Symbol"):
            ChartResponse.from_dict({})

    def test_single_bar_as_dict_not_list(self):
        """API may return a bare dict instead of a list when there is one bar."""
        data = {
            "Symbol": [
                {
                    **_SYMBOL_DICT,
                    "BarList": {
                        "BarRecord": {
                            "lt": "2026/03/30-04:00:00",
                            "op": "636.88",
                            "cl": "636.82",
                            "hi": "637.07",
                            "lo": "634.1",
                            "v": "112744",
                        }
                    },
                }
            ]
        }
        resp = ChartResponse.from_dict(data)
        assert len(resp.bars) == 1
        assert resp.bars[0].volume == 112744

    def test_empty_bar_list(self):
        data = {
            "Symbol": [
                {
                    **_SYMBOL_DICT,
                    "BarList": {"BarRecord": []},
                }
            ]
        }
        resp = ChartResponse.from_dict(data)
        assert resp.bars == []

    def test_missing_bar_list(self):
        data = {
            "Symbol": [
                {k: v for k, v in _SYMBOL_DICT.items() if k != "BarList"}
            ]
        }
        resp = ChartResponse.from_dict(data)
        assert resp.bars == []


# ---------------------------------------------------------------------------
# _unwrap_jsonp helper
# ---------------------------------------------------------------------------


class TestUnwrapJsonp:
    def test_unwraps_standard_jsonp(self):
        payload = '{"key": "value"}'
        wrapped = f"jsonp_123({payload})"
        result = _unwrap_jsonp(wrapped, "jsonp_123")
        assert result == {"key": "value"}

    def test_unwraps_with_trailing_whitespace(self):
        payload = '{"x": 1}'
        wrapped = f"jsonp_abc({payload})  \n"
        result = _unwrap_jsonp(wrapped, "jsonp_abc")
        assert result == {"x": 1}

    def test_unwraps_via_regex_fallback(self):
        payload = '{"a": "b"}'
        # Slightly different callback name than what we pass; regex still works
        wrapped = f"some_cb({payload})"
        result = _unwrap_jsonp(wrapped, "some_cb")
        assert result == {"a": "b"}

    def test_raises_on_non_jsonp(self):
        with pytest.raises(ValueError, match="JSONP"):
            _unwrap_jsonp('{"plain": "json"}', "cb")

    def test_unwraps_full_chart_fixture(self):
        result = _unwrap_jsonp(_JSONP_BODY, _CALLBACK)
        assert "Symbol" in result
        assert result["Symbol"][0]["Identifier"] == "SPY"


# ---------------------------------------------------------------------------
# _make_callback
# ---------------------------------------------------------------------------


def test_make_callback_format():
    cb = _make_callback()
    assert cb.startswith("jsonp_")
    parts = cb.split("_")
    assert len(parts) == 3
    assert parts[2] == "1"
    assert parts[1].isdigit()


# ---------------------------------------------------------------------------
# ChartAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------


class TestChartAPI:
    @respx.mock
    def test_get_chart_makes_request_to_correct_url(self):
        route = respx.get(_CHART_URL).mock(
            return_value=httpx.Response(200, text=_JSONP_BODY)
        )
        client = httpx.Client()
        api = ChartAPI(client)
        # Patch _make_callback so we can predict the callback name
        import fidelity_trader.market_data.chart as chart_mod
        original = chart_mod._make_callback
        chart_mod._make_callback = lambda: _CALLBACK
        try:
            result = api.get_chart(
                "SPY",
                "2026/03/30-04:00:00",
                "2026/03/31-20:00:00",
            )
        finally:
            chart_mod._make_callback = original
            client.close()

        assert route.called
        assert isinstance(result, ChartResponse)

    @respx.mock
    def test_get_chart_sends_required_params(self):
        route = respx.get(_CHART_URL).mock(
            return_value=httpx.Response(200, text=_JSONP_BODY)
        )
        client = httpx.Client()
        api = ChartAPI(client)
        import fidelity_trader.market_data.chart as chart_mod
        original = chart_mod._make_callback
        chart_mod._make_callback = lambda: _CALLBACK
        try:
            api.get_chart(
                "SPY",
                "2026/03/30-04:00:00",
                "2026/03/31-20:00:00",
                bar_width="15",
                extended_hours=True,
            )
        finally:
            chart_mod._make_callback = original
            client.close()

        req_url = str(route.calls[0].request.url)
        assert "symbols=SPY" in req_url
        assert "barWidth=15" in req_url
        assert "extendedHours=Y" in req_url
        assert "productid=atn" in req_url
        assert "quoteType=R" in req_url
        assert f"callback={_CALLBACK}" in req_url

    @respx.mock
    def test_get_chart_extended_hours_false_sends_N(self):
        route = respx.get(_CHART_URL).mock(
            return_value=httpx.Response(200, text=_JSONP_BODY)
        )
        client = httpx.Client()
        api = ChartAPI(client)
        import fidelity_trader.market_data.chart as chart_mod
        original = chart_mod._make_callback
        chart_mod._make_callback = lambda: _CALLBACK
        try:
            api.get_chart(
                "SPY",
                "2026/03/30-09:30:00",
                "2026/03/30-16:00:00",
                extended_hours=False,
            )
        finally:
            chart_mod._make_callback = original
            client.close()

        req_url = str(route.calls[0].request.url)
        assert "extendedHours=N" in req_url

    @respx.mock
    def test_get_chart_default_bar_width_is_5(self):
        route = respx.get(_CHART_URL).mock(
            return_value=httpx.Response(200, text=_JSONP_BODY)
        )
        client = httpx.Client()
        api = ChartAPI(client)
        import fidelity_trader.market_data.chart as chart_mod
        original = chart_mod._make_callback
        chart_mod._make_callback = lambda: _CALLBACK
        try:
            api.get_chart("SPY", "2026/03/30-04:00:00", "2026/03/31-20:00:00")
        finally:
            chart_mod._make_callback = original
            client.close()

        req_url = str(route.calls[0].request.url)
        assert "barWidth=5" in req_url

    @respx.mock
    def test_get_chart_parses_response(self):
        respx.get(_CHART_URL).mock(
            return_value=httpx.Response(200, text=_JSONP_BODY)
        )
        client = httpx.Client()
        api = ChartAPI(client)
        import fidelity_trader.market_data.chart as chart_mod
        original = chart_mod._make_callback
        chart_mod._make_callback = lambda: _CALLBACK
        try:
            result = api.get_chart("SPY", "2026/03/30-04:00:00", "2026/03/31-20:00:00")
        finally:
            chart_mod._make_callback = original
            client.close()

        assert result.symbol_info.identifier == "SPY"
        assert result.symbol_info.last_trade == pytest.approx(648.56)
        assert len(result.bars) == 2
        assert result.bars[0].timestamp == "2026/03/30-04:00:00"
        assert result.bars[0].volume == 112744

    @respx.mock
    def test_get_chart_raises_on_http_error(self):
        respx.get(_CHART_URL).mock(return_value=httpx.Response(403))
        client = httpx.Client()
        api = ChartAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_chart("SPY", "2026/03/30-04:00:00", "2026/03/31-20:00:00")
        client.close()

    @respx.mock
    def test_get_chart_daily_bars(self):
        """Smoke test for D bar_width variant."""
        respx.get(_CHART_URL).mock(
            return_value=httpx.Response(200, text=_JSONP_BODY)
        )
        client = httpx.Client()
        api = ChartAPI(client)
        import fidelity_trader.market_data.chart as chart_mod
        original = chart_mod._make_callback
        chart_mod._make_callback = lambda: _CALLBACK
        try:
            result = api.get_chart(
                "SPY",
                "2025/01/01-00:00:00",
                "2026/03/31-00:00:00",
                bar_width="D",
            )
        finally:
            chart_mod._make_callback = original
            client.close()

        assert isinstance(result, ChartResponse)


# ---------------------------------------------------------------------------
# FidelityClient integration: client.chart attribute
# ---------------------------------------------------------------------------


def test_fidelity_client_has_chart_attribute():
    from fidelity_trader import FidelityClient

    with FidelityClient() as client:
        assert isinstance(client.chart, ChartAPI)


def test_fidelity_client_chart_shares_http_client():
    from fidelity_trader import FidelityClient

    with FidelityClient() as client:
        assert client.chart._http is client._http
