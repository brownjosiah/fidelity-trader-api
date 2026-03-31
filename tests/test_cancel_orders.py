"""Tests for the order cancellation API models and OrderCancelAPI client."""
from __future__ import annotations

import json
import pytest
import httpx
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.cancel_order import CancelConfirmDetail, CancelResponse
from fidelity_trader.orders.cancel import OrderCancelAPI

_CANCEL_URL = f"{DPSERVICE_URL}/ftgw/dp/orderentry/cancel/place/v1"

# ---------------------------------------------------------------------------
# Helpers matching captured traffic
# ---------------------------------------------------------------------------

def _make_cancel_api_response(
    resp_type_code: str = "A",
    conf_num: str = "24A0JX2V",
    acct_num: str = "Z21772945",
    action_code: str = "B",
) -> dict:
    return {
        "place": {
            "cancelConfirmDetail": [
                {
                    "respTypeCode": resp_type_code,
                    "confNum": conf_num,
                    "acctNum": acct_num,
                    "actionCode": action_code,
                    "actionCodeDesc": "Buy",
                    "origQty": 1,
                    "execQty": 0,
                    "remainingQty": 1,
                }
            ]
        }
    }


# ---------------------------------------------------------------------------
# CancelConfirmDetail
# ---------------------------------------------------------------------------

class TestCancelConfirmDetail:
    def test_parses_from_captured_response(self):
        raw = {
            "respTypeCode": "A",
            "confNum": "24A0JX2V",
            "acctNum": "Z21772945",
            "actionCode": "B",
            "actionCodeDesc": "Buy",
            "origQty": 1,
            "execQty": 0,
            "remainingQty": 1,
        }
        detail = CancelConfirmDetail.model_validate(raw)
        assert detail.resp_type_code == "A"
        assert detail.conf_num == "24A0JX2V"
        assert detail.acct_num == "Z21772945"
        assert detail.action_code == "B"
        assert detail.action_code_desc == "Buy"
        assert detail.orig_qty == pytest.approx(1)
        assert detail.exec_qty == pytest.approx(0)
        assert detail.remaining_qty == pytest.approx(1)

    def test_is_accepted_true_when_a(self):
        detail = CancelConfirmDetail.model_validate({"respTypeCode": "A"})
        assert detail.is_accepted is True

    def test_is_accepted_false_when_not_a(self):
        detail = CancelConfirmDetail.model_validate({"respTypeCode": "E"})
        assert detail.is_accepted is False

    def test_is_accepted_false_when_none(self):
        detail = CancelConfirmDetail.model_validate({})
        assert detail.is_accepted is False

    def test_optional_fields_default_none(self):
        detail = CancelConfirmDetail.model_validate({})
        assert detail.resp_type_code is None
        assert detail.conf_num is None
        assert detail.acct_num is None
        assert detail.action_code is None
        assert detail.action_code_desc is None
        assert detail.orig_qty is None
        assert detail.exec_qty is None
        assert detail.remaining_qty is None


# ---------------------------------------------------------------------------
# CancelResponse
# ---------------------------------------------------------------------------

class TestCancelResponse:
    def test_from_api_response_parses_captured_traffic(self):
        resp = CancelResponse.from_api_response(_make_cancel_api_response())
        assert len(resp.cancel_confirm_detail) == 1
        detail = resp.cancel_confirm_detail[0]
        assert detail.resp_type_code == "A"
        assert detail.conf_num == "24A0JX2V"
        assert detail.acct_num == "Z21772945"
        assert detail.action_code == "B"
        assert detail.action_code_desc == "Buy"
        assert detail.orig_qty == pytest.approx(1)
        assert detail.exec_qty == pytest.approx(0)
        assert detail.remaining_qty == pytest.approx(1)

    def test_is_accepted_true_when_detail_is_accepted(self):
        resp = CancelResponse.from_api_response(_make_cancel_api_response(resp_type_code="A"))
        assert resp.is_accepted is True

    def test_is_accepted_false_when_not_accepted(self):
        resp = CancelResponse.from_api_response(_make_cancel_api_response(resp_type_code="E"))
        assert resp.is_accepted is False

    def test_is_accepted_false_on_empty_response(self):
        resp = CancelResponse.from_api_response({})
        assert resp.is_accepted is False
        assert resp.cancel_confirm_detail == []

    def test_from_api_response_missing_place_key(self):
        resp = CancelResponse.from_api_response({"other": {}})
        assert resp.cancel_confirm_detail == []

    def test_conf_num_accessible(self):
        resp = CancelResponse.from_api_response(_make_cancel_api_response(conf_num="24A0JX2V"))
        assert resp.cancel_confirm_detail[0].conf_num == "24A0JX2V"


# ---------------------------------------------------------------------------
# OrderCancelAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestOrderCancelAPI:
    @respx.mock
    def test_cancel_posts_to_correct_url(self):
        route = respx.post(_CANCEL_URL).mock(
            return_value=httpx.Response(200, json=_make_cancel_api_response())
        )
        api = OrderCancelAPI(httpx.Client())
        result = api.cancel_order("24A0JX2V", "Z21772945", "B")

        assert route.called
        assert isinstance(result, CancelResponse)

    @respx.mock
    def test_cancel_request_body_matches_captured_traffic(self):
        route = respx.post(_CANCEL_URL).mock(
            return_value=httpx.Response(200, json=_make_cancel_api_response())
        )
        api = OrderCancelAPI(httpx.Client())
        api.cancel_order("24A0JX2V", "Z21772945", "B")

        sent = json.loads(route.calls[0].request.content)
        params = sent["request"]["parameter"]
        assert params["previewInd"] is False
        assert params["confInd"] is False
        detail = params["cancelOrderDetail"][0]
        assert detail["confNum"] == "24A0JX2V"
        assert detail["acctNum"] == "Z21772945"
        assert detail["actionCode"] == "B"

    @respx.mock
    def test_cancel_returns_accepted_response(self):
        respx.post(_CANCEL_URL).mock(
            return_value=httpx.Response(200, json=_make_cancel_api_response())
        )
        api = OrderCancelAPI(httpx.Client())
        result = api.cancel_order("24A0JX2V", "Z21772945", "B")

        assert result.is_accepted
        assert result.cancel_confirm_detail[0].conf_num == "24A0JX2V"

    @respx.mock
    def test_cancel_raises_on_http_error(self):
        respx.post(_CANCEL_URL).mock(return_value=httpx.Response(401))
        api = OrderCancelAPI(httpx.Client())
        with pytest.raises(httpx.HTTPStatusError):
            api.cancel_order("24A0JX2V", "Z21772945", "B")

    @respx.mock
    def test_cancel_raises_on_server_error(self):
        respx.post(_CANCEL_URL).mock(return_value=httpx.Response(500))
        api = OrderCancelAPI(httpx.Client())
        with pytest.raises(httpx.HTTPStatusError):
            api.cancel_order("24A0JX2V", "Z21772945", "B")
