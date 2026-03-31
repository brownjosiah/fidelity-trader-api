"""Tests for the watchlist API models and WatchlistAPI client."""
import json

import httpx
import pytest
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.watchlist import (
    Watchlist,
    WatchlistResponse,
    WatchlistSecurity,
)
from fidelity_trader.watchlists.watchlists import WatchlistAPI

_WATCHLIST_URL = (
    f"{DPSERVICE_URL}/ftgw/dp/retail-watchlist/v1/customers/watchlists/get"
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_security(
    symbol: str = "CODI",
    rank_id: int = 1,
    security_id: str = "673d839f-b9fd-46f2-b506-ca482b2b03fd",
) -> dict:
    return {
        "symbol": symbol,
        "cusip": "",
        "securityType": "",
        "newsStateInd": False,
        "watchCloselyInd": False,
        "rankId": rank_id,
        "securityId": security_id,
    }


def _make_watchlist(
    watchlist_id: str = "6a8b8049-f3a2-45fd-b0cc-f2b4bfbfc21c",
    name: str = "Research",
    securities: list[dict] = None,
) -> dict:
    if securities is None:
        securities = [_make_security()]
    return {
        "watchListId": watchlist_id,
        "watchListName": name,
        "watchListTypeCode": "WL",
        "isDefault": False,
        "sortOrder": 1,
        "createdTimeStamp": "2024-09-12 18:14:41.5",
        "lastUpdatedTime": "2025-02-11 18:28:20.6",
        "securityDetails": securities,
    }


def _make_api_response(watchlists: list[dict] = None) -> dict:
    if watchlists is None:
        watchlists = [_make_watchlist()]
    return {
        "sysMsgs": {
            "sysMsg": [
                {
                    "message": "Successfully retreived all Watchlist Details",
                    "code": "2000",
                }
            ]
        },
        "watchListDetails": watchlists,
    }


# ---------------------------------------------------------------------------
# WatchlistSecurity
# ---------------------------------------------------------------------------

class TestWatchlistSecurity:
    def test_parses_all_fields(self):
        sec = WatchlistSecurity.model_validate(_make_security("VRDN", rank_id=3))
        assert sec.symbol == "VRDN"
        assert sec.rank_id == 3
        assert sec.news_state_ind is False
        assert sec.watch_closely_ind is False

    def test_optional_fields_default(self):
        sec = WatchlistSecurity.model_validate({"symbol": "AAPL"})
        assert sec.symbol == "AAPL"
        assert sec.cusip is None
        assert sec.security_type is None
        assert sec.rank_id is None
        assert sec.security_id is None

    def test_security_id_parsed(self):
        uid = "5f5d375a-0a40-43ca-9946-ad1507a7b71b"
        sec = WatchlistSecurity.model_validate({"symbol": "VRDN", "securityId": uid})
        assert sec.security_id == uid

    def test_flags_true(self):
        sec = WatchlistSecurity.model_validate(
            {"symbol": "X", "newsStateInd": True, "watchCloselyInd": True}
        )
        assert sec.news_state_ind is True
        assert sec.watch_closely_ind is True


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

class TestWatchlist:
    def test_parses_all_fields(self):
        wl = Watchlist.model_validate(_make_watchlist())
        assert wl.watchlist_id == "6a8b8049-f3a2-45fd-b0cc-f2b4bfbfc21c"
        assert wl.watchlist_name == "Research"
        assert wl.watchlist_type_code == "WL"
        assert wl.is_default is False
        assert wl.sort_order == 1
        assert wl.created_timestamp == "2024-09-12 18:14:41.5"
        assert wl.last_updated_time == "2025-02-11 18:28:20.6"

    def test_security_details_populated(self):
        wl = Watchlist.model_validate(
            _make_watchlist(
                securities=[
                    _make_security("CODI", 1),
                    _make_security("VRDN", 3),
                    _make_security("BIOA", 4),
                ]
            )
        )
        assert len(wl.security_details) == 3
        assert wl.security_details[0].symbol == "CODI"
        assert wl.security_details[1].symbol == "VRDN"
        assert wl.security_details[2].symbol == "BIOA"

    def test_empty_security_details(self):
        data = dict(_make_watchlist())
        data["securityDetails"] = []
        wl = Watchlist.model_validate(data)
        assert wl.security_details == []

    def test_optional_fields_default(self):
        data = {
            "watchListId": "abc",
            "watchListName": "Test",
            "watchListTypeCode": "WL",
        }
        wl = Watchlist.model_validate(data)
        assert wl.sort_order is None
        assert wl.created_timestamp is None
        assert wl.last_updated_time is None
        assert wl.is_default is False


# ---------------------------------------------------------------------------
# WatchlistResponse — from_api_response
# ---------------------------------------------------------------------------

class TestWatchlistResponse:
    def test_single_watchlist(self):
        raw = _make_api_response()
        resp = WatchlistResponse.from_api_response(raw)
        assert len(resp.watchlists) == 1
        assert resp.watchlists[0].watchlist_name == "Research"

    def test_multiple_watchlists(self):
        raw = _make_api_response([
            _make_watchlist("id-1", "Research"),
            _make_watchlist("id-2", "Tech Stocks"),
        ])
        resp = WatchlistResponse.from_api_response(raw)
        assert len(resp.watchlists) == 2
        assert resp.watchlists[0].watchlist_name == "Research"
        assert resp.watchlists[1].watchlist_name == "Tech Stocks"

    def test_security_details_in_response(self):
        securities = [
            _make_security("CODI", 1),
            _make_security("VRDN", 3),
            _make_security("BIOA", 4),
            _make_security("ELTP", 5),
            _make_security("BVAXF", 6),
        ]
        raw = _make_api_response([_make_watchlist(securities=securities)])
        resp = WatchlistResponse.from_api_response(raw)
        syms = [s.symbol for s in resp.watchlists[0].security_details]
        assert syms == ["CODI", "VRDN", "BIOA", "ELTP", "BVAXF"]

    def test_empty_watchlist_details(self):
        resp = WatchlistResponse.from_api_response({"watchListDetails": []})
        assert resp.watchlists == []

    def test_missing_watchlist_details_key(self):
        resp = WatchlistResponse.from_api_response({})
        assert resp.watchlists == []

    def test_real_traffic_shape(self):
        """Validate against the exact abbreviated response from captured traffic."""
        raw = {
            "sysMsgs": {
                "sysMsg": [
                    {
                        "message": "Successfully retreived all Watchlist Details",
                        "code": "2000",
                    }
                ]
            },
            "watchListDetails": [
                {
                    "watchListId": "6a8b8049-f3a2-45fd-b0cc-f2b4bfbfc21c",
                    "watchListName": "Research",
                    "watchListTypeCode": "WL",
                    "isDefault": False,
                    "sortOrder": 1,
                    "createdTimeStamp": "2024-09-12 18:14:41.5",
                    "lastUpdatedTime": "2025-02-11 18:28:20.6",
                    "securityDetails": [
                        {
                            "symbol": "CODI",
                            "cusip": "",
                            "securityType": "",
                            "newsStateInd": False,
                            "watchCloselyInd": False,
                            "rankId": 1,
                            "securityId": "673d839f-b9fd-46f2-b506-ca482b2b03fd",
                        },
                        {
                            "symbol": "VRDN",
                            "cusip": "",
                            "securityType": "",
                            "newsStateInd": False,
                            "watchCloselyInd": False,
                            "rankId": 3,
                            "securityId": "5f5d375a-0a40-43ca-9946-ad1507a7b71b",
                        },
                        {
                            "symbol": "BIOA",
                            "cusip": "",
                            "securityType": "",
                            "newsStateInd": False,
                            "watchCloselyInd": False,
                            "rankId": 4,
                            "securityId": "76b3f735-f3ea-40e3-963a-06d9b57a7623",
                        },
                        {
                            "symbol": "ELTP",
                            "cusip": "",
                            "securityType": "",
                            "newsStateInd": False,
                            "watchCloselyInd": False,
                            "rankId": 5,
                            "securityId": "12cd41a5-17ee-43d8-8581-79c135eeae8a",
                        },
                        {
                            "symbol": "BVAXF",
                            "cusip": "",
                            "securityType": "",
                            "newsStateInd": False,
                            "watchCloselyInd": False,
                            "rankId": 6,
                            "securityId": "9f0ad7ab-18eb-4f62-bfe4-246ae4a5bd8e",
                        },
                    ],
                }
            ],
        }
        resp = WatchlistResponse.from_api_response(raw)
        assert len(resp.watchlists) == 1
        wl = resp.watchlists[0]
        assert wl.watchlist_id == "6a8b8049-f3a2-45fd-b0cc-f2b4bfbfc21c"
        assert wl.watchlist_name == "Research"
        assert len(wl.security_details) == 5
        assert wl.security_details[4].symbol == "BVAXF"
        assert wl.security_details[4].rank_id == 6
        assert wl.security_details[4].security_id == "9f0ad7ab-18eb-4f62-bfe4-246ae4a5bd8e"


# ---------------------------------------------------------------------------
# WatchlistAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestWatchlistAPI:
    @respx.mock
    def test_get_watchlists_makes_correct_request(self):
        raw = _make_api_response()
        route = respx.post(_WATCHLIST_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = WatchlistAPI(client)
        result = api.get_watchlists()

        assert route.called
        assert isinstance(result, WatchlistResponse)
        assert len(result.watchlists) == 1

    @respx.mock
    def test_get_watchlists_default_request_body(self):
        raw = _make_api_response()
        route = respx.post(_WATCHLIST_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = WatchlistAPI(client)
        api.get_watchlists()

        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["includeWatchListSecurityDetails"] is True
        assert sent_body["positionTypes"] == ["H", "O"]
        wl_entry = sent_body["watchlists"][0]
        assert wl_entry["watchListIds"] == []
        assert wl_entry["watchListTypeCode"] == "WL"

    @respx.mock
    def test_get_watchlists_with_specific_ids(self):
        raw = _make_api_response()
        route = respx.post(_WATCHLIST_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = WatchlistAPI(client)
        uid = "6a8b8049-f3a2-45fd-b0cc-f2b4bfbfc21c"
        api.get_watchlists(watchlist_ids=[uid])

        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["watchlists"][0]["watchListIds"] == [uid]

    @respx.mock
    def test_get_watchlists_custom_params(self):
        raw = _make_api_response()
        route = respx.post(_WATCHLIST_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = WatchlistAPI(client)
        api.get_watchlists(
            include_security_details=False,
            position_types=["H"],
            watchlist_type_code="WL",
        )

        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["includeWatchListSecurityDetails"] is False
        assert sent_body["positionTypes"] == ["H"]

    @respx.mock
    def test_get_watchlists_raises_on_http_error(self):
        respx.post(_WATCHLIST_URL).mock(return_value=httpx.Response(401))
        client = httpx.Client()
        api = WatchlistAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_watchlists()

    @respx.mock
    def test_get_watchlists_returns_all_securities(self):
        securities = [_make_security(sym, i + 1) for i, sym in enumerate(
            ["CODI", "VRDN", "BIOA", "ELTP", "BVAXF"]
        )]
        raw = _make_api_response([_make_watchlist(securities=securities)])
        respx.post(_WATCHLIST_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = WatchlistAPI(client)
        result = api.get_watchlists()

        syms = [s.symbol for s in result.watchlists[0].security_details]
        assert syms == ["CODI", "VRDN", "BIOA", "ELTP", "BVAXF"]

    @respx.mock
    def test_get_watchlists_empty_response(self):
        raw = {"watchListDetails": []}
        respx.post(_WATCHLIST_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = WatchlistAPI(client)
        result = api.get_watchlists()
        assert result.watchlists == []
