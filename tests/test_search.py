"""Tests for the symbol autosuggest API models and SearchAPI client."""
import pytest
import httpx
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.search import Suggestion, AutosuggestResponse
from fidelity_trader.research.search import SearchAPI

_AUTOSUGGEST_URL = f"{DPSERVICE_URL}/ftgw/dpdirect/search/autosuggest/v1"

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_SAMPLE_RESPONSE = {
    "quotes": {
        "count": 6,
        "suggestions": [
            {
                "symbol": "S",
                "cusip": "81730H109",
                "desc": "Sentinelone Class A",
                "type": "EQ",
                "subType": "COM",
                "exchange": "N",
                "nc": False,
                "intl": False,
                "tradeEligible": True,
                "options": ["Std"],
            },
            {
                "symbol": "SPAXX",
                "cusip": "31617H102",
                "desc": "FIDELITY GOVERNMENT MONEY MARKET FUND",
                "type": "MMF",
                "subType": "Govt",
                "exchange": "Q",
                "nc": False,
                "intl": False,
                "tradeEligible": True,
            },
            {
                "symbol": ".SPX",
                "cusip": "648815108",
                "desc": "S&P 500 INDEX",
                "type": "IX",
                "subType": "",
                "exchange": "WI1",
                "nc": False,
                "intl": False,
                "tradeEligible": True,
                "options": ["Std"],
            },
            {
                "symbol": "SPY",
                "cusip": "78462F103",
                "desc": "State Street SPDR S&P 500 ETF Trust",
                "type": "ETP",
                "subType": "ETF",
                "exchange": "P",
                "nc": False,
                "intl": False,
                "tradeEligible": True,
                "options": ["Std"],
            },
            {
                "symbol": "TSM",
                "cusip": "874039100",
                "desc": "Taiwan Semiconductor Manufacturing ADR",
                "type": "EQ",
                "subType": "ADR",
                "exchange": "N",
                "nc": False,
                "intl": False,
                "tradeEligible": True,
                "options": ["Std"],
            },
            {
                "symbol": "SCHD",
                "cusip": "808524797",
                "desc": "Schwab US Dividend Equity ETF",
                "type": "ETP",
                "subType": "ETF",
                "exchange": "P",
                "nc": False,
                "intl": False,
                "tradeEligible": True,
                "options": ["Std"],
            },
        ],
    }
}


# ---------------------------------------------------------------------------
# Suggestion model
# ---------------------------------------------------------------------------

class TestSuggestion:
    def test_parses_equity_with_options(self):
        raw = _SAMPLE_RESPONSE["quotes"]["suggestions"][0]
        s = Suggestion.model_validate(raw)
        assert s.symbol == "S"
        assert s.cusip == "81730H109"
        assert s.desc == "Sentinelone Class A"
        assert s.type == "EQ"
        assert s.sub_type == "COM"
        assert s.exchange == "N"
        assert s.nc is False
        assert s.intl is False
        assert s.trade_eligible is True
        assert s.options == ["Std"]

    def test_parses_mmf_without_options_field(self):
        raw = _SAMPLE_RESPONSE["quotes"]["suggestions"][1]
        s = Suggestion.model_validate(raw)
        assert s.symbol == "SPAXX"
        assert s.type == "MMF"
        assert s.sub_type == "Govt"
        assert s.options is None

    def test_parses_index_symbol(self):
        raw = _SAMPLE_RESPONSE["quotes"]["suggestions"][2]
        s = Suggestion.model_validate(raw)
        assert s.symbol == ".SPX"
        assert s.type == "IX"
        assert s.sub_type == ""

    def test_parses_etf(self):
        raw = _SAMPLE_RESPONSE["quotes"]["suggestions"][3]
        s = Suggestion.model_validate(raw)
        assert s.symbol == "SPY"
        assert s.type == "ETP"
        assert s.sub_type == "ETF"

    def test_optional_fields_default_none(self):
        s = Suggestion.model_validate({"symbol": "AAPL"})
        assert s.cusip is None
        assert s.desc is None
        assert s.type is None
        assert s.sub_type is None
        assert s.exchange is None
        assert s.nc is None
        assert s.intl is None
        assert s.trade_eligible is None
        assert s.options is None

    def test_sub_type_alias(self):
        s = Suggestion.model_validate({"symbol": "SPY", "subType": "ETF"})
        assert s.sub_type == "ETF"

    def test_trade_eligible_alias(self):
        s = Suggestion.model_validate({"symbol": "SPY", "tradeEligible": False})
        assert s.trade_eligible is False


# ---------------------------------------------------------------------------
# AutosuggestResponse model
# ---------------------------------------------------------------------------

class TestAutosuggestResponse:
    def test_parses_full_response(self):
        resp = AutosuggestResponse.from_api_response(_SAMPLE_RESPONSE)
        assert resp.count == 6
        assert len(resp.suggestions) == 6

    def test_first_suggestion_symbol(self):
        resp = AutosuggestResponse.from_api_response(_SAMPLE_RESPONSE)
        assert resp.suggestions[0].symbol == "S"

    def test_all_symbols_present(self):
        resp = AutosuggestResponse.from_api_response(_SAMPLE_RESPONSE)
        symbols = [s.symbol for s in resp.suggestions]
        assert symbols == ["S", "SPAXX", ".SPX", "SPY", "TSM", "SCHD"]

    def test_empty_response(self):
        resp = AutosuggestResponse.from_api_response({})
        assert resp.count == 0
        assert resp.suggestions == []

    def test_empty_suggestions_list(self):
        raw = {"quotes": {"count": 0, "suggestions": []}}
        resp = AutosuggestResponse.from_api_response(raw)
        assert resp.count == 0
        assert resp.suggestions == []

    def test_missing_quotes_key(self):
        resp = AutosuggestResponse.from_api_response({"other": "data"})
        assert resp.count == 0
        assert resp.suggestions == []

    def test_count_reflects_api_value(self):
        raw = {
            "quotes": {
                "count": 2,
                "suggestions": [
                    {"symbol": "AAPL", "type": "EQ"},
                    {"symbol": "AMZN", "type": "EQ"},
                ],
            }
        }
        resp = AutosuggestResponse.from_api_response(raw)
        assert resp.count == 2
        assert len(resp.suggestions) == 2


# ---------------------------------------------------------------------------
# SearchAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestSearchAPI:
    @respx.mock
    def test_autosuggest_makes_correct_request(self):
        route = respx.get(_AUTOSUGGEST_URL).mock(
            return_value=httpx.Response(200, json=_SAMPLE_RESPONSE)
        )
        client = httpx.Client()
        api = SearchAPI(client)
        result = api.autosuggest("S")

        assert route.called
        assert isinstance(result, AutosuggestResponse)

    @respx.mock
    def test_autosuggest_passes_q_param(self):
        route = respx.get(_AUTOSUGGEST_URL).mock(
            return_value=httpx.Response(200, json=_SAMPLE_RESPONSE)
        )
        client = httpx.Client()
        api = SearchAPI(client)
        api.autosuggest("SPY")

        request = route.calls[0].request
        assert "q=SPY" in str(request.url)

    @respx.mock
    def test_autosuggest_query_with_special_chars(self):
        route = respx.get(_AUTOSUGGEST_URL).mock(
            return_value=httpx.Response(200, json=_SAMPLE_RESPONSE)
        )
        client = httpx.Client()
        api = SearchAPI(client)
        api.autosuggest(".SPX")

        request = route.calls[0].request
        assert ".SPX" in str(request.url) or "%2ESPX" in str(request.url)

    @respx.mock
    def test_autosuggest_returns_parsed_response(self):
        respx.get(_AUTOSUGGEST_URL).mock(
            return_value=httpx.Response(200, json=_SAMPLE_RESPONSE)
        )
        client = httpx.Client()
        api = SearchAPI(client)
        result = api.autosuggest("S")

        assert result.count == 6
        assert len(result.suggestions) == 6
        assert result.suggestions[0].symbol == "S"
        assert result.suggestions[2].symbol == ".SPX"
        assert result.suggestions[3].type == "ETP"

    @respx.mock
    def test_autosuggest_raises_on_http_error(self):
        respx.get(_AUTOSUGGEST_URL).mock(return_value=httpx.Response(401))
        client = httpx.Client()
        api = SearchAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.autosuggest("S")

    @respx.mock
    def test_autosuggest_raises_on_server_error(self):
        respx.get(_AUTOSUGGEST_URL).mock(return_value=httpx.Response(500))
        client = httpx.Client()
        api = SearchAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.autosuggest("AAPL")

    @respx.mock
    def test_autosuggest_empty_query(self):
        empty_resp = {"quotes": {"count": 0, "suggestions": []}}
        respx.get(_AUTOSUGGEST_URL).mock(
            return_value=httpx.Response(200, json=empty_resp)
        )
        client = httpx.Client()
        api = SearchAPI(client)
        result = api.autosuggest("")

        assert result.count == 0
        assert result.suggestions == []

    @respx.mock
    def test_autosuggest_single_result(self):
        single_resp = {
            "quotes": {
                "count": 1,
                "suggestions": [
                    {
                        "symbol": "AAPL",
                        "cusip": "037833100",
                        "desc": "Apple Inc",
                        "type": "EQ",
                        "subType": "COM",
                        "exchange": "Q",
                        "nc": False,
                        "intl": False,
                        "tradeEligible": True,
                        "options": ["Std"],
                    }
                ],
            }
        }
        respx.get(_AUTOSUGGEST_URL).mock(
            return_value=httpx.Response(200, json=single_resp)
        )
        client = httpx.Client()
        api = SearchAPI(client)
        result = api.autosuggest("AAPL")

        assert result.count == 1
        assert result.suggestions[0].symbol == "AAPL"
        assert result.suggestions[0].cusip == "037833100"
        assert result.suggestions[0].trade_eligible is True
