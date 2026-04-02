"""Tests for the single-leg option order preview/place API models and SingleOptionOrderAPI client."""
from __future__ import annotations

import json
import pytest
import httpx
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.single_option_order import (
    SingleOptionOrderRequest,
    SingleOptionPreviewResponse,
    SingleOptionPlaceResponse,
    SingleOptionOrderConfirmDetail,
    SingleOptionRespPriceDetail,
    SingleOptionEstCommissionDetail,
    SingleOptionRespOrderDetail,
    SingleOptionRespBaseOrderDetail,
    SingleOptionRespSecurityDetail,
    SingleOptionRespTradableSecOrderDetail,
    SingleOptionRespPriceTypeDetail,
    SingleOptionRespOptionDetail,
    SingleOptionRespSpecificShrDetail,
)
from fidelity_trader.orders.single_option import SingleOptionOrderAPI

_PREVIEW_URL = f"{DPSERVICE_URL}/ftgw/dp/orderentry/option/preview/v2"
_PLACE_URL = f"{DPSERVICE_URL}/ftgw/dp/orderentry/option/place/v2"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_order_request(
    acct_num: str = "Z21772945",
    symbol: str = "QS270115C7",
    order_action_code: str = "BC",
    acct_type_code: str = "M",
    qty: int = 1,
    qty_type_code: str = "S",
    tif_code: str = "D",
    price_type_code: str = "M",
    limit_price: float | None = None,
    mkt_route_code: str = "",
    destination_code: str = "",
) -> SingleOptionOrderRequest:
    return SingleOptionOrderRequest(
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
        destinationCode=destination_code,
    )


def _make_confirm_detail(
    resp_type_code: str = "V",
    conf_num: str = "D02PXWRR",
    order_action_code: str = "BC",
    action_code_desc: str = "Buy Call",
) -> dict:
    return {
        "respTypeCode": resp_type_code,
        "confNum": conf_num,
        "acctNum": "Z21772945",
        "acctTypeCode": "M",
        "priceDetail": {
            "price": 1.51,
            "priceDateTime": 1775147597,
            "bidPrice": 1.5,
            "askPrice": 1.54,
        },
        "estCommissionDetail": {
            "estCommission": 0.65,
            "typeCode": "3",
        },
        "netAmount": 154.65,
        "netProceedsInclusive": 154.65,
        "orderDetail": {
            "acctNum": "Z21772945",
            "baseOrderDetail": {
                "orderActionCode": order_action_code,
                "actionCodeDesc": action_code_desc,
                "qty": 1,
                "qtyTypeCode": "S",
                "valOfOrder": 154.0,
                "securityDetail": {
                    "symbol": "QS270115C7",
                    "cusip": "7421019HF",
                    "secDesc": "QS JAN 15 2027 $7 CALL",
                },
                "specificShrDetail": {"taxLotDetails": []},
            },
            "tradableSecOrderDetail": {
                "priceTypeDetail": {
                    "priceTypeCode": "M",
                    "priceTypeDesc": "Market",
                },
                "optionDetail": {"type": "O"},
                "tifCode": "D",
                "mktRouteCode": "",
                "destinationCode": "",
            },
        },
    }


def _make_preview_response(conf_num: str = "D02PXWRR") -> dict:
    return {
        "preview": {
            "acctNum": "Z21772945",
            "orderConfirmDetail": _make_confirm_detail(
                resp_type_code="V", conf_num=conf_num
            ),
        }
    }


def _make_place_response(conf_num: str = "D02PXWRR") -> dict:
    return {
        "place": {
            "acctNum": "Z21772945",
            "orderConfirmDetail": _make_confirm_detail(
                resp_type_code="A", conf_num=conf_num
            ),
        }
    }


# ---------------------------------------------------------------------------
# SingleOptionOrderRequest -- body construction
# ---------------------------------------------------------------------------

class TestSingleOptionOrderRequest:
    def test_to_preview_body_shape(self):
        order = _make_order_request()
        body = order.to_preview_body()

        params = body["request"]["parameter"]
        base = params["baseOrderDetail"]
        tradable = params["tradableSecOrderDetail"]

        assert base["orderActionCode"] == "BC"
        assert base["acctTypeCode"] == "M"
        assert base["qty"] == 1
        assert base["qtyTypeCode"] == "S"
        assert base["securityDetail"]["symbol"] == "QS270115C7"
        assert base["specificShrDetail"] == {}
        assert "confNum" not in base

        assert tradable["tifCode"] == "D"
        assert tradable["priceTypeDetail"]["priceTypeCode"] == "M"
        assert tradable["mktRouteCode"] == ""
        assert tradable["destinationCode"] == ""
        assert tradable["optionDetail"]["type"] == "O"

        assert params["priceDetail"] == {}
        assert params["acctNum"] == "Z21772945"
        assert "previewInd" not in params
        assert "confInd" not in params

    def test_to_place_body_injects_conf_num(self):
        order = _make_order_request()
        body = order.to_place_body("D02PXWRR")

        params = body["request"]["parameter"]
        base = params["baseOrderDetail"]

        assert base["confNum"] == "D02PXWRR"
        assert params["previewInd"] is False
        assert params["confInd"] is False

    def test_place_body_has_option_detail(self):
        order = _make_order_request()
        body = order.to_place_body("D02PXWRR")

        tradable = body["request"]["parameter"]["tradableSecOrderDetail"]
        assert tradable["optionDetail"]["type"] == "O"

    def test_place_body_has_specific_shr_detail(self):
        order = _make_order_request()
        body = order.to_place_body("D02PXWRR")

        base = body["request"]["parameter"]["baseOrderDetail"]
        assert base["specificShrDetail"] == {}

    def test_place_body_key_ordering(self):
        """Verify the place body has tradableSecOrderDetail before baseOrderDetail
        (matching the captured traffic key order)."""
        order = _make_order_request()
        body = order.to_place_body("D02PXWRR")

        param_keys = list(body["request"]["parameter"].keys())
        assert param_keys.index("tradableSecOrderDetail") < param_keys.index("baseOrderDetail")

    def test_market_order_omits_limit_price(self):
        order = _make_order_request(price_type_code="M")
        body = order.to_preview_body()
        ptd = body["request"]["parameter"]["tradableSecOrderDetail"]["priceTypeDetail"]
        assert ptd["priceTypeCode"] == "M"
        assert "limitPrice" not in ptd

    def test_limit_order_includes_limit_price(self):
        order = _make_order_request(price_type_code="L", limit_price=5.50)
        body = order.to_preview_body()
        ptd = body["request"]["parameter"]["tradableSecOrderDetail"]["priceTypeDetail"]
        assert ptd["priceTypeCode"] == "L"
        assert ptd["limitPrice"] == pytest.approx(5.50)

    def test_limit_price_in_place_body(self):
        order = _make_order_request(price_type_code="L", limit_price=3.25)
        body = order.to_place_body("CONF123")
        ptd = body["request"]["parameter"]["tradableSecOrderDetail"]["priceTypeDetail"]
        assert ptd["limitPrice"] == pytest.approx(3.25)

    def test_buy_call_action_code(self):
        order = _make_order_request(order_action_code="BC")
        body = order.to_preview_body()
        assert body["request"]["parameter"]["baseOrderDetail"]["orderActionCode"] == "BC"

    def test_buy_put_action_code(self):
        order = _make_order_request(order_action_code="BP")
        body = order.to_preview_body()
        assert body["request"]["parameter"]["baseOrderDetail"]["orderActionCode"] == "BP"

    def test_sell_call_action_code(self):
        order = _make_order_request(order_action_code="SC")
        body = order.to_preview_body()
        assert body["request"]["parameter"]["baseOrderDetail"]["orderActionCode"] == "SC"

    def test_sell_put_action_code(self):
        order = _make_order_request(order_action_code="SP")
        body = order.to_preview_body()
        assert body["request"]["parameter"]["baseOrderDetail"]["orderActionCode"] == "SP"

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

    def test_multiple_contracts(self):
        order = _make_order_request(qty=10)
        body = order.to_preview_body()
        assert body["request"]["parameter"]["baseOrderDetail"]["qty"] == 10

    def test_defaults(self):
        order = SingleOptionOrderRequest(
            acctNum="Z99999999",
            symbol="AAPL250620C200",
            orderActionCode="BC",
            qty=1,
        )
        assert order.acct_type_code == "M"
        assert order.qty_type_code == "S"
        assert order.tif_code == "D"
        assert order.price_type_code == "M"
        assert order.mkt_route_code == ""
        assert order.destination_code == ""
        assert order.limit_price is None

    def test_preview_body_matches_captured_traffic(self):
        """Verify the full preview body matches the exact captured traffic shape."""
        order = _make_order_request()
        body = order.to_preview_body()

        expected = {
            "request": {
                "parameter": {
                    "baseOrderDetail": {
                        "orderActionCode": "BC",
                        "acctTypeCode": "M",
                        "qty": 1,
                        "qtyTypeCode": "S",
                        "securityDetail": {"symbol": "QS270115C7"},
                        "specificShrDetail": {},
                    },
                    "tradableSecOrderDetail": {
                        "tifCode": "D",
                        "priceTypeDetail": {"priceTypeCode": "M"},
                        "mktRouteCode": "",
                        "destinationCode": "",
                        "optionDetail": {"type": "O"},
                    },
                    "priceDetail": {},
                    "acctNum": "Z21772945",
                }
            }
        }
        assert body == expected


# ---------------------------------------------------------------------------
# SingleOptionOrderConfirmDetail
# ---------------------------------------------------------------------------

class TestSingleOptionOrderConfirmDetail:
    def test_parses_preview_confirm_detail(self):
        detail = SingleOptionOrderConfirmDetail.model_validate(
            _make_confirm_detail("V")
        )
        assert detail.resp_type_code == "V"
        assert detail.conf_num == "D02PXWRR"
        assert detail.acct_num == "Z21772945"
        assert detail.acct_type_code == "M"
        assert detail.net_amount == pytest.approx(154.65)
        assert detail.net_proceeds_inclusive == pytest.approx(154.65)

    def test_parses_price_detail(self):
        detail = SingleOptionOrderConfirmDetail.model_validate(
            _make_confirm_detail("V")
        )
        pd = detail.price_detail
        assert pd is not None
        assert pd.price == pytest.approx(1.51)
        assert pd.bid_price == pytest.approx(1.5)
        assert pd.ask_price == pytest.approx(1.54)
        assert pd.price_date_time == 1775147597

    def test_parses_commission_detail(self):
        detail = SingleOptionOrderConfirmDetail.model_validate(
            _make_confirm_detail("V")
        )
        ec = detail.est_commission_detail
        assert ec is not None
        assert ec.est_commission == pytest.approx(0.65)
        assert ec.type_code == "3"

    def test_parses_nested_order_detail(self):
        detail = SingleOptionOrderConfirmDetail.model_validate(
            _make_confirm_detail("V")
        )
        od = detail.order_detail
        assert od is not None
        assert od.acct_num == "Z21772945"
        base = od.base_order_detail
        assert base is not None
        assert base.order_action_code == "BC"
        assert base.action_code_desc == "Buy Call"
        assert base.qty == 1
        assert base.val_of_order == pytest.approx(154.0)
        sec = base.security_detail
        assert sec is not None
        assert sec.symbol == "QS270115C7"
        assert sec.cusip == "7421019HF"
        assert sec.sec_desc == "QS JAN 15 2027 $7 CALL"

    def test_parses_specific_shr_detail(self):
        detail = SingleOptionOrderConfirmDetail.model_validate(
            _make_confirm_detail("V")
        )
        ssd = detail.order_detail.base_order_detail.specific_shr_detail
        assert ssd is not None
        assert ssd.tax_lot_details == []

    def test_parses_tradable_sec_order_detail(self):
        detail = SingleOptionOrderConfirmDetail.model_validate(
            _make_confirm_detail("V")
        )
        tsd = detail.order_detail.tradable_sec_order_detail
        assert tsd is not None
        assert tsd.tif_code == "D"
        assert tsd.mkt_route_code == ""
        assert tsd.destination_code == ""
        ptd = tsd.price_type_detail
        assert ptd is not None
        assert ptd.price_type_code == "M"
        assert ptd.price_type_desc == "Market"

    def test_parses_option_detail_in_response(self):
        detail = SingleOptionOrderConfirmDetail.model_validate(
            _make_confirm_detail("V")
        )
        od = detail.order_detail.tradable_sec_order_detail.option_detail
        assert od is not None
        assert od.type == "O"

    def test_optional_fields_default_none(self):
        detail = SingleOptionOrderConfirmDetail.model_validate({})
        assert detail.resp_type_code is None
        assert detail.conf_num is None
        assert detail.price_detail is None
        assert detail.order_detail is None
        assert detail.est_commission_detail is None
        assert detail.net_amount is None
        assert detail.net_proceeds_inclusive is None


# ---------------------------------------------------------------------------
# SingleOptionPreviewResponse
# ---------------------------------------------------------------------------

class TestSingleOptionPreviewResponse:
    def test_from_api_response_parsed(self):
        resp = SingleOptionPreviewResponse.from_api_response(
            _make_preview_response()
        )
        assert resp.acct_num == "Z21772945"
        assert resp.order_confirm_detail is not None
        assert resp.order_confirm_detail.resp_type_code == "V"

    def test_conf_num_property(self):
        resp = SingleOptionPreviewResponse.from_api_response(
            _make_preview_response("D02PXWRR")
        )
        assert resp.conf_num == "D02PXWRR"

    def test_is_validated_true(self):
        resp = SingleOptionPreviewResponse.from_api_response(
            _make_preview_response()
        )
        assert resp.is_validated is True

    def test_is_validated_false_when_not_v(self):
        raw = {
            "preview": {
                "acctNum": "Z21772945",
                "orderConfirmDetail": _make_confirm_detail(resp_type_code="E"),
            }
        }
        resp = SingleOptionPreviewResponse.from_api_response(raw)
        assert resp.is_validated is False

    def test_conf_num_none_on_empty(self):
        resp = SingleOptionPreviewResponse.from_api_response({})
        assert resp.conf_num is None
        assert resp.is_validated is False

    def test_security_detail_accessible(self):
        resp = SingleOptionPreviewResponse.from_api_response(
            _make_preview_response()
        )
        sec = resp.order_confirm_detail.order_detail.base_order_detail.security_detail
        assert sec.symbol == "QS270115C7"

    def test_option_detail_accessible(self):
        resp = SingleOptionPreviewResponse.from_api_response(
            _make_preview_response()
        )
        od = resp.order_confirm_detail.order_detail.tradable_sec_order_detail.option_detail
        assert od.type == "O"


# ---------------------------------------------------------------------------
# SingleOptionPlaceResponse
# ---------------------------------------------------------------------------

class TestSingleOptionPlaceResponse:
    def test_from_api_response_parsed(self):
        resp = SingleOptionPlaceResponse.from_api_response(_make_place_response())
        assert resp.acct_num == "Z21772945"
        assert resp.order_confirm_detail is not None
        assert resp.order_confirm_detail.resp_type_code == "A"

    def test_conf_num_property(self):
        resp = SingleOptionPlaceResponse.from_api_response(
            _make_place_response("D02PXWRR")
        )
        assert resp.conf_num == "D02PXWRR"

    def test_is_accepted_true(self):
        resp = SingleOptionPlaceResponse.from_api_response(_make_place_response())
        assert resp.is_accepted is True

    def test_is_accepted_false_when_not_a(self):
        raw = {
            "place": {
                "acctNum": "Z21772945",
                "orderConfirmDetail": _make_confirm_detail(resp_type_code="V"),
            }
        }
        resp = SingleOptionPlaceResponse.from_api_response(raw)
        assert resp.is_accepted is False

    def test_conf_num_none_on_empty(self):
        resp = SingleOptionPlaceResponse.from_api_response({})
        assert resp.conf_num is None
        assert resp.is_accepted is False

    def test_net_amount(self):
        resp = SingleOptionPlaceResponse.from_api_response(_make_place_response())
        assert resp.order_confirm_detail.net_amount == pytest.approx(154.65)


# ---------------------------------------------------------------------------
# SingleOptionOrderAPI -- HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestSingleOptionOrderAPIPreview:
    @respx.mock
    def test_preview_posts_to_correct_url(self):
        route = respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_preview_response())
        )
        api = SingleOptionOrderAPI(httpx.Client())
        result = api.preview_order(_make_order_request())

        assert route.called
        assert isinstance(result, SingleOptionPreviewResponse)

    @respx.mock
    def test_preview_request_body_matches_capture(self):
        route = respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_preview_response())
        )
        api = SingleOptionOrderAPI(httpx.Client())
        api.preview_order(_make_order_request())

        sent = json.loads(route.calls[0].request.content)
        params = sent["request"]["parameter"]
        base = params["baseOrderDetail"]
        tradable = params["tradableSecOrderDetail"]

        assert base["orderActionCode"] == "BC"
        assert base["acctTypeCode"] == "M"
        assert base["qty"] == 1
        assert base["qtyTypeCode"] == "S"
        assert base["securityDetail"]["symbol"] == "QS270115C7"
        assert base["specificShrDetail"] == {}
        assert "confNum" not in base

        assert tradable["tifCode"] == "D"
        assert tradable["priceTypeDetail"]["priceTypeCode"] == "M"
        assert tradable["mktRouteCode"] == ""
        assert tradable["destinationCode"] == ""
        assert tradable["optionDetail"]["type"] == "O"

        assert params["priceDetail"] == {}
        assert params["acctNum"] == "Z21772945"
        assert "previewInd" not in params

    @respx.mock
    def test_preview_returns_validated_response(self):
        respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_preview_response())
        )
        api = SingleOptionOrderAPI(httpx.Client())
        result = api.preview_order(_make_order_request())

        assert result.is_validated
        assert result.conf_num == "D02PXWRR"

    @respx.mock
    def test_preview_raises_on_http_error(self):
        respx.post(_PREVIEW_URL).mock(return_value=httpx.Response(401))
        api = SingleOptionOrderAPI(httpx.Client())
        with pytest.raises(httpx.HTTPStatusError):
            api.preview_order(_make_order_request())


class TestSingleOptionOrderAPIPlace:
    @respx.mock
    def test_place_posts_to_correct_url(self):
        route = respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_place_response())
        )
        api = SingleOptionOrderAPI(httpx.Client())
        result = api.place_order(_make_order_request(), conf_num="D02PXWRR")

        assert route.called
        assert isinstance(result, SingleOptionPlaceResponse)

    @respx.mock
    def test_place_request_body_matches_capture(self):
        route = respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_place_response())
        )
        api = SingleOptionOrderAPI(httpx.Client())
        api.place_order(_make_order_request(), conf_num="D02PXWRR")

        sent = json.loads(route.calls[0].request.content)
        params = sent["request"]["parameter"]
        base = params["baseOrderDetail"]
        tradable = params["tradableSecOrderDetail"]

        assert base["confNum"] == "D02PXWRR"
        assert base["orderActionCode"] == "BC"
        assert base["securityDetail"]["symbol"] == "QS270115C7"
        assert base["specificShrDetail"] == {}

        assert params["previewInd"] is False
        assert params["confInd"] is False
        assert params["acctNum"] == "Z21772945"

        assert tradable["optionDetail"]["type"] == "O"
        assert tradable["destinationCode"] == ""

    @respx.mock
    def test_place_returns_accepted_response(self):
        respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_place_response())
        )
        api = SingleOptionOrderAPI(httpx.Client())
        result = api.place_order(_make_order_request(), conf_num="D02PXWRR")

        assert result.is_accepted
        assert result.conf_num == "D02PXWRR"

    @respx.mock
    def test_place_raises_on_http_error(self):
        respx.post(_PLACE_URL).mock(return_value=httpx.Response(500))
        api = SingleOptionOrderAPI(httpx.Client())
        with pytest.raises(httpx.HTTPStatusError):
            api.place_order(_make_order_request(), conf_num="D02PXWRR")


class TestSingleOptionOrderAPIEndToEnd:
    @respx.mock
    def test_full_preview_then_place_workflow(self):
        """Verify the conf_num flows from preview into the place request body."""
        preview_route = respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(
                200, json=_make_preview_response("D02PXWRR")
            )
        )
        place_route = respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(
                200, json=_make_place_response("D02PXWRR")
            )
        )

        api = SingleOptionOrderAPI(httpx.Client())
        order = _make_order_request()

        preview = api.preview_order(order)
        assert preview.is_validated
        conf_num = preview.conf_num
        assert conf_num == "D02PXWRR"

        place = api.place_order(order, conf_num=conf_num)
        assert place.is_accepted
        assert place.conf_num == "D02PXWRR"

        # Verify place request actually used the conf_num
        place_body = json.loads(place_route.calls[0].request.content)
        assert (
            place_body["request"]["parameter"]["baseOrderDetail"]["confNum"]
            == "D02PXWRR"
        )
        # Verify place-specific flags
        assert place_body["request"]["parameter"]["previewInd"] is False
        assert place_body["request"]["parameter"]["confInd"] is False
