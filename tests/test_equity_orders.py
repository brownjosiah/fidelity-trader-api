"""Tests for the equity order preview/place API models and EquityOrderAPI client."""
from __future__ import annotations

import json
import pytest
import httpx
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.equity_order import (
    EquityOrderRequest,
    EquityPreviewResponse,
    EquityPlaceResponse,
    EquityOrderConfirmDetail,
    EquityRespPriceDetail,
    EquityEstCommissionDetail,
    EquityRespOrderDetail,
    EquityRespBaseOrderDetail,
    EquityRespSecurityDetail,
    EquityRespTradableSecOrderDetail,
    EquityRespPriceTypeDetail,
)
from fidelity_trader.orders.equity import EquityOrderAPI

_PREVIEW_URL = f"{DPSERVICE_URL}/ftgw/dp/orderentry/equity/preview/v1"
_PLACE_URL = f"{DPSERVICE_URL}/ftgw/dp/orderentry/equity/place/v1"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_order_request(
    acct_num: str = "Z21772945",
    symbol: str = "LGVN",
    order_action_code: str = "B",
    acct_type_code: str = "M",
    qty: float = 1,
    qty_type_code: str = "S",
    tif_code: str = "D",
    price_type_code: str = "L",
    limit_price: float = 1.0,
    mkt_route_code: str = "",
) -> EquityOrderRequest:
    return EquityOrderRequest(
        acctNum=acct_num,
        symbol=symbol,
        orderActionCode=order_action_code,
        acctTypeCode=acct_type_code,
        qty=qty,
        qtyTypeCode=qty_type_code,
        tifCode=tif_code,
        priceTypeCode=price_type_code,
        limitPrice=limit_price,
        mktRouteCode=mkt_route_code,
    )


def _make_confirm_detail(resp_type_code: str = "V", conf_num: str = "24A0L75J") -> dict:
    return {
        "respTypeCode": resp_type_code,
        "confNum": conf_num,
        "acctNum": "Z21772945",
        "acctTypeCode": "M",
        "priceDetail": {
            "price": 0.965,
            "priceDateTime": 1774969802,
            "bidPrice": 0.954,
            "askPrice": 0.97,
        },
        "estCommissionDetail": {
            "estCommission": 0.00,
            "typeCode": "30",
        },
        "dtcEstFee": 0,
        "netAmount": 1,
        "netProceedsInclusive": 1,
        "orderDetail": {
            "acctNum": "Z21772945",
            "baseOrderDetail": {
                "orderActionCode": "B",
                "actionCodeDesc": "Buy",
                "qty": 1,
                "qtyTypeCode": "S",
                "valOfOrder": 1,
                "securityDetail": {
                    "symbol": "LGVN",
                    "cusip": "54303L203",
                    "secDesc": "LONGEVERON CLASS A",
                },
            },
            "tradableSecOrderDetail": {
                "priceTypeDetail": {
                    "priceTypeCode": "L",
                    "priceTypeDesc": "Limit",
                    "limitPrice": 1,
                },
                "tifCode": "D",
                "mktRouteCode": "",
            },
        },
    }


def _make_preview_response(conf_num: str = "24A0L75J") -> dict:
    return {
        "preview": {
            "acctNum": "Z21772945",
            "orderConfirmDetail": _make_confirm_detail(resp_type_code="V", conf_num=conf_num),
        }
    }


def _make_place_response(conf_num: str = "24A0L75J") -> dict:
    detail = _make_confirm_detail(resp_type_code="A", conf_num=conf_num)
    # The place response omits a few fields present in preview
    detail.pop("dtcEstFee", None)
    detail.pop("netProceedsInclusive", None)
    detail["estCommissionDetail"] = {"estCommission": 0.00}
    detail["orderDetail"]["baseOrderDetail"].pop("qtyTypeCode", None)
    detail["orderDetail"]["baseOrderDetail"].pop("valOfOrder", None)
    detail["orderDetail"]["tradableSecOrderDetail"].pop("mktRouteCode", None)
    return {
        "place": {
            "acctNum": "Z21772945",
            "orderConfirmDetail": detail,
        }
    }


# ---------------------------------------------------------------------------
# EquityOrderRequest — body construction
# ---------------------------------------------------------------------------

class TestEquityOrderRequest:
    def test_to_preview_body_shape(self):
        order = _make_order_request()
        body = order.to_preview_body()

        params = body["request"]["parameter"]
        base = params["baseOrderDetail"]
        tradable = params["tradableSecOrderDetail"]

        assert base["orderActionCode"] == "B"
        assert base["acctTypeCode"] == "M"
        assert base["qty"] == 1
        assert base["qtyTypeCode"] == "S"
        assert base["securityDetail"]["symbol"] == "LGVN"
        assert "confNum" not in base

        assert tradable["tifCode"] == "D"
        assert tradable["priceTypeDetail"]["priceTypeCode"] == "L"
        assert tradable["priceTypeDetail"]["limitPrice"] == pytest.approx(1.0)
        assert tradable["mktRouteCode"] == ""

        assert params["priceDetail"] == {}
        assert params["acctNum"] == "Z21772945"
        assert "previewInd" not in params
        assert "confInd" not in params

    def test_to_place_body_injects_conf_num(self):
        order = _make_order_request()
        body = order.to_place_body("24A0L75J")

        params = body["request"]["parameter"]
        base = params["baseOrderDetail"]

        assert base["confNum"] == "24A0L75J"
        assert params["previewInd"] is True
        assert params["confInd"] is True

    def test_market_order_omits_limit_price(self):
        order = EquityOrderRequest(
            acctNum="Z21772945",
            symbol="AAPL",
            orderActionCode="B",
            qty=10,
            priceTypeCode="M",
        )
        body = order.to_preview_body()
        ptd = body["request"]["parameter"]["tradableSecOrderDetail"]["priceTypeDetail"]
        assert ptd["priceTypeCode"] == "M"
        assert "limitPrice" not in ptd

    def test_sell_order(self):
        order = _make_order_request(order_action_code="S", qty=5, symbol="TSLA")
        body = order.to_preview_body()
        base = body["request"]["parameter"]["baseOrderDetail"]
        assert base["orderActionCode"] == "S"
        assert base["qty"] == 5
        assert base["securityDetail"]["symbol"] == "TSLA"

    def test_gtc_tif_code(self):
        order = _make_order_request(tif_code="G")
        body = order.to_preview_body()
        tradable = body["request"]["parameter"]["tradableSecOrderDetail"]
        assert tradable["tifCode"] == "G"

    def test_cash_account_type(self):
        order = _make_order_request(acct_type_code="C")
        body = order.to_preview_body()
        base = body["request"]["parameter"]["baseOrderDetail"]
        assert base["acctTypeCode"] == "C"

    def test_defaults(self):
        order = EquityOrderRequest(
            acctNum="Z99999999",
            symbol="MSFT",
            orderActionCode="B",
            qty=3,
        )
        assert order.acct_type_code == "M"
        assert order.qty_type_code == "S"
        assert order.tif_code == "D"
        assert order.price_type_code == "L"
        assert order.mkt_route_code == ""


# ---------------------------------------------------------------------------
# EquityOrderConfirmDetail
# ---------------------------------------------------------------------------

class TestEquityOrderConfirmDetail:
    def test_parses_preview_confirm_detail(self):
        detail = EquityOrderConfirmDetail.model_validate(_make_confirm_detail("V"))
        assert detail.resp_type_code == "V"
        assert detail.conf_num == "24A0L75J"
        assert detail.acct_num == "Z21772945"
        assert detail.acct_type_code == "M"
        assert detail.net_amount == pytest.approx(1)
        assert detail.dtc_est_fee == pytest.approx(0)
        assert detail.net_proceeds_inclusive == pytest.approx(1)

    def test_parses_price_detail(self):
        detail = EquityOrderConfirmDetail.model_validate(_make_confirm_detail("V"))
        pd = detail.price_detail
        assert pd is not None
        assert pd.price == pytest.approx(0.965)
        assert pd.bid_price == pytest.approx(0.954)
        assert pd.ask_price == pytest.approx(0.97)
        assert pd.price_date_time == 1774969802

    def test_parses_commission_detail(self):
        detail = EquityOrderConfirmDetail.model_validate(_make_confirm_detail("V"))
        ec = detail.est_commission_detail
        assert ec is not None
        assert ec.est_commission == pytest.approx(0.0)
        assert ec.type_code == "30"

    def test_parses_nested_order_detail(self):
        detail = EquityOrderConfirmDetail.model_validate(_make_confirm_detail("V"))
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
        assert sec.symbol == "LGVN"
        assert sec.cusip == "54303L203"
        assert sec.sec_desc == "LONGEVERON CLASS A"

    def test_parses_tradable_sec_order_detail(self):
        detail = EquityOrderConfirmDetail.model_validate(_make_confirm_detail("V"))
        tsd = detail.order_detail.tradable_sec_order_detail
        assert tsd is not None
        assert tsd.tif_code == "D"
        ptd = tsd.price_type_detail
        assert ptd is not None
        assert ptd.price_type_code == "L"
        assert ptd.price_type_desc == "Limit"
        assert ptd.limit_price == pytest.approx(1.0)

    def test_optional_fields_default_none(self):
        detail = EquityOrderConfirmDetail.model_validate({})
        assert detail.resp_type_code is None
        assert detail.conf_num is None
        assert detail.price_detail is None
        assert detail.order_detail is None


# ---------------------------------------------------------------------------
# EquityPreviewResponse
# ---------------------------------------------------------------------------

class TestEquityPreviewResponse:
    def test_from_api_response_parsed(self):
        resp = EquityPreviewResponse.from_api_response(_make_preview_response())
        assert resp.acct_num == "Z21772945"
        assert resp.order_confirm_detail is not None
        assert resp.order_confirm_detail.resp_type_code == "V"

    def test_conf_num_property(self):
        resp = EquityPreviewResponse.from_api_response(_make_preview_response("24A0L75J"))
        assert resp.conf_num == "24A0L75J"

    def test_is_validated_true(self):
        resp = EquityPreviewResponse.from_api_response(_make_preview_response())
        assert resp.is_validated is True

    def test_is_validated_false_when_not_v(self):
        raw = {"preview": _make_confirm_detail(resp_type_code="E")}
        resp = EquityPreviewResponse.from_api_response(raw)
        assert resp.is_validated is False

    def test_conf_num_none_on_empty(self):
        resp = EquityPreviewResponse.from_api_response({})
        assert resp.conf_num is None
        assert resp.is_validated is False

    def test_security_detail_accessible(self):
        resp = EquityPreviewResponse.from_api_response(_make_preview_response())
        sec = resp.order_confirm_detail.order_detail.base_order_detail.security_detail
        assert sec.symbol == "LGVN"


# ---------------------------------------------------------------------------
# EquityPlaceResponse
# ---------------------------------------------------------------------------

class TestEquityPlaceResponse:
    def test_from_api_response_parsed(self):
        resp = EquityPlaceResponse.from_api_response(_make_place_response())
        assert resp.acct_num == "Z21772945"
        assert resp.order_confirm_detail is not None
        assert resp.order_confirm_detail.resp_type_code == "A"

    def test_conf_num_property(self):
        resp = EquityPlaceResponse.from_api_response(_make_place_response("24A0L75J"))
        assert resp.conf_num == "24A0L75J"

    def test_is_accepted_true(self):
        resp = EquityPlaceResponse.from_api_response(_make_place_response())
        assert resp.is_accepted is True

    def test_is_accepted_false_when_not_a(self):
        raw = {"place": _make_confirm_detail(resp_type_code="V")}
        resp = EquityPlaceResponse.from_api_response(raw)
        assert resp.is_accepted is False

    def test_conf_num_none_on_empty(self):
        resp = EquityPlaceResponse.from_api_response({})
        assert resp.conf_num is None
        assert resp.is_accepted is False

    def test_net_amount(self):
        resp = EquityPlaceResponse.from_api_response(_make_place_response())
        assert resp.order_confirm_detail.net_amount == pytest.approx(1)


# ---------------------------------------------------------------------------
# EquityOrderAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestEquityOrderAPIPreview:
    @respx.mock
    def test_preview_posts_to_correct_url(self):
        route = respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_preview_response())
        )
        api = EquityOrderAPI(httpx.Client())
        result = api.preview_order(_make_order_request())

        assert route.called
        assert isinstance(result, EquityPreviewResponse)

    @respx.mock
    def test_preview_request_body_matches_capture(self):
        route = respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_preview_response())
        )
        api = EquityOrderAPI(httpx.Client())
        api.preview_order(_make_order_request())

        sent = json.loads(route.calls[0].request.content)
        params = sent["request"]["parameter"]
        base = params["baseOrderDetail"]
        tradable = params["tradableSecOrderDetail"]

        assert base["orderActionCode"] == "B"
        assert base["acctTypeCode"] == "M"
        assert base["qty"] == 1
        assert base["qtyTypeCode"] == "S"
        assert base["securityDetail"]["symbol"] == "LGVN"
        assert "confNum" not in base

        assert tradable["tifCode"] == "D"
        assert tradable["priceTypeDetail"]["priceTypeCode"] == "L"
        assert tradable["priceTypeDetail"]["limitPrice"] == pytest.approx(1.0)
        assert tradable["mktRouteCode"] == ""

        assert params["priceDetail"] == {}
        assert params["acctNum"] == "Z21772945"
        assert "previewInd" not in params

    @respx.mock
    def test_preview_returns_validated_response(self):
        respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_preview_response())
        )
        api = EquityOrderAPI(httpx.Client())
        result = api.preview_order(_make_order_request())

        assert result.is_validated
        assert result.conf_num == "24A0L75J"

    @respx.mock
    def test_preview_raises_on_http_error(self):
        respx.post(_PREVIEW_URL).mock(return_value=httpx.Response(401))
        api = EquityOrderAPI(httpx.Client())
        with pytest.raises(httpx.HTTPStatusError):
            api.preview_order(_make_order_request())


class TestEquityOrderAPIPlace:
    @respx.mock
    def test_place_posts_to_correct_url(self):
        route = respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_place_response())
        )
        api = EquityOrderAPI(httpx.Client())
        result = api.place_order(_make_order_request(), conf_num="24A0L75J")

        assert route.called
        assert isinstance(result, EquityPlaceResponse)

    @respx.mock
    def test_place_request_body_matches_capture(self):
        route = respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_place_response())
        )
        api = EquityOrderAPI(httpx.Client())
        api.place_order(_make_order_request(), conf_num="24A0L75J")

        sent = json.loads(route.calls[0].request.content)
        params = sent["request"]["parameter"]
        base = params["baseOrderDetail"]

        assert base["confNum"] == "24A0L75J"
        assert params["previewInd"] is True
        assert params["confInd"] is True
        assert params["acctNum"] == "Z21772945"
        assert base["orderActionCode"] == "B"
        assert base["securityDetail"]["symbol"] == "LGVN"

    @respx.mock
    def test_place_returns_accepted_response(self):
        respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_place_response())
        )
        api = EquityOrderAPI(httpx.Client())
        result = api.place_order(_make_order_request(), conf_num="24A0L75J")

        assert result.is_accepted
        assert result.conf_num == "24A0L75J"

    @respx.mock
    def test_place_raises_on_http_error(self):
        respx.post(_PLACE_URL).mock(return_value=httpx.Response(500))
        api = EquityOrderAPI(httpx.Client())
        with pytest.raises(httpx.HTTPStatusError):
            api.place_order(_make_order_request(), conf_num="24A0L75J")


class TestEquityOrderAPIEndToEnd:
    @respx.mock
    def test_full_preview_then_place_workflow(self):
        """Verify the conf_num flows from preview into the place request body."""
        preview_route = respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_preview_response("24A0L75J"))
        )
        place_route = respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_place_response("24A0L75J"))
        )

        api = EquityOrderAPI(httpx.Client())
        order = _make_order_request()

        preview = api.preview_order(order)
        assert preview.is_validated
        conf_num = preview.conf_num
        assert conf_num == "24A0L75J"

        place = api.place_order(order, conf_num=conf_num)
        assert place.is_accepted
        assert place.conf_num == "24A0L75J"

        # Verify place request actually used the conf_num
        place_body = json.loads(place_route.calls[0].request.content)
        assert place_body["request"]["parameter"]["baseOrderDetail"]["confNum"] == "24A0L75J"
