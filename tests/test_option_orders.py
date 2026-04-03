"""Tests for the multi-leg option order preview/place API models and client."""
from __future__ import annotations

import json
import pytest
import httpx
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.option_order import (
    MultiLegOptionOrderRequest,
    MultiLegOptionPreviewResponse,
    MultiLegOptionPlaceResponse,
    MultiLegOptionOrderConfirmDetail,
    OptionLeg,
    OptionLegSecurityDetail,
    OptionLegPriceDetail,
    OptionRespLeg,
    OptionRespComplexDetail,
    OptionSysMsg,
    OptionSysMsgs,
)
from fidelity_trader.orders.options import MultiLegOptionOrderAPI

_PREVIEW_URL = f"{DPSERVICE_URL}/ftgw/dp/orderentry/multilegoption/preview/v1"
_PLACE_URL = f"{DPSERVICE_URL}/ftgw/dp/orderentry/multilegoption/place/v1"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_leg(
    order_action_code: str = "BO",
    symbol: str = "QS280121C7",
    qty: int = 1,
    price: float = 6.18,
    price_date_time: int = 1774969854,
    bid_price: float = 2.5,
    ask_price: float = 2.59,
) -> OptionLeg:
    return OptionLeg(
        orderActionCode=order_action_code,
        qty=qty,
        securityDetail=OptionLegSecurityDetail(
            symbolCUSIPCode="S",
            symbol=symbol,
        ),
        priceDetail=OptionLegPriceDetail(
            price=price,
            priceDateTime=price_date_time,
            bidPrice=bid_price,
            askPrice=ask_price,
        ),
    )


def _make_order_request(
    acct_num: str = "Z21772945",
    net_amount: float = 0.92,
    tif_code: str = "D",
    db_cr_even_code: str = "DB",
    strategy_type: str = "CU",
) -> MultiLegOptionOrderRequest:
    return MultiLegOptionOrderRequest(
        acctNum=acct_num,
        netAmount=net_amount,
        tifCode=tif_code,
        dbCrEvenCode=db_cr_even_code,
        strategyType=strategy_type,
        legs=[
            _make_leg("BO", "QS280121C7", 1, 6.18, 1774969854, 2.5, 2.59),
            _make_leg("SO", "QS280121C12", 1, 6.18, 1774969854, 1.54, 1.7),
        ],
    )


def _make_confirm_detail(resp_type_code: str = "V", conf_num: str = "C31PHDRX") -> dict:
    return {
        "respTypeCode": resp_type_code,
        "confNum": conf_num,
        "acctTypeCode": "M",
        "netAmount": 0.92,
        "netAsk": 1.05,
        "netBid": 0.80,
        "midPoint": 0.925,
        "gcd": 1,
        "finalTotalValOfOrder": 92.0,
        "totalEstCommission": 0.0,
        "subtotalValOfOrder": 92.0,
        "orderDetail": {
            "baseOrderDetail": {
                "optionDetail": {
                    "complexType": "CO",
                    "numOfLegs": 2,
                    "complexOrderDetails": [
                        {
                            "orderActionCode": "BC",
                            "type": "O",
                            "qty": 1,
                            "securityDetail": {"symbol": "QS280121C7", "etfInd": False},
                            "estCommissionDetail": {"estCommission": 0.0},
                            "priceDetail": {
                                "price": 2.39,
                                "bidPrice": 2.5,
                                "askPrice": 2.59,
                            },
                        },
                        {
                            "orderActionCode": "SC",
                            "type": "O",
                            "qty": 1,
                            "securityDetail": {"symbol": "QS280121C12", "etfInd": False},
                            "estCommissionDetail": {"estCommission": 0.0},
                            "priceDetail": {
                                "price": 1.65,
                                "bidPrice": 1.54,
                                "askPrice": 1.7,
                            },
                        },
                    ],
                }
            },
            "tradableSecOrderDetail": {
                "tifCode": "D",
                "priceTypeDetail": {"priceTypeCode": "L"},
                "dbCrEvenCode": "DB",
                "aonCode": False,
                "destinationCode": "",
            },
        },
    }


def _make_sys_msgs() -> dict:
    return {
        "sysMsg": [
            {
                "message": "Other",
                "detail": "Code=354020, Text=(354020) If you plan to day-trade...",
                "source": "multilegorder",
                "code": "1999",
                "type": "warning",
            }
        ]
    }


def _make_preview_response(conf_num: str = "C31PHDRX") -> dict:
    return {
        "multiLegOptionResponse": {
            "sysMsgs": _make_sys_msgs(),
            "acctNum": "Z21772945",
            "orderConfirmDetail": _make_confirm_detail(
                resp_type_code="V", conf_num=conf_num
            ),
        }
    }


def _make_place_response(conf_num: str = "C31PHDRX") -> dict:
    return {
        "multiLegOptionResponse": {
            "sysMsgs": _make_sys_msgs(),
            "acctNum": "Z21772945",
            "orderConfirmDetail": _make_confirm_detail(
                resp_type_code="A", conf_num=conf_num
            ),
        }
    }


# ---------------------------------------------------------------------------
# OptionLeg / request serialisation
# ---------------------------------------------------------------------------

class TestOptionLeg:
    def test_to_api_dict_buy_to_open(self):
        leg = _make_leg("BO", "QS280121C7")
        d = leg.to_api_dict()
        assert d["orderActionCode"] == "BO"
        assert d["type"] == "O"
        assert d["qty"] == 1
        assert d["securityDetail"]["symbol"] == "QS280121C7"
        assert d["securityDetail"]["symbolCUSIPCode"] == "S"
        assert d["priceDetail"]["price"] == pytest.approx(6.18)
        assert d["priceDetail"]["bidPrice"] == pytest.approx(2.5)
        assert d["priceDetail"]["askPrice"] == pytest.approx(2.59)

    def test_to_api_dict_sell_to_open(self):
        leg = _make_leg("SO", "QS280121C12", bid_price=1.54, ask_price=1.7)
        d = leg.to_api_dict()
        assert d["orderActionCode"] == "SO"
        assert d["securityDetail"]["symbol"] == "QS280121C12"


class TestMultiLegOptionOrderRequest:
    def test_to_preview_body_shape(self):
        order = _make_order_request()
        body = order.to_preview_body()

        params = body["parameters"]
        tsd = params["tradableSecOrderDetail"]
        base = params["baseOrderDetail"]
        opt = base["optionDetail"]

        assert params["acctNum"] == "Z21772945"
        assert params["expDateDefaultInd"] is True
        assert params["expTimeDefaultInd"] is True

        assert tsd["tifCode"] == "D"
        assert tsd["dbCrEvenCode"] == "DB"
        assert tsd["netAmount"] == pytest.approx(0.92)
        assert tsd["destinationCode"] == ""

        assert base["acctTypeCode"] == "M"
        assert base["reqTypeCode"] == "N"
        assert "confNum" not in base

        assert opt["strategyType"] == "CU"
        assert opt["numOfLegs"] == 2
        assert len(opt["complexOrderDetails"]) == 2

        leg0 = opt["complexOrderDetails"][0]
        assert leg0["orderActionCode"] == "BO"
        assert leg0["securityDetail"]["symbol"] == "QS280121C7"

        leg1 = opt["complexOrderDetails"][1]
        assert leg1["orderActionCode"] == "SO"
        assert leg1["securityDetail"]["symbol"] == "QS280121C12"

    def test_to_place_body_injects_conf_num_and_req_type(self):
        order = _make_order_request()
        body = order.to_place_body("C31PHDRX")

        params = body["parameters"]
        base = params["baseOrderDetail"]

        assert base["reqTypeCode"] == "P"
        assert base["confNum"] == "C31PHDRX"
        assert "confNum" in base

    def test_to_place_body_legs_preserved(self):
        order = _make_order_request()
        body = order.to_place_body("C31PHDRX")
        legs = body["parameters"]["baseOrderDetail"]["optionDetail"]["complexOrderDetails"]
        assert len(legs) == 2
        assert legs[0]["orderActionCode"] == "BO"
        assert legs[1]["orderActionCode"] == "SO"

    def test_num_of_legs_derived_from_legs_list(self):
        order = _make_order_request()
        body = order.to_preview_body()
        assert body["parameters"]["baseOrderDetail"]["optionDetail"]["numOfLegs"] == 2

    def test_credit_order(self):
        order = MultiLegOptionOrderRequest(
            acctNum="Z21772945",
            netAmount=0.50,
            dbCrEvenCode="CR",
            legs=[_make_leg("SO", "QS280121C7")],
        )
        body = order.to_preview_body()
        assert body["parameters"]["tradableSecOrderDetail"]["dbCrEvenCode"] == "CR"

    def test_defaults(self):
        order = MultiLegOptionOrderRequest(
            acctNum="Z99999999",
            netAmount=1.0,
            legs=[_make_leg()],
        )
        assert order.tif_code == "D"
        assert order.db_cr_even_code == "DB"
        assert order.strategy_type == "CU"
        assert order.acct_type_code == "M"
        assert order.exp_date_default_ind is True
        assert order.exp_time_default_ind is True


# ---------------------------------------------------------------------------
# MultiLegOptionOrderConfirmDetail
# ---------------------------------------------------------------------------

class TestMultiLegOptionOrderConfirmDetail:
    def test_parses_preview_confirm_detail(self):
        detail = MultiLegOptionOrderConfirmDetail.model_validate(
            _make_confirm_detail("V")
        )
        assert detail.resp_type_code == "V"
        assert detail.conf_num == "C31PHDRX"
        assert detail.acct_type_code == "M"
        assert detail.net_amount == pytest.approx(0.92)
        assert detail.net_ask == pytest.approx(1.05)
        assert detail.net_bid == pytest.approx(0.80)
        assert detail.mid_point == pytest.approx(0.925)
        assert detail.gcd == 1
        assert detail.final_total_val_of_order == pytest.approx(92.0)
        assert detail.total_est_commission == pytest.approx(0.0)
        assert detail.subtotal_val_of_order == pytest.approx(92.0)

    def test_parses_option_detail_legs(self):
        detail = MultiLegOptionOrderConfirmDetail.model_validate(
            _make_confirm_detail("V")
        )
        opt = detail.order_detail.base_order_detail.option_detail
        assert opt is not None
        assert opt.complex_type == "CO"
        assert opt.num_of_legs == 2
        assert len(opt.complex_order_details) == 2

        leg0 = opt.complex_order_details[0]
        assert leg0.order_action_code == "BC"
        assert leg0.security_detail.symbol == "QS280121C7"
        assert leg0.security_detail.etf_ind is False
        assert leg0.price_detail.price == pytest.approx(2.39)
        assert leg0.est_commission_detail.est_commission == pytest.approx(0.0)

        leg1 = opt.complex_order_details[1]
        assert leg1.order_action_code == "SC"
        assert leg1.security_detail.symbol == "QS280121C12"

    def test_parses_tradable_sec_order_detail(self):
        detail = MultiLegOptionOrderConfirmDetail.model_validate(
            _make_confirm_detail("V")
        )
        tsd = detail.order_detail.tradable_sec_order_detail
        assert tsd is not None
        assert tsd.tif_code == "D"
        assert tsd.db_cr_even_code == "DB"
        assert tsd.aon_code is False
        assert tsd.destination_code == ""
        assert tsd.price_type_detail.price_type_code == "L"

    def test_optional_fields_default_none(self):
        detail = MultiLegOptionOrderConfirmDetail.model_validate({})
        assert detail.resp_type_code is None
        assert detail.conf_num is None
        assert detail.order_detail is None


# ---------------------------------------------------------------------------
# OptionSysMsgs
# ---------------------------------------------------------------------------

class TestOptionSysMsgs:
    def test_parses_warning_message(self):
        msgs = OptionSysMsgs.model_validate(_make_sys_msgs())
        assert msgs.sys_msg is not None
        assert len(msgs.sys_msg) == 1
        msg = msgs.sys_msg[0]
        assert msg.message == "Other"
        assert msg.code == "1999"
        assert msg.type == "warning"
        assert msg.source == "multilegorder"
        assert "354020" in msg.detail


# ---------------------------------------------------------------------------
# MultiLegOptionPreviewResponse
# ---------------------------------------------------------------------------

class TestMultiLegOptionPreviewResponse:
    def test_from_api_response_parsed(self):
        resp = MultiLegOptionPreviewResponse.from_api_response(_make_preview_response())
        assert resp.acct_num == "Z21772945"
        assert resp.order_confirm_detail is not None
        assert resp.order_confirm_detail.resp_type_code == "V"

    def test_conf_num_property(self):
        resp = MultiLegOptionPreviewResponse.from_api_response(
            _make_preview_response("C31PHDRX")
        )
        assert resp.conf_num == "C31PHDRX"

    def test_is_validated_true(self):
        resp = MultiLegOptionPreviewResponse.from_api_response(_make_preview_response())
        assert resp.is_validated is True

    def test_is_validated_false_when_not_v(self):
        raw = {
            "multiLegOptionResponse": {
                "orderConfirmDetail": _make_confirm_detail(resp_type_code="E")
            }
        }
        resp = MultiLegOptionPreviewResponse.from_api_response(raw)
        assert resp.is_validated is False

    def test_conf_num_none_on_empty(self):
        resp = MultiLegOptionPreviewResponse.from_api_response({})
        assert resp.conf_num is None
        assert resp.is_validated is False

    def test_sys_msgs_accessible(self):
        resp = MultiLegOptionPreviewResponse.from_api_response(_make_preview_response())
        assert resp.sys_msgs is not None
        assert resp.sys_msgs.sys_msg is not None
        assert len(resp.sys_msgs.sys_msg) == 1

    def test_leg_symbols_accessible(self):
        resp = MultiLegOptionPreviewResponse.from_api_response(_make_preview_response())
        legs = (
            resp.order_confirm_detail
            .order_detail
            .base_order_detail
            .option_detail
            .complex_order_details
        )
        assert legs[0].security_detail.symbol == "QS280121C7"
        assert legs[1].security_detail.symbol == "QS280121C12"


# ---------------------------------------------------------------------------
# MultiLegOptionPlaceResponse
# ---------------------------------------------------------------------------

class TestMultiLegOptionPlaceResponse:
    def test_from_api_response_parsed(self):
        resp = MultiLegOptionPlaceResponse.from_api_response(_make_place_response())
        assert resp.acct_num == "Z21772945"
        assert resp.order_confirm_detail is not None
        assert resp.order_confirm_detail.resp_type_code == "A"

    def test_conf_num_property(self):
        resp = MultiLegOptionPlaceResponse.from_api_response(
            _make_place_response("C31PHDRX")
        )
        assert resp.conf_num == "C31PHDRX"

    def test_is_accepted_true(self):
        resp = MultiLegOptionPlaceResponse.from_api_response(_make_place_response())
        assert resp.is_accepted is True

    def test_is_accepted_false_when_not_a(self):
        raw = {
            "multiLegOptionResponse": {
                "orderConfirmDetail": _make_confirm_detail(resp_type_code="V")
            }
        }
        resp = MultiLegOptionPlaceResponse.from_api_response(raw)
        assert resp.is_accepted is False

    def test_conf_num_none_on_empty(self):
        resp = MultiLegOptionPlaceResponse.from_api_response({})
        assert resp.conf_num is None
        assert resp.is_accepted is False

    def test_net_amount(self):
        resp = MultiLegOptionPlaceResponse.from_api_response(_make_place_response())
        assert resp.order_confirm_detail.net_amount == pytest.approx(0.92)


# ---------------------------------------------------------------------------
# MultiLegOptionOrderAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestMultiLegOptionOrderAPIPreview:
    @respx.mock
    def test_preview_posts_to_correct_url(self):
        route = respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_preview_response())
        )
        api = MultiLegOptionOrderAPI(httpx.Client())
        result = api.preview_order(_make_order_request())

        assert route.called
        assert isinstance(result, MultiLegOptionPreviewResponse)

    @respx.mock
    def test_preview_request_body_matches_capture(self):
        route = respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_preview_response())
        )
        api = MultiLegOptionOrderAPI(httpx.Client())
        api.preview_order(_make_order_request())

        sent = json.loads(route.calls[0].request.content)
        params = sent["parameters"]
        tsd = params["tradableSecOrderDetail"]
        base = params["baseOrderDetail"]
        opt = base["optionDetail"]

        assert params["acctNum"] == "Z21772945"
        assert tsd["tifCode"] == "D"
        assert tsd["dbCrEvenCode"] == "DB"
        assert tsd["netAmount"] == pytest.approx(0.92)
        assert base["reqTypeCode"] == "N"
        assert "confNum" not in base
        assert opt["strategyType"] == "CU"
        assert opt["numOfLegs"] == 2
        assert opt["complexOrderDetails"][0]["orderActionCode"] == "BO"
        assert opt["complexOrderDetails"][1]["orderActionCode"] == "SO"

    @respx.mock
    def test_preview_returns_validated_response(self):
        respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_preview_response())
        )
        api = MultiLegOptionOrderAPI(httpx.Client())
        result = api.preview_order(_make_order_request())

        assert result.is_validated
        assert result.conf_num == "C31PHDRX"

    @respx.mock
    def test_preview_raises_on_http_error(self):
        respx.post(_PREVIEW_URL).mock(return_value=httpx.Response(401))
        api = MultiLegOptionOrderAPI(httpx.Client())
        with pytest.raises(httpx.HTTPStatusError):
            api.preview_order(_make_order_request())


class TestMultiLegOptionOrderAPIPlace:
    @respx.mock
    def test_place_posts_to_correct_url(self):
        route = respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_place_response())
        )
        api = MultiLegOptionOrderAPI(httpx.Client(), live_trading=True)
        result = api.place_order(_make_order_request(), conf_num="C31PHDRX")

        assert route.called
        assert isinstance(result, MultiLegOptionPlaceResponse)

    @respx.mock
    def test_place_request_body_matches_capture(self):
        route = respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_place_response())
        )
        api = MultiLegOptionOrderAPI(httpx.Client(), live_trading=True)
        api.place_order(_make_order_request(), conf_num="C31PHDRX")

        sent = json.loads(route.calls[0].request.content)
        params = sent["parameters"]
        base = params["baseOrderDetail"]

        assert base["reqTypeCode"] == "P"
        assert base["confNum"] == "C31PHDRX"
        assert params["acctNum"] == "Z21772945"
        assert base["optionDetail"]["numOfLegs"] == 2

    @respx.mock
    def test_place_returns_accepted_response(self):
        respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_place_response())
        )
        api = MultiLegOptionOrderAPI(httpx.Client(), live_trading=True)
        result = api.place_order(_make_order_request(), conf_num="C31PHDRX")

        assert result.is_accepted
        assert result.conf_num == "C31PHDRX"

    @respx.mock
    def test_place_raises_on_http_error(self):
        respx.post(_PLACE_URL).mock(return_value=httpx.Response(500))
        api = MultiLegOptionOrderAPI(httpx.Client(), live_trading=True)
        with pytest.raises(httpx.HTTPStatusError):
            api.place_order(_make_order_request(), conf_num="C31PHDRX")


class TestMultiLegOptionOrderAPIEndToEnd:
    @respx.mock
    def test_full_preview_then_place_workflow(self):
        """Verify the conf_num flows from preview into the place request body."""
        preview_route = respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_preview_response("C31PHDRX"))
        )
        place_route = respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_place_response("C31PHDRX"))
        )

        api = MultiLegOptionOrderAPI(httpx.Client(), live_trading=True)
        order = _make_order_request()

        preview = api.preview_order(order)
        assert preview.is_validated
        conf_num = preview.conf_num
        assert conf_num == "C31PHDRX"

        place = api.place_order(order, conf_num=conf_num)
        assert place.is_accepted
        assert place.conf_num == "C31PHDRX"

        # Verify place request actually used the conf_num
        place_body = json.loads(place_route.calls[0].request.content)
        assert place_body["parameters"]["baseOrderDetail"]["confNum"] == "C31PHDRX"
        assert place_body["parameters"]["baseOrderDetail"]["reqTypeCode"] == "P"
