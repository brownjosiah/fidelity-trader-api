"""Tests for the staged/saved orders API models and StagedOrderAPI client."""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.staged_order import (
    StagedOrderDetail,
    StagedOrderMessage,
    StagedOrdersResponse,
)
from fidelity_trader.orders.staged import StagedOrderAPI

_STAGED_ORDER_URL = (
    f"{DPSERVICE_URL}/ftgw/dp/ent-research-staging/v1/customers/staged-order/get"
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_empty_response() -> dict:
    """Response captured when no saved orders exist (code 204)."""
    return {
        "messages": [
            {
                "code": "204",
                "severity": "INFO",
                "message": (
                    "NO DATA HAS BEEN RETRIEVED BECAUSE STAGE ID(s) OR "
                    "STAGE TYPE PROVIDED DOES NOT EXIST IN THE TABLE."
                ),
            }
        ]
    }


def _make_populated_response(count: int = 2) -> dict:
    """Synthetic response with staged orders (shape inferred from request)."""
    orders = []
    for i in range(count):
        orders.append(
            {
                "stageId": f"STG{i + 1:04d}",
                "stageType": "saveD_ORDER",
                "symbol": f"SYM{i}",
                "orderActionCode": "B",
            }
        )
    return {"stagedOrders": orders}


def _make_populated_response_with_messages() -> dict:
    """Response with both staged orders and informational messages."""
    return {
        "messages": [
            {
                "code": "200",
                "severity": "INFO",
                "message": "SUCCESS",
            }
        ],
        "stagedOrders": [
            {
                "stageId": "STG0001",
                "stageType": "saveD_ORDER",
            }
        ],
    }


# ---------------------------------------------------------------------------
# StagedOrderMessage
# ---------------------------------------------------------------------------

class TestStagedOrderMessage:
    def test_parses_from_dict(self):
        msg = StagedOrderMessage.model_validate(
            {"code": "204", "severity": "INFO", "message": "no data"}
        )
        assert msg.code == "204"
        assert msg.severity == "INFO"
        assert msg.message == "no data"

    def test_defaults_to_none(self):
        msg = StagedOrderMessage.model_validate({})
        assert msg.code is None
        assert msg.severity is None
        assert msg.message is None


# ---------------------------------------------------------------------------
# StagedOrderDetail
# ---------------------------------------------------------------------------

class TestStagedOrderDetail:
    def test_parses_known_fields(self):
        detail = StagedOrderDetail.from_dict(
            {"stageId": "STG0001", "stageType": "saveD_ORDER"}
        )
        assert detail.stage_id == "STG0001"
        assert detail.stage_type == "saveD_ORDER"

    def test_preserves_raw_dict(self):
        raw = {"stageId": "STG0002", "stageType": "saveD_ORDER", "extra": 42}
        detail = StagedOrderDetail.from_dict(raw)
        assert detail.raw is not None
        assert detail.raw["extra"] == 42

    def test_defaults_to_none(self):
        detail = StagedOrderDetail.model_validate({})
        assert detail.stage_id is None
        assert detail.stage_type is None


# ---------------------------------------------------------------------------
# StagedOrdersResponse — empty (captured traffic)
# ---------------------------------------------------------------------------

class TestStagedOrdersResponseEmpty:
    def test_from_api_response_empty(self):
        resp = StagedOrdersResponse.from_api_response(_make_empty_response())
        assert len(resp.messages) == 1
        assert resp.messages[0].code == "204"
        assert resp.messages[0].severity == "INFO"
        assert resp.staged_orders is None

    def test_is_empty_with_204_message(self):
        resp = StagedOrdersResponse.from_api_response(_make_empty_response())
        assert resp.is_empty is True

    def test_is_empty_with_no_data_at_all(self):
        resp = StagedOrdersResponse.from_api_response({})
        assert resp.is_empty is True

    def test_is_empty_with_empty_staged_orders_list(self):
        resp = StagedOrdersResponse.from_api_response({"stagedOrders": []})
        assert resp.is_empty is True


# ---------------------------------------------------------------------------
# StagedOrdersResponse — populated
# ---------------------------------------------------------------------------

class TestStagedOrdersResponsePopulated:
    def test_from_api_response_with_orders(self):
        resp = StagedOrdersResponse.from_api_response(_make_populated_response(2))
        assert resp.staged_orders is not None
        assert len(resp.staged_orders) == 2
        assert resp.staged_orders[0].stage_id == "STG0001"
        assert resp.staged_orders[1].stage_id == "STG0002"

    def test_is_empty_false_when_orders_present(self):
        resp = StagedOrdersResponse.from_api_response(_make_populated_response(1))
        assert resp.is_empty is False

    def test_single_order(self):
        resp = StagedOrdersResponse.from_api_response(_make_populated_response(1))
        assert resp.staged_orders is not None
        assert len(resp.staged_orders) == 1
        assert resp.staged_orders[0].stage_type == "saveD_ORDER"

    def test_raw_fields_preserved_on_detail(self):
        resp = StagedOrdersResponse.from_api_response(_make_populated_response(1))
        detail = resp.staged_orders[0]
        assert detail.raw is not None
        assert detail.raw["symbol"] == "SYM0"
        assert detail.raw["orderActionCode"] == "B"

    def test_messages_and_orders_coexist(self):
        resp = StagedOrdersResponse.from_api_response(
            _make_populated_response_with_messages()
        )
        assert len(resp.messages) == 1
        assert resp.messages[0].code == "200"
        assert resp.staged_orders is not None
        assert len(resp.staged_orders) == 1
        assert resp.is_empty is False


# ---------------------------------------------------------------------------
# StagedOrderAPI — request body construction
# ---------------------------------------------------------------------------

class TestStagedOrderAPIRequestBody:
    def test_default_body(self):
        body = StagedOrderAPI.build_request_body()
        assert body == {
            "stagedOrders": [
                {"stageType": "saveD_ORDER", "stageIds": []}
            ]
        }

    def test_custom_stage_type(self):
        body = StagedOrderAPI.build_request_body(stage_type="PENDING_ORDER")
        assert body["stagedOrders"][0]["stageType"] == "PENDING_ORDER"

    def test_with_stage_ids(self):
        body = StagedOrderAPI.build_request_body(stage_ids=["ID1", "ID2"])
        assert body["stagedOrders"][0]["stageIds"] == ["ID1", "ID2"]

    def test_stage_ids_none_becomes_empty_list(self):
        body = StagedOrderAPI.build_request_body(stage_ids=None)
        assert body["stagedOrders"][0]["stageIds"] == []


# ---------------------------------------------------------------------------
# StagedOrderAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestStagedOrderAPIClient:
    @respx.mock
    def test_posts_to_correct_url(self):
        route = respx.post(_STAGED_ORDER_URL).mock(
            return_value=httpx.Response(200, json=_make_empty_response())
        )
        api = StagedOrderAPI(httpx.Client())
        result = api.get_staged_orders()

        assert route.called
        assert isinstance(result, StagedOrdersResponse)

    @respx.mock
    def test_request_body_matches_capture(self):
        route = respx.post(_STAGED_ORDER_URL).mock(
            return_value=httpx.Response(200, json=_make_empty_response())
        )
        api = StagedOrderAPI(httpx.Client())
        api.get_staged_orders()

        sent = json.loads(route.calls[0].request.content)
        assert sent == {
            "stagedOrders": [
                {"stageType": "saveD_ORDER", "stageIds": []}
            ]
        }

    @respx.mock
    def test_request_body_with_stage_ids(self):
        route = respx.post(_STAGED_ORDER_URL).mock(
            return_value=httpx.Response(200, json=_make_empty_response())
        )
        api = StagedOrderAPI(httpx.Client())
        api.get_staged_orders(stage_ids=["ABC", "DEF"])

        sent = json.loads(route.calls[0].request.content)
        assert sent["stagedOrders"][0]["stageIds"] == ["ABC", "DEF"]

    @respx.mock
    def test_request_body_custom_stage_type(self):
        route = respx.post(_STAGED_ORDER_URL).mock(
            return_value=httpx.Response(200, json=_make_empty_response())
        )
        api = StagedOrderAPI(httpx.Client())
        api.get_staged_orders(stage_type="CUSTOM_TYPE")

        sent = json.loads(route.calls[0].request.content)
        assert sent["stagedOrders"][0]["stageType"] == "CUSTOM_TYPE"

    @respx.mock
    def test_returns_empty_response(self):
        respx.post(_STAGED_ORDER_URL).mock(
            return_value=httpx.Response(200, json=_make_empty_response())
        )
        api = StagedOrderAPI(httpx.Client())
        result = api.get_staged_orders()

        assert result.is_empty is True
        assert len(result.messages) == 1
        assert result.messages[0].code == "204"

    @respx.mock
    def test_returns_populated_response(self):
        respx.post(_STAGED_ORDER_URL).mock(
            return_value=httpx.Response(200, json=_make_populated_response(3))
        )
        api = StagedOrderAPI(httpx.Client())
        result = api.get_staged_orders()

        assert result.is_empty is False
        assert result.staged_orders is not None
        assert len(result.staged_orders) == 3

    @respx.mock
    def test_raises_on_http_error(self):
        respx.post(_STAGED_ORDER_URL).mock(return_value=httpx.Response(401))
        api = StagedOrderAPI(httpx.Client())
        with pytest.raises(httpx.HTTPStatusError):
            api.get_staged_orders()

    @respx.mock
    def test_raises_on_server_error(self):
        respx.post(_STAGED_ORDER_URL).mock(return_value=httpx.Response(500))
        api = StagedOrderAPI(httpx.Client())
        with pytest.raises(httpx.HTTPStatusError):
            api.get_staged_orders()
