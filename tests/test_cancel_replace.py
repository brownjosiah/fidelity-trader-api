"""Tests for cancel-and-replace (order modification) models and CancelReplaceAPI client."""
from __future__ import annotations

import json
import pytest
import httpx
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.cancel_replace import (
    CancelReplaceRequest,
    CancelReplacePreviewResponse,
    CancelReplacePlaceResponse,
    CancelReplaceOrderConfirmDetail,
    CancelReplaceConfirmMsgs,
    OrderConfirmMessage,
)
from fidelity_trader.orders.cancel_replace import CancelReplaceAPI

_PREVIEW_URL = f"{DPSERVICE_URL}/ftgw/dp/orderentry/cancelandreplace/preview/v1"
_PLACE_URL = f"{DPSERVICE_URL}/ftgw/dp/orderentry/cancelandreplace/place/v1"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_cr_request(
    acct_num: str = "Z21772945",
    order_num_orig: str = "24C0ZBR7",
    symbol: str = "QS",
    cusip: str = "74767V109",
    order_action_code: str = "B",
    acct_type_code: str = "M",
    qty: float = 1,
    qty_type_code: str = "S",
    tif_code: str = "D",
    price_type_code: str = "L",
    limit_price: float = 5.0,
    mkt_route_code: str = "",
) -> CancelReplaceRequest:
    return CancelReplaceRequest(
        acctNum=acct_num,
        orderNumOrig=order_num_orig,
        symbol=symbol,
        cusip=cusip,
        orderActionCode=order_action_code,
        acctTypeCode=acct_type_code,
        qty=qty,
        qtyTypeCode=qty_type_code,
        tifCode=tif_code,
        priceTypeCode=price_type_code,
        limitPrice=limit_price,
        mktRouteCode=mkt_route_code,
    )


def _make_confirm_detail(
    resp_type_code: str = "V",
    conf_num: str = "24C0SZD3",
) -> dict:
    return {
        "respTypeCode": resp_type_code,
        "confNum": conf_num,
        "acctNum": "Z21772945",
        "acctTypeCode": "M",
        "priceDetail": {
            "price": 6.195,
            "priceDateTime": 1775147628,
            "bidPrice": 6.19,
            "askPrice": 6.2,
        },
        "estCommissionDetail": {
            "estCommission": 0.0,
            "typeCode": "30",
        },
        "dtcEstFee": 0,
        "netAmount": 5,
        "netProceedsInclusive": 5,
        "orderDetail": {
            "acctNum": "Z21772945",
            "baseOrderDetail": {
                "orderActionCode": "B",
                "actionCodeDesc": "Buy",
                "qty": 1,
                "qtyTypeCode": "S",
                "valOfOrder": 5,
                "securityDetail": {
                    "symbol": "QS",
                    "cusip": "74767V109",
                    "secDesc": "QUANTUMSCAPE CLASS A",
                },
            },
            "tradableSecOrderDetail": {
                "priceTypeDetail": {
                    "priceTypeCode": "L",
                    "priceTypeDesc": "Limit",
                    "limitPrice": 5,
                },
                "tifCode": "D",
                "mktRouteCode": "",
            },
        },
    }


def _make_error_confirm_detail(conf_num: str = "24C0SZF5") -> dict:
    detail = _make_confirm_detail(resp_type_code="E", conf_num=conf_num)
    detail["errorCategories"] = ["UNKNOWN"]
    detail["netAmount"] = 7
    detail["netProceedsInclusive"] = 7
    detail["orderDetail"]["baseOrderDetail"]["valOfOrder"] = 7
    detail["orderDetail"]["baseOrderDetail"]["securityDetail"]["secDesc"] = "QUANTUMSCAPE CLASS A"
    detail["orderDetail"]["tradableSecOrderDetail"]["priceTypeDetail"]["limitPrice"] = 7
    return detail


def _make_preview_response(conf_num: str = "24C0SZD3") -> dict:
    return {
        "cancelandreplace": {
            "acctNum": "Z21772945",
            "orderNumOrig": "24C0ZBR7",
            "orderConfirmDetail": _make_confirm_detail(
                resp_type_code="V", conf_num=conf_num
            ),
        }
    }


def _make_error_preview_response(conf_num: str = "24C0SZF5") -> dict:
    return {
        "cancelandreplace": {
            "acctNum": "Z21772945",
            "orderNumOrig": "24C0SZD3",
            "orderConfirmMsgs": {
                "orderConfirmMessage": [
                    {
                        "message": "other",
                        "detail": (
                            "Code=MA5010,Text=The limit price entered is too far "
                            "away from the last trade for this security. Please "
                            "correct and re-submit your order.,Source="
                        ),
                        "source": "EquityOptionPreview",
                        "code": "2999",
                        "type": "error",
                    }
                ]
            },
            "orderConfirmDetail": _make_error_confirm_detail(conf_num=conf_num),
        }
    }


def _make_place_response(conf_num: str = "24C0SZD3") -> dict:
    return {
        "cancelandreplace": {
            "acctNum": "Z21772945",
            "orderNumOrig": "24C0ZBR7",
            "orderConfirmDetail": _make_confirm_detail(
                resp_type_code="A", conf_num=conf_num
            ),
        }
    }


# ---------------------------------------------------------------------------
# CancelReplaceRequest — body construction
# ---------------------------------------------------------------------------

class TestCancelReplaceRequest:
    def test_to_preview_body_shape(self):
        order = _make_cr_request()
        body = order.to_preview_body()

        params = body["request"]["parameter"]
        base = params["baseOrderDetail"]
        tradable = params["tradableSecOrderDetail"]

        assert base["orderActionCode"] == "B"
        assert base["acctTypeCode"] == "M"
        assert base["qty"] == 1
        assert base["qtyTypeCode"] == "S"
        assert base["securityDetail"]["symbol"] == "QS"
        assert base["securityDetail"]["cusip"] == "74767V109"
        assert "confNum" not in base

        assert tradable["tifCode"] == "D"
        assert tradable["priceTypeDetail"]["priceTypeCode"] == "L"
        assert tradable["priceTypeDetail"]["limitPrice"] == pytest.approx(5.0)
        assert tradable["mktRouteCode"] == ""

        assert params["orderNumOrig"] == "24C0ZBR7"
        assert params["acctNum"] == "Z21772945"
        assert "previewInd" not in params
        assert "confInd" not in params

    def test_order_num_orig_at_parameter_level_preview(self):
        order = _make_cr_request()
        body = order.to_preview_body()
        params = body["request"]["parameter"]
        assert "orderNumOrig" in params
        assert params["orderNumOrig"] == "24C0ZBR7"
        # Must NOT be inside baseOrderDetail
        assert "orderNumOrig" not in params["baseOrderDetail"]

    def test_order_num_orig_at_parameter_level_place(self):
        order = _make_cr_request()
        body = order.to_place_body("24C0SZD3")
        params = body["request"]["parameter"]
        assert "orderNumOrig" in params
        assert params["orderNumOrig"] == "24C0ZBR7"
        assert "orderNumOrig" not in params["baseOrderDetail"]

    def test_to_place_body_injects_conf_num_in_base_order_detail(self):
        order = _make_cr_request()
        body = order.to_place_body("24C0SZD3")

        params = body["request"]["parameter"]
        base = params["baseOrderDetail"]

        assert base["confNum"] == "24C0SZD3"

    def test_to_place_body_sets_preview_and_conf_ind(self):
        order = _make_cr_request()
        body = order.to_place_body("24C0SZD3")

        params = body["request"]["parameter"]
        assert params["previewInd"] is True
        assert params["confInd"] is True

    def test_to_place_body_does_not_include_mkt_route_code(self):
        """Place body omits mktRouteCode in tradableSecOrderDetail per captured traffic."""
        order = _make_cr_request()
        body = order.to_place_body("24C0SZD3")
        tradable = body["request"]["parameter"]["tradableSecOrderDetail"]
        assert "mktRouteCode" not in tradable

    def test_cusip_included_in_security_detail(self):
        order = _make_cr_request(cusip="74767V109")
        body = order.to_preview_body()
        sec = body["request"]["parameter"]["baseOrderDetail"]["securityDetail"]
        assert sec["cusip"] == "74767V109"

    def test_cusip_omitted_when_none(self):
        order = _make_cr_request(cusip=None)
        # Workaround: cusip is provided as a kwarg, need to construct without it
        order_no_cusip = CancelReplaceRequest(
            acctNum="Z21772945",
            orderNumOrig="24C0ZBR7",
            symbol="QS",
            orderActionCode="B",
            qty=1,
        )
        body = order_no_cusip.to_preview_body()
        sec = body["request"]["parameter"]["baseOrderDetail"]["securityDetail"]
        assert "cusip" not in sec

    def test_market_order_omits_limit_price(self):
        order = CancelReplaceRequest(
            acctNum="Z21772945",
            orderNumOrig="24C0ZBR7",
            symbol="QS",
            orderActionCode="B",
            qty=10,
            priceTypeCode="M",
        )
        body = order.to_preview_body()
        ptd = body["request"]["parameter"]["tradableSecOrderDetail"]["priceTypeDetail"]
        assert ptd["priceTypeCode"] == "M"
        assert "limitPrice" not in ptd

    def test_sell_order(self):
        order = _make_cr_request(order_action_code="S", qty=5, symbol="TSLA")
        body = order.to_preview_body()
        base = body["request"]["parameter"]["baseOrderDetail"]
        assert base["orderActionCode"] == "S"
        assert base["qty"] == 5
        assert base["securityDetail"]["symbol"] == "TSLA"

    def test_gtc_tif_code(self):
        order = _make_cr_request(tif_code="G")
        body = order.to_preview_body()
        tradable = body["request"]["parameter"]["tradableSecOrderDetail"]
        assert tradable["tifCode"] == "G"

    def test_cash_account_type(self):
        order = _make_cr_request(acct_type_code="C")
        body = order.to_preview_body()
        base = body["request"]["parameter"]["baseOrderDetail"]
        assert base["acctTypeCode"] == "C"

    def test_defaults(self):
        order = CancelReplaceRequest(
            acctNum="Z99999999",
            orderNumOrig="24X0AAAA",
            symbol="MSFT",
            orderActionCode="B",
            qty=3,
        )
        assert order.acct_type_code == "M"
        assert order.qty_type_code == "S"
        assert order.tif_code == "D"
        assert order.price_type_code == "L"
        assert order.mkt_route_code == ""
        assert order.cusip is None
        assert order.limit_price is None

    def test_preview_body_no_price_detail_key(self):
        """Cancel-and-replace preview does not include empty priceDetail (unlike equity)."""
        order = _make_cr_request()
        body = order.to_preview_body()
        params = body["request"]["parameter"]
        assert "priceDetail" not in params


# ---------------------------------------------------------------------------
# OrderConfirmMessage
# ---------------------------------------------------------------------------

class TestOrderConfirmMessage:
    def test_parses_all_fields(self):
        msg = OrderConfirmMessage.model_validate({
            "message": "other",
            "detail": "Code=MA5010,Text=limit price too far",
            "source": "EquityOptionPreview",
            "code": "2999",
            "type": "error",
        })
        assert msg.message == "other"
        assert "MA5010" in msg.detail
        assert msg.source == "EquityOptionPreview"
        assert msg.code == "2999"
        assert msg.type == "error"

    def test_optional_fields_default_none(self):
        msg = OrderConfirmMessage.model_validate({})
        assert msg.message is None
        assert msg.detail is None
        assert msg.source is None
        assert msg.code is None
        assert msg.type is None


# ---------------------------------------------------------------------------
# CancelReplaceConfirmMsgs
# ---------------------------------------------------------------------------

class TestCancelReplaceConfirmMsgs:
    def test_parses_message_list(self):
        msgs = CancelReplaceConfirmMsgs.model_validate({
            "orderConfirmMessage": [
                {"message": "other", "code": "2999", "type": "error"},
                {"message": "warning", "code": "1000", "type": "warning"},
            ]
        })
        assert len(msgs.messages) == 2
        assert msgs.messages[0].code == "2999"
        assert msgs.messages[1].code == "1000"

    def test_empty_list(self):
        msgs = CancelReplaceConfirmMsgs.model_validate({"orderConfirmMessage": []})
        assert msgs.messages == []

    def test_defaults_to_empty(self):
        msgs = CancelReplaceConfirmMsgs.model_validate({})
        assert msgs.messages == []


# ---------------------------------------------------------------------------
# CancelReplaceOrderConfirmDetail
# ---------------------------------------------------------------------------

class TestCancelReplaceOrderConfirmDetail:
    def test_parses_preview_confirm_detail(self):
        detail = CancelReplaceOrderConfirmDetail.model_validate(
            _make_confirm_detail("V")
        )
        assert detail.resp_type_code == "V"
        assert detail.conf_num == "24C0SZD3"
        assert detail.acct_num == "Z21772945"
        assert detail.acct_type_code == "M"
        assert detail.net_amount == pytest.approx(5)
        assert detail.dtc_est_fee == pytest.approx(0)
        assert detail.net_proceeds_inclusive == pytest.approx(5)

    def test_parses_price_detail(self):
        detail = CancelReplaceOrderConfirmDetail.model_validate(
            _make_confirm_detail("V")
        )
        pd = detail.price_detail
        assert pd is not None
        assert pd.price == pytest.approx(6.195)
        assert pd.bid_price == pytest.approx(6.19)
        assert pd.ask_price == pytest.approx(6.2)
        assert pd.price_date_time == 1775147628

    def test_parses_commission_detail(self):
        detail = CancelReplaceOrderConfirmDetail.model_validate(
            _make_confirm_detail("V")
        )
        ec = detail.est_commission_detail
        assert ec is not None
        assert ec.est_commission == pytest.approx(0.0)
        assert ec.type_code == "30"

    def test_parses_nested_order_detail(self):
        detail = CancelReplaceOrderConfirmDetail.model_validate(
            _make_confirm_detail("V")
        )
        od = detail.order_detail
        assert od is not None
        assert od.acct_num == "Z21772945"
        base = od.base_order_detail
        assert base is not None
        assert base.order_action_code == "B"
        assert base.action_code_desc == "Buy"
        assert base.qty == pytest.approx(1)
        sec = base.security_detail
        assert sec is not None
        assert sec.symbol == "QS"
        assert sec.cusip == "74767V109"
        assert sec.sec_desc == "QUANTUMSCAPE CLASS A"

    def test_parses_error_categories(self):
        detail = CancelReplaceOrderConfirmDetail.model_validate(
            _make_error_confirm_detail()
        )
        assert detail.resp_type_code == "E"
        assert detail.error_categories == ["UNKNOWN"]

    def test_optional_fields_default_none(self):
        detail = CancelReplaceOrderConfirmDetail.model_validate({})
        assert detail.resp_type_code is None
        assert detail.conf_num is None
        assert detail.price_detail is None
        assert detail.order_detail is None
        assert detail.error_categories is None


# ---------------------------------------------------------------------------
# CancelReplacePreviewResponse
# ---------------------------------------------------------------------------

class TestCancelReplacePreviewResponse:
    def test_from_api_response_parsed(self):
        resp = CancelReplacePreviewResponse.from_api_response(
            _make_preview_response()
        )
        assert resp.acct_num == "Z21772945"
        assert resp.order_num_orig == "24C0ZBR7"
        assert resp.order_confirm_detail is not None
        assert resp.order_confirm_detail.resp_type_code == "V"

    def test_conf_num_property(self):
        resp = CancelReplacePreviewResponse.from_api_response(
            _make_preview_response("24C0SZD3")
        )
        assert resp.conf_num == "24C0SZD3"

    def test_is_validated_true(self):
        resp = CancelReplacePreviewResponse.from_api_response(
            _make_preview_response()
        )
        assert resp.is_validated is True

    def test_is_validated_false_when_error(self):
        resp = CancelReplacePreviewResponse.from_api_response(
            _make_error_preview_response()
        )
        assert resp.is_validated is False

    def test_is_error_true(self):
        resp = CancelReplacePreviewResponse.from_api_response(
            _make_error_preview_response()
        )
        assert resp.is_error is True

    def test_is_error_false_when_validated(self):
        resp = CancelReplacePreviewResponse.from_api_response(
            _make_preview_response()
        )
        assert resp.is_error is False

    def test_error_messages_populated(self):
        resp = CancelReplacePreviewResponse.from_api_response(
            _make_error_preview_response()
        )
        msgs = resp.error_messages
        assert len(msgs) == 1
        assert msgs[0].code == "2999"
        assert msgs[0].type == "error"
        assert "MA5010" in msgs[0].detail

    def test_error_messages_empty_on_success(self):
        resp = CancelReplacePreviewResponse.from_api_response(
            _make_preview_response()
        )
        assert resp.error_messages == []

    def test_conf_num_none_on_empty(self):
        resp = CancelReplacePreviewResponse.from_api_response({})
        assert resp.conf_num is None
        assert resp.is_validated is False
        assert resp.is_error is False

    def test_security_detail_accessible(self):
        resp = CancelReplacePreviewResponse.from_api_response(
            _make_preview_response()
        )
        sec = resp.order_confirm_detail.order_detail.base_order_detail.security_detail
        assert sec.symbol == "QS"
        assert sec.cusip == "74767V109"

    def test_order_num_orig_on_response(self):
        resp = CancelReplacePreviewResponse.from_api_response(
            _make_preview_response()
        )
        assert resp.order_num_orig == "24C0ZBR7"


# ---------------------------------------------------------------------------
# CancelReplacePlaceResponse
# ---------------------------------------------------------------------------

class TestCancelReplacePlaceResponse:
    def test_from_api_response_parsed(self):
        resp = CancelReplacePlaceResponse.from_api_response(
            _make_place_response()
        )
        assert resp.acct_num == "Z21772945"
        assert resp.order_num_orig == "24C0ZBR7"
        assert resp.order_confirm_detail is not None
        assert resp.order_confirm_detail.resp_type_code == "A"

    def test_conf_num_property(self):
        resp = CancelReplacePlaceResponse.from_api_response(
            _make_place_response("24C0SZD3")
        )
        assert resp.conf_num == "24C0SZD3"

    def test_is_accepted_true(self):
        resp = CancelReplacePlaceResponse.from_api_response(
            _make_place_response()
        )
        assert resp.is_accepted is True

    def test_is_accepted_false_when_not_a(self):
        raw = {
            "cancelandreplace": {
                "orderConfirmDetail": {"respTypeCode": "V"},
            }
        }
        resp = CancelReplacePlaceResponse.from_api_response(raw)
        assert resp.is_accepted is False

    def test_is_error_on_place(self):
        raw = {
            "cancelandreplace": {
                "orderConfirmDetail": {"respTypeCode": "E"},
            }
        }
        resp = CancelReplacePlaceResponse.from_api_response(raw)
        assert resp.is_error is True
        assert resp.is_accepted is False

    def test_conf_num_none_on_empty(self):
        resp = CancelReplacePlaceResponse.from_api_response({})
        assert resp.conf_num is None
        assert resp.is_accepted is False

    def test_net_amount(self):
        resp = CancelReplacePlaceResponse.from_api_response(
            _make_place_response()
        )
        assert resp.order_confirm_detail.net_amount == pytest.approx(5)

    def test_error_messages_empty_on_accepted(self):
        resp = CancelReplacePlaceResponse.from_api_response(
            _make_place_response()
        )
        assert resp.error_messages == []


# ---------------------------------------------------------------------------
# CancelReplaceAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestCancelReplaceAPIPreview:
    @respx.mock
    def test_preview_posts_to_correct_url(self):
        route = respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_preview_response())
        )
        api = CancelReplaceAPI(httpx.Client())
        result = api.preview_order(_make_cr_request())

        assert route.called
        assert isinstance(result, CancelReplacePreviewResponse)

    @respx.mock
    def test_preview_request_body_matches_capture(self):
        route = respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_preview_response())
        )
        api = CancelReplaceAPI(httpx.Client())
        api.preview_order(_make_cr_request())

        sent = json.loads(route.calls[0].request.content)
        params = sent["request"]["parameter"]
        base = params["baseOrderDetail"]
        tradable = params["tradableSecOrderDetail"]

        assert base["orderActionCode"] == "B"
        assert base["acctTypeCode"] == "M"
        assert base["qty"] == 1
        assert base["qtyTypeCode"] == "S"
        assert base["securityDetail"]["symbol"] == "QS"
        assert base["securityDetail"]["cusip"] == "74767V109"
        assert "confNum" not in base

        assert tradable["tifCode"] == "D"
        assert tradable["priceTypeDetail"]["priceTypeCode"] == "L"
        assert tradable["priceTypeDetail"]["limitPrice"] == pytest.approx(5.0)
        assert tradable["mktRouteCode"] == ""

        assert params["orderNumOrig"] == "24C0ZBR7"
        assert params["acctNum"] == "Z21772945"
        assert "previewInd" not in params

    @respx.mock
    def test_preview_returns_validated_response(self):
        respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_preview_response())
        )
        api = CancelReplaceAPI(httpx.Client())
        result = api.preview_order(_make_cr_request())

        assert result.is_validated
        assert result.conf_num == "24C0SZD3"

    @respx.mock
    def test_preview_raises_on_http_error(self):
        respx.post(_PREVIEW_URL).mock(return_value=httpx.Response(401))
        api = CancelReplaceAPI(httpx.Client())
        with pytest.raises(httpx.HTTPStatusError):
            api.preview_order(_make_cr_request())

    @respx.mock
    def test_preview_error_response_parsed(self):
        respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_error_preview_response())
        )
        api = CancelReplaceAPI(httpx.Client())
        result = api.preview_order(_make_cr_request())

        assert result.is_error is True
        assert result.is_validated is False
        assert len(result.error_messages) == 1
        assert result.error_messages[0].code == "2999"


class TestCancelReplaceAPIPlace:
    @respx.mock
    def test_place_posts_to_correct_url(self):
        route = respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_place_response())
        )
        api = CancelReplaceAPI(httpx.Client(), live_trading=True)
        result = api.place_order(_make_cr_request(), conf_num="24C0SZD3")

        assert route.called
        assert isinstance(result, CancelReplacePlaceResponse)

    @respx.mock
    def test_place_request_body_matches_capture(self):
        route = respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_place_response())
        )
        api = CancelReplaceAPI(httpx.Client(), live_trading=True)
        api.place_order(_make_cr_request(), conf_num="24C0SZD3")

        sent = json.loads(route.calls[0].request.content)
        params = sent["request"]["parameter"]
        base = params["baseOrderDetail"]

        assert base["confNum"] == "24C0SZD3"
        assert base["orderActionCode"] == "B"
        assert base["securityDetail"]["symbol"] == "QS"
        assert base["securityDetail"]["cusip"] == "74767V109"
        assert params["previewInd"] is True
        assert params["confInd"] is True
        assert params["orderNumOrig"] == "24C0ZBR7"
        assert params["acctNum"] == "Z21772945"

    @respx.mock
    def test_place_returns_accepted_response(self):
        respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_place_response())
        )
        api = CancelReplaceAPI(httpx.Client(), live_trading=True)
        result = api.place_order(_make_cr_request(), conf_num="24C0SZD3")

        assert result.is_accepted
        assert result.conf_num == "24C0SZD3"

    @respx.mock
    def test_place_raises_on_http_error(self):
        respx.post(_PLACE_URL).mock(return_value=httpx.Response(500))
        api = CancelReplaceAPI(httpx.Client(), live_trading=True)
        with pytest.raises(httpx.HTTPStatusError):
            api.place_order(_make_cr_request(), conf_num="24C0SZD3")


class TestCancelReplaceAPIEndToEnd:
    @respx.mock
    def test_full_preview_then_place_workflow(self):
        """Verify the conf_num flows from preview into the place request body."""
        preview_route = respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(
                200, json=_make_preview_response("24C0SZD3")
            )
        )
        place_route = respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(
                200, json=_make_place_response("24C0SZD3")
            )
        )

        api = CancelReplaceAPI(httpx.Client(), live_trading=True)
        order = _make_cr_request()

        preview = api.preview_order(order)
        assert preview.is_validated
        conf_num = preview.conf_num
        assert conf_num == "24C0SZD3"

        place = api.place_order(order, conf_num=conf_num)
        assert place.is_accepted
        assert place.conf_num == "24C0SZD3"

        # Verify place request actually used the conf_num
        place_body = json.loads(place_route.calls[0].request.content)
        assert (
            place_body["request"]["parameter"]["baseOrderDetail"]["confNum"]
            == "24C0SZD3"
        )
        assert place_body["request"]["parameter"]["orderNumOrig"] == "24C0ZBR7"

    @respx.mock
    def test_preview_error_then_no_place(self):
        """When preview returns an error, the caller should not proceed to place."""
        respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(
                200, json=_make_error_preview_response()
            )
        )

        api = CancelReplaceAPI(httpx.Client())
        order = _make_cr_request()

        preview = api.preview_order(order)
        assert preview.is_error
        assert not preview.is_validated
        assert len(preview.error_messages) == 1
        assert "MA5010" in preview.error_messages[0].detail
