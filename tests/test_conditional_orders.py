"""Tests for the conditional order (OTOCO/OTO/OCO) models and ConditionalOrderAPI client."""
from __future__ import annotations

import json
import pytest
import httpx
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.conditional_order import (
    ConditionalOrderLeg,
    ConditionalOrderRequest,
    ConditionalPreviewResponse,
    ConditionalPlaceResponse,
    CondOrderSysMsg,
    CondOrderConfirmDetail,
)
from fidelity_trader.orders.conditional import ConditionalOrderAPI

_PREVIEW_URL = f"{DPSERVICE_URL}/ftgw/dp/orderentry/conditional/preview/v1"
_PLACE_URL = f"{DPSERVICE_URL}/ftgw/dp/orderentry/conditional/place/v1"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_otoco_request(
    acct_num: str = "Z21772945",
    symbol: str = "QS",
) -> ConditionalOrderRequest:
    """OTOCO: buy triggers take-profit limit sell + stop-loss sell."""
    return ConditionalOrderRequest(
        condOrderTypeCode="OTOCO",
        acctNum=acct_num,
        legs=[
            ConditionalOrderLeg(
                acctTypeCode="M", orderActionCode="B", qty=1,
                symbol=symbol, tifCode="D", priceTypeCode="L", limitPrice=6.2,
            ),
            ConditionalOrderLeg(
                acctTypeCode="M", orderActionCode="S", qty=1,
                symbol=symbol, tifCode="D", priceTypeCode="L", limitPrice=7,
            ),
            ConditionalOrderLeg(
                acctTypeCode="M", orderActionCode="S", qty=1,
                symbol=symbol, tifCode="D", priceTypeCode="S", stopPrice=5.5,
            ),
        ],
    )


def _make_oto_request(
    acct_num: str = "Z21772945",
    symbol: str = "AAPL",
) -> ConditionalOrderRequest:
    """OTO: buy triggers a sell."""
    return ConditionalOrderRequest(
        condOrderTypeCode="OTO",
        acctNum=acct_num,
        legs=[
            ConditionalOrderLeg(
                acctTypeCode="M", orderActionCode="B", qty=10,
                symbol=symbol, tifCode="D", priceTypeCode="L", limitPrice=150.0,
            ),
            ConditionalOrderLeg(
                acctTypeCode="M", orderActionCode="S", qty=10,
                symbol=symbol, tifCode="G", priceTypeCode="L", limitPrice=160.0,
            ),
        ],
    )


def _make_oco_request(
    acct_num: str = "Z21772945",
    symbol: str = "TSLA",
) -> ConditionalOrderRequest:
    """OCO: take-profit OR stop-loss (one cancels other)."""
    return ConditionalOrderRequest(
        condOrderTypeCode="OCO",
        acctNum=acct_num,
        legs=[
            ConditionalOrderLeg(
                acctTypeCode="M", orderActionCode="S", qty=5,
                symbol=symbol, tifCode="D", priceTypeCode="L", limitPrice=200.0,
            ),
            ConditionalOrderLeg(
                acctTypeCode="M", orderActionCode="S", qty=5,
                symbol=symbol, tifCode="D", priceTypeCode="S", stopPrice=180.0,
            ),
        ],
    )


def _make_leg_confirm(
    resp_type_code: str = "V",
    conf_num: str = "D02JRNZX",
    action: str = "B",
    symbol: str = "QS",
    net_amt: float = 6.2,
    price_type_code: str = "L",
    limit_price: float | None = 6.2,
    stop_price: float | None = None,
    warnings: list[dict] | None = None,
) -> dict:
    """Build an ``orderConfirmDetail`` dict for one leg."""
    price_detail_inner: dict = {"priceTypeCode": price_type_code}
    if limit_price is not None:
        price_detail_inner["limitPrice"] = limit_price
    if stop_price is not None:
        price_detail_inner["stopPrice"] = stop_price

    order_detail: dict = {
        "baseOrderDetail": {
            "orderActionCode": action,
            "qty": 1,
            "valueOfOrder": net_amt,
            "secDetail": {"symbol": symbol, "cusip": "74767V109", "secDesc": "QUANTUMSCAPE CORP COM CL A"},
        },
        "tradableSecOrderDetail": {
            "tifCode": "D",
            "priceTypeDetail": price_detail_inner,
        },
    }
    if warnings:
        order_detail["sysMsgs"] = {"sysMsg": warnings}

    return {
        "orderConfirmDetail": {
            "respTypeCode": resp_type_code,
            "confNum": conf_num,
            "acctTypeCode": "M",
            "netAmt": net_amt,
            "totalCost": net_amt,
            "orderDetail": order_detail,
            "estCommDetail": {"amt": 0.0, "typeCode": "3", "estComm": 0.0},
            "priceDetail": {"price": 6.215, "priceDateTime": 1775152327, "bidPrice": 6.21, "askPrice": 6.22},
        }
    }


def _make_otoco_preview_response() -> dict:
    """Build the full preview response for an OTOCO order (3 legs)."""
    return {
        "preview": {
            "sysMsgs": {
                "sysMsg": [
                    {"message": "Success", "detail": "Code=000000, Text=Success, Source=ConditionalOrder",
                     "source": "ConditionalOrder", "code": "0999", "type": "info"}
                ]
            },
            "acctNum": "Z21772945",
            "condOrderDetails": [
                _make_leg_confirm("V", "D02JRNZX", "B", "QS", 6.2, "L", 6.2),
                _make_leg_confirm("V", "D02JRPBB", "S", "QS", 7.0, "L", 7),
                _make_leg_confirm("V", "D02JRPBD", "S", "QS", 5.5, "S", None, 5.5,
                                  warnings=[{"message": "(001924) Stop Loss and Stop Limit orders are triggered by...",
                                             "code": "1999", "type": "warning", "source": "ConditionalOrder",
                                             "detail": "warning detail"}]),
            ],
        }
    }


def _make_otoco_place_response() -> dict:
    """Build the full place response for an OTOCO order (3 legs)."""
    return {
        "place": {
            "acctNum": "Z21772945",
            "condOrderDetails": [
                _make_leg_confirm("A", "D02JRNZX", "B", "QS", 6.2, "L", 6.2),
                _make_leg_confirm("A", "D02JRPBB", "S", "QS", 7.0, "L", 7),
                _make_leg_confirm("A", "D02JRPBD", "S", "QS", 5.5, "S", None, 5.5),
            ],
        }
    }


def _make_oto_preview_response() -> dict:
    return {
        "preview": {
            "acctNum": "Z21772945",
            "condOrderDetails": [
                _make_leg_confirm("V", "CONF001", "B", "AAPL", 1500.0, "L", 150.0),
                _make_leg_confirm("V", "CONF002", "S", "AAPL", 1600.0, "L", 160.0),
            ],
        }
    }


def _make_oco_preview_response() -> dict:
    return {
        "preview": {
            "acctNum": "Z21772945",
            "condOrderDetails": [
                _make_leg_confirm("V", "CONF_A", "S", "TSLA", 1000.0, "L", 200.0),
                _make_leg_confirm("V", "CONF_B", "S", "TSLA", 900.0, "S", None, 180.0),
            ],
        }
    }


# ---------------------------------------------------------------------------
# ConditionalOrderLeg — body construction
# ---------------------------------------------------------------------------

class TestConditionalOrderLeg:
    def test_limit_leg_detail_shape(self):
        leg = ConditionalOrderLeg(
            acctTypeCode="M", orderActionCode="B", qty=1,
            symbol="QS", tifCode="D", priceTypeCode="L", limitPrice=6.2,
        )
        detail = leg._to_order_detail()
        base = detail["baseOrderDetail"]
        tradable = detail["tradableSecOrderDetail"]

        assert base["acctTypeCode"] == "M"
        assert base["orderActionCode"] == "B"
        assert base["qty"] == 1
        assert base["secDetail"]["symbol"] == "QS"
        assert "confNum" not in base

        assert tradable["tifCode"] == "D"
        assert tradable["priceTypeDetail"]["priceTypeCode"] == "L"
        assert tradable["priceTypeDetail"]["limitPrice"] == pytest.approx(6.2)
        assert "stopPrice" not in tradable["priceTypeDetail"]

    def test_stop_leg_detail_shape(self):
        leg = ConditionalOrderLeg(
            acctTypeCode="M", orderActionCode="S", qty=1,
            symbol="QS", tifCode="D", priceTypeCode="S", stopPrice=5.5,
        )
        detail = leg._to_order_detail()
        ptd = detail["tradableSecOrderDetail"]["priceTypeDetail"]

        assert ptd["priceTypeCode"] == "S"
        assert ptd["stopPrice"] == pytest.approx(5.5)
        assert "limitPrice" not in ptd

    def test_place_detail_injects_conf_num(self):
        leg = ConditionalOrderLeg(
            acctTypeCode="M", orderActionCode="S", qty=1,
            symbol="QS", tifCode="D", priceTypeCode="L", limitPrice=7,
        )
        detail = leg._to_place_detail(conf_num="D02JRPBB")
        assert detail["baseOrderDetail"]["confNum"] == "D02JRPBB"

    def test_place_detail_no_conf_num(self):
        leg = ConditionalOrderLeg(
            acctTypeCode="M", orderActionCode="B", qty=1,
            symbol="QS", tifCode="D", priceTypeCode="L", limitPrice=6.2,
        )
        detail = leg._to_place_detail()
        assert "confNum" not in detail["baseOrderDetail"]

    def test_defaults(self):
        leg = ConditionalOrderLeg(
            orderActionCode="B", qty=5, symbol="MSFT", priceTypeCode="M",
        )
        assert leg.acct_type_code == "M"
        assert leg.tif_code == "D"
        assert leg.limit_price is None
        assert leg.stop_price is None


# ---------------------------------------------------------------------------
# ConditionalOrderRequest — OTOCO body
# ---------------------------------------------------------------------------

class TestConditionalOrderRequestOTOCO:
    def test_preview_body_top_level_key_is_parameters(self):
        order = _make_otoco_request()
        body = order.to_preview_body()
        assert "parameters" in body
        assert "request" not in body

    def test_preview_body_has_cond_order_type_code(self):
        order = _make_otoco_request()
        body = order.to_preview_body()
        assert body["parameters"]["condOrderTypeCode"] == "OTOCO"

    def test_preview_body_has_acct_num(self):
        order = _make_otoco_request()
        body = order.to_preview_body()
        assert body["parameters"]["acctNum"] == "Z21772945"

    def test_preview_body_has_three_legs(self):
        order = _make_otoco_request()
        body = order.to_preview_body()
        legs = body["parameters"]["condOrderDetails"]
        assert len(legs) == 3

    def test_preview_body_leg_0_is_buy(self):
        order = _make_otoco_request()
        body = order.to_preview_body()
        leg0 = body["parameters"]["condOrderDetails"][0]
        assert leg0["baseOrderDetail"]["orderActionCode"] == "B"
        assert leg0["tradableSecOrderDetail"]["priceTypeDetail"]["limitPrice"] == pytest.approx(6.2)

    def test_preview_body_leg_1_is_limit_sell(self):
        order = _make_otoco_request()
        body = order.to_preview_body()
        leg1 = body["parameters"]["condOrderDetails"][1]
        assert leg1["baseOrderDetail"]["orderActionCode"] == "S"
        assert leg1["tradableSecOrderDetail"]["priceTypeDetail"]["priceTypeCode"] == "L"
        assert leg1["tradableSecOrderDetail"]["priceTypeDetail"]["limitPrice"] == pytest.approx(7)

    def test_preview_body_leg_2_is_stop_sell(self):
        order = _make_otoco_request()
        body = order.to_preview_body()
        leg2 = body["parameters"]["condOrderDetails"][2]
        assert leg2["baseOrderDetail"]["orderActionCode"] == "S"
        assert leg2["tradableSecOrderDetail"]["priceTypeDetail"]["priceTypeCode"] == "S"
        assert leg2["tradableSecOrderDetail"]["priceTypeDetail"]["stopPrice"] == pytest.approx(5.5)
        assert "limitPrice" not in leg2["tradableSecOrderDetail"]["priceTypeDetail"]

    def test_preview_body_empty_cntgnt_details(self):
        order = _make_otoco_request()
        body = order.to_preview_body()
        assert body["parameters"]["cntgntDetails"] == []
        assert body["parameters"]["condOrderDetail"] == {}

    def test_preview_body_no_preview_ind(self):
        order = _make_otoco_request()
        body = order.to_preview_body()
        assert "previewInd" not in body["parameters"]
        assert "confInd" not in body["parameters"]

    def test_place_body_has_preview_ind_false(self):
        order = _make_otoco_request()
        body = order.to_place_body(["D02JRNZX", "D02JRPBB"])
        assert body["parameters"]["previewInd"] is False
        assert body["parameters"]["confInd"] is False

    def test_place_body_primary_leg_no_conf_num(self):
        order = _make_otoco_request()
        body = order.to_place_body(["D02JRNZX", "D02JRPBB"])
        leg0 = body["parameters"]["condOrderDetails"][0]
        assert "confNum" not in leg0["baseOrderDetail"]

    def test_place_body_triggered_legs_have_conf_nums(self):
        order = _make_otoco_request()
        body = order.to_place_body(["D02JRNZX", "D02JRPBB"])
        leg1 = body["parameters"]["condOrderDetails"][1]
        leg2 = body["parameters"]["condOrderDetails"][2]
        assert leg1["baseOrderDetail"]["confNum"] == "D02JRNZX"
        assert leg2["baseOrderDetail"]["confNum"] == "D02JRPBB"

    def test_place_body_matches_captured_shape(self):
        """Verify the full place body matches the captured traffic structure."""
        order = _make_otoco_request()
        body = order.to_place_body(["D02JRNZX", "D02JRPBB"])
        params = body["parameters"]

        assert params["condOrderTypeCode"] == "OTOCO"
        assert params["acctNum"] == "Z21772945"
        assert params["cntgntDetails"] == []
        assert params["condOrderDetail"] == {}
        assert params["previewInd"] is False
        assert params["confInd"] is False
        assert len(params["condOrderDetails"]) == 3


# ---------------------------------------------------------------------------
# ConditionalOrderRequest — OTO body
# ---------------------------------------------------------------------------

class TestConditionalOrderRequestOTO:
    def test_preview_body_has_two_legs(self):
        order = _make_oto_request()
        body = order.to_preview_body()
        assert body["parameters"]["condOrderTypeCode"] == "OTO"
        assert len(body["parameters"]["condOrderDetails"]) == 2

    def test_preview_body_leg_actions(self):
        order = _make_oto_request()
        body = order.to_preview_body()
        legs = body["parameters"]["condOrderDetails"]
        assert legs[0]["baseOrderDetail"]["orderActionCode"] == "B"
        assert legs[1]["baseOrderDetail"]["orderActionCode"] == "S"

    def test_place_body_conf_num_on_triggered_leg_only(self):
        order = _make_oto_request()
        body = order.to_place_body(["CONF001"])
        legs = body["parameters"]["condOrderDetails"]
        assert "confNum" not in legs[0]["baseOrderDetail"]
        assert legs[1]["baseOrderDetail"]["confNum"] == "CONF001"

    def test_oto_gtc_tif_on_triggered_leg(self):
        order = _make_oto_request()
        body = order.to_preview_body()
        leg1 = body["parameters"]["condOrderDetails"][1]
        assert leg1["tradableSecOrderDetail"]["tifCode"] == "G"


# ---------------------------------------------------------------------------
# ConditionalOrderRequest — OCO body
# ---------------------------------------------------------------------------

class TestConditionalOrderRequestOCO:
    def test_preview_body_has_two_legs(self):
        order = _make_oco_request()
        body = order.to_preview_body()
        assert body["parameters"]["condOrderTypeCode"] == "OCO"
        assert len(body["parameters"]["condOrderDetails"]) == 2

    def test_oco_first_leg_is_limit(self):
        order = _make_oco_request()
        body = order.to_preview_body()
        leg0 = body["parameters"]["condOrderDetails"][0]
        ptd = leg0["tradableSecOrderDetail"]["priceTypeDetail"]
        assert ptd["priceTypeCode"] == "L"
        assert ptd["limitPrice"] == pytest.approx(200.0)

    def test_oco_second_leg_is_stop(self):
        order = _make_oco_request()
        body = order.to_preview_body()
        leg1 = body["parameters"]["condOrderDetails"][1]
        ptd = leg1["tradableSecOrderDetail"]["priceTypeDetail"]
        assert ptd["priceTypeCode"] == "S"
        assert ptd["stopPrice"] == pytest.approx(180.0)
        assert "limitPrice" not in ptd

    def test_oco_place_conf_num_on_triggered_leg(self):
        order = _make_oco_request()
        body = order.to_place_body(["CONF_A"])
        legs = body["parameters"]["condOrderDetails"]
        assert "confNum" not in legs[0]["baseOrderDetail"]
        assert legs[1]["baseOrderDetail"]["confNum"] == "CONF_A"


# ---------------------------------------------------------------------------
# Response sub-models
# ---------------------------------------------------------------------------

class TestCondOrderSysMsg:
    def test_parses_info_message(self):
        msg = CondOrderSysMsg.model_validate({
            "message": "Success", "code": "0999", "type": "info",
            "source": "ConditionalOrder", "detail": "Code=000000",
        })
        assert msg.message == "Success"
        assert msg.code == "0999"
        assert msg.type == "info"
        assert msg.source == "ConditionalOrder"

    def test_parses_warning_message(self):
        msg = CondOrderSysMsg.model_validate({
            "message": "(001924) Stop Loss orders...", "code": "1999",
            "type": "warning", "source": "ConditionalOrder",
        })
        assert msg.type == "warning"
        assert msg.code == "1999"

    def test_optional_fields(self):
        msg = CondOrderSysMsg.model_validate({})
        assert msg.message is None
        assert msg.code is None
        assert msg.type is None


class TestCondOrderConfirmDetail:
    def test_parses_preview_confirm(self):
        raw = _make_leg_confirm("V", "D02JRNZX", "B", "QS", 6.2, "L", 6.2)
        detail = CondOrderConfirmDetail.model_validate(raw["orderConfirmDetail"])
        assert detail.resp_type_code == "V"
        assert detail.conf_num == "D02JRNZX"
        assert detail.net_amt == pytest.approx(6.2)
        assert detail.total_cost == pytest.approx(6.2)

    def test_parses_est_comm_detail(self):
        raw = _make_leg_confirm("V", "D02JRNZX")
        detail = CondOrderConfirmDetail.model_validate(raw["orderConfirmDetail"])
        assert detail.est_comm_detail is not None
        assert detail.est_comm_detail.amt == pytest.approx(0.0)
        assert detail.est_comm_detail.est_comm == pytest.approx(0.0)

    def test_parses_price_detail(self):
        raw = _make_leg_confirm("V", "D02JRNZX")
        detail = CondOrderConfirmDetail.model_validate(raw["orderConfirmDetail"])
        pd = detail.price_detail
        assert pd is not None
        assert pd.price == pytest.approx(6.215)
        assert pd.bid_price == pytest.approx(6.21)
        assert pd.ask_price == pytest.approx(6.22)
        assert pd.price_date_time == 1775152327

    def test_optional_fields(self):
        detail = CondOrderConfirmDetail.model_validate({})
        assert detail.resp_type_code is None
        assert detail.conf_num is None
        assert detail.order_detail is None
        assert detail.est_comm_detail is None
        assert detail.price_detail is None


class TestCondOrderDetail:
    def test_warnings_from_stop_leg(self):
        raw = _make_leg_confirm(
            "V", "D02JRPBD", "S", "QS", 5.5, "S", None, 5.5,
            warnings=[{"message": "Stop warning", "code": "1999", "type": "warning",
                        "source": "ConditionalOrder"}],
        )
        detail = CondOrderConfirmDetail.model_validate(raw["orderConfirmDetail"])
        od = detail.order_detail
        assert od is not None
        assert len(od.warnings) == 1
        assert od.warnings[0].type == "warning"
        assert od.warnings[0].message == "Stop warning"

    def test_all_sys_msgs(self):
        raw = _make_leg_confirm(
            "V", "D02JRPBD", "S", "QS", 5.5, "S", None, 5.5,
            warnings=[
                {"message": "Info", "code": "0999", "type": "info", "source": "CO"},
                {"message": "Warn", "code": "1999", "type": "warning", "source": "CO"},
            ],
        )
        detail = CondOrderConfirmDetail.model_validate(raw["orderConfirmDetail"])
        all_msgs = detail.order_detail.all_sys_msgs
        assert len(all_msgs) == 2
        assert all_msgs[0].type == "info"
        assert all_msgs[1].type == "warning"

    def test_no_sys_msgs(self):
        raw = _make_leg_confirm("V", "D02JRNZX")
        detail = CondOrderConfirmDetail.model_validate(raw["orderConfirmDetail"])
        assert detail.order_detail.warnings == []
        assert detail.order_detail.all_sys_msgs == []

    def test_base_order_detail_parsed(self):
        raw = _make_leg_confirm("V", "D02JRNZX", "B", "QS", 6.2)
        detail = CondOrderConfirmDetail.model_validate(raw["orderConfirmDetail"])
        base = detail.order_detail.base_order_detail
        assert base is not None
        assert base.order_action_code == "B"
        assert base.qty == pytest.approx(1)
        assert base.value_of_order == pytest.approx(6.2)
        assert base.sec_detail is not None
        assert base.sec_detail.symbol == "QS"
        assert base.sec_detail.cusip == "74767V109"

    def test_tradable_sec_detail_limit(self):
        raw = _make_leg_confirm("V", "D02JRNZX", "B", "QS", 6.2, "L", 6.2)
        detail = CondOrderConfirmDetail.model_validate(raw["orderConfirmDetail"])
        tsd = detail.order_detail.tradable_sec_order_detail
        assert tsd is not None
        assert tsd.tif_code == "D"
        assert tsd.price_type_detail.price_type_code == "L"
        assert tsd.price_type_detail.limit_price == pytest.approx(6.2)

    def test_tradable_sec_detail_stop(self):
        raw = _make_leg_confirm("V", "D02JRPBD", "S", "QS", 5.5, "S", None, 5.5)
        detail = CondOrderConfirmDetail.model_validate(raw["orderConfirmDetail"])
        tsd = detail.order_detail.tradable_sec_order_detail
        assert tsd.price_type_detail.price_type_code == "S"
        assert tsd.price_type_detail.stop_price == pytest.approx(5.5)
        assert tsd.price_type_detail.limit_price is None


# ---------------------------------------------------------------------------
# ConditionalPreviewResponse
# ---------------------------------------------------------------------------

class TestConditionalPreviewResponse:
    def test_from_api_response_parses_legs(self):
        resp = ConditionalPreviewResponse.from_api_response(_make_otoco_preview_response())
        assert resp.acct_num == "Z21772945"
        assert len(resp.legs) == 3

    def test_conf_nums_extraction(self):
        resp = ConditionalPreviewResponse.from_api_response(_make_otoco_preview_response())
        assert resp.conf_nums == ["D02JRNZX", "D02JRPBB", "D02JRPBD"]

    def test_is_validated_true(self):
        resp = ConditionalPreviewResponse.from_api_response(_make_otoco_preview_response())
        assert resp.is_validated is True

    def test_all_validated_true(self):
        resp = ConditionalPreviewResponse.from_api_response(_make_otoco_preview_response())
        assert resp.all_validated is True

    def test_all_validated_false_when_one_leg_not_v(self):
        raw = _make_otoco_preview_response()
        raw["preview"]["condOrderDetails"][1]["orderConfirmDetail"]["respTypeCode"] = "E"
        resp = ConditionalPreviewResponse.from_api_response(raw)
        assert resp.is_validated is True  # first leg is V
        assert resp.all_validated is False

    def test_is_validated_false_on_empty(self):
        resp = ConditionalPreviewResponse.from_api_response({})
        assert resp.is_validated is False
        assert resp.all_validated is False

    def test_conf_nums_empty_on_empty(self):
        resp = ConditionalPreviewResponse.from_api_response({})
        assert resp.conf_nums == []

    def test_top_level_sys_msgs_parsed(self):
        resp = ConditionalPreviewResponse.from_api_response(_make_otoco_preview_response())
        assert len(resp.top_sys_msgs) == 1
        assert resp.top_sys_msgs[0].message == "Success"
        assert resp.top_sys_msgs[0].code == "0999"

    def test_per_leg_resp_type_code(self):
        resp = ConditionalPreviewResponse.from_api_response(_make_otoco_preview_response())
        for leg in resp.legs:
            assert leg.order_confirm_detail.resp_type_code == "V"

    def test_oto_preview_two_legs(self):
        resp = ConditionalPreviewResponse.from_api_response(_make_oto_preview_response())
        assert len(resp.legs) == 2
        assert resp.conf_nums == ["CONF001", "CONF002"]

    def test_oco_preview_two_legs(self):
        resp = ConditionalPreviewResponse.from_api_response(_make_oco_preview_response())
        assert len(resp.legs) == 2
        assert resp.conf_nums == ["CONF_A", "CONF_B"]


# ---------------------------------------------------------------------------
# ConditionalPlaceResponse
# ---------------------------------------------------------------------------

class TestConditionalPlaceResponse:
    def test_from_api_response_parses_legs(self):
        resp = ConditionalPlaceResponse.from_api_response(_make_otoco_place_response())
        assert resp.acct_num == "Z21772945"
        assert len(resp.legs) == 3

    def test_is_accepted_true(self):
        resp = ConditionalPlaceResponse.from_api_response(_make_otoco_place_response())
        assert resp.is_accepted is True

    def test_all_accepted_true(self):
        resp = ConditionalPlaceResponse.from_api_response(_make_otoco_place_response())
        assert resp.all_accepted is True

    def test_all_accepted_false_when_one_leg_not_a(self):
        raw = _make_otoco_place_response()
        raw["place"]["condOrderDetails"][2]["orderConfirmDetail"]["respTypeCode"] = "E"
        resp = ConditionalPlaceResponse.from_api_response(raw)
        assert resp.is_accepted is True
        assert resp.all_accepted is False

    def test_is_accepted_false_on_empty(self):
        resp = ConditionalPlaceResponse.from_api_response({})
        assert resp.is_accepted is False
        assert resp.all_accepted is False

    def test_conf_nums_from_place(self):
        resp = ConditionalPlaceResponse.from_api_response(_make_otoco_place_response())
        assert resp.conf_nums == ["D02JRNZX", "D02JRPBB", "D02JRPBD"]

    def test_per_leg_resp_type_code(self):
        resp = ConditionalPlaceResponse.from_api_response(_make_otoco_place_response())
        for leg in resp.legs:
            assert leg.order_confirm_detail.resp_type_code == "A"


# ---------------------------------------------------------------------------
# ConditionalOrderAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestConditionalOrderAPIPreview:
    @respx.mock
    def test_preview_posts_to_correct_url(self):
        route = respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_otoco_preview_response())
        )
        api = ConditionalOrderAPI(httpx.Client())
        result = api.preview_order(_make_otoco_request())

        assert route.called
        assert isinstance(result, ConditionalPreviewResponse)

    @respx.mock
    def test_preview_request_body_uses_parameters_key(self):
        route = respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_otoco_preview_response())
        )
        api = ConditionalOrderAPI(httpx.Client())
        api.preview_order(_make_otoco_request())

        sent = json.loads(route.calls[0].request.content)
        assert "parameters" in sent
        assert "request" not in sent
        assert sent["parameters"]["condOrderTypeCode"] == "OTOCO"

    @respx.mock
    def test_preview_request_body_matches_capture(self):
        route = respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_otoco_preview_response())
        )
        api = ConditionalOrderAPI(httpx.Client())
        api.preview_order(_make_otoco_request())

        sent = json.loads(route.calls[0].request.content)
        params = sent["parameters"]
        assert params["acctNum"] == "Z21772945"
        assert params["cntgntDetails"] == []
        assert params["condOrderDetail"] == {}
        assert len(params["condOrderDetails"]) == 3
        assert "previewInd" not in params

        # Leg 0: buy limit
        leg0 = params["condOrderDetails"][0]
        assert leg0["baseOrderDetail"]["orderActionCode"] == "B"
        assert leg0["baseOrderDetail"]["qty"] == 1
        assert leg0["baseOrderDetail"]["secDetail"]["symbol"] == "QS"
        assert leg0["tradableSecOrderDetail"]["priceTypeDetail"]["priceTypeCode"] == "L"

        # Leg 2: stop sell
        leg2 = params["condOrderDetails"][2]
        assert leg2["tradableSecOrderDetail"]["priceTypeDetail"]["priceTypeCode"] == "S"
        assert leg2["tradableSecOrderDetail"]["priceTypeDetail"]["stopPrice"] == pytest.approx(5.5)

    @respx.mock
    def test_preview_returns_validated_response(self):
        respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_otoco_preview_response())
        )
        api = ConditionalOrderAPI(httpx.Client())
        result = api.preview_order(_make_otoco_request())

        assert result.all_validated
        assert len(result.conf_nums) == 3

    @respx.mock
    def test_preview_raises_on_http_error(self):
        respx.post(_PREVIEW_URL).mock(return_value=httpx.Response(401))
        api = ConditionalOrderAPI(httpx.Client())
        with pytest.raises(httpx.HTTPStatusError):
            api.preview_order(_make_otoco_request())


class TestConditionalOrderAPIPlace:
    @respx.mock
    def test_place_posts_to_correct_url(self):
        route = respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_otoco_place_response())
        )
        api = ConditionalOrderAPI(httpx.Client(), live_trading=True)
        result = api.place_order(
            _make_otoco_request(), conf_nums=["D02JRNZX", "D02JRPBB"]
        )

        assert route.called
        assert isinstance(result, ConditionalPlaceResponse)

    @respx.mock
    def test_place_request_body_matches_capture(self):
        route = respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_otoco_place_response())
        )
        api = ConditionalOrderAPI(httpx.Client(), live_trading=True)
        api.place_order(_make_otoco_request(), conf_nums=["D02JRNZX", "D02JRPBB"])

        sent = json.loads(route.calls[0].request.content)
        params = sent["parameters"]

        assert params["condOrderTypeCode"] == "OTOCO"
        assert params["acctNum"] == "Z21772945"
        assert params["previewInd"] is False
        assert params["confInd"] is False

        # Primary leg: no confNum
        assert "confNum" not in params["condOrderDetails"][0]["baseOrderDetail"]
        # Triggered legs: confNums applied
        assert params["condOrderDetails"][1]["baseOrderDetail"]["confNum"] == "D02JRNZX"
        assert params["condOrderDetails"][2]["baseOrderDetail"]["confNum"] == "D02JRPBB"

    @respx.mock
    def test_place_returns_accepted_response(self):
        respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_otoco_place_response())
        )
        api = ConditionalOrderAPI(httpx.Client(), live_trading=True)
        result = api.place_order(
            _make_otoco_request(), conf_nums=["D02JRNZX", "D02JRPBB"]
        )

        assert result.all_accepted
        assert len(result.conf_nums) == 3

    @respx.mock
    def test_place_raises_on_http_error(self):
        respx.post(_PLACE_URL).mock(return_value=httpx.Response(500))
        api = ConditionalOrderAPI(httpx.Client(), live_trading=True)
        with pytest.raises(httpx.HTTPStatusError):
            api.place_order(_make_otoco_request(), conf_nums=["X", "Y"])


class TestConditionalOrderAPIEndToEnd:
    @respx.mock
    def test_full_preview_then_place_workflow(self):
        """Verify conf_nums flow from preview into the place request body."""
        respx.post(_PREVIEW_URL).mock(
            return_value=httpx.Response(200, json=_make_otoco_preview_response())
        )
        place_route = respx.post(_PLACE_URL).mock(
            return_value=httpx.Response(200, json=_make_otoco_place_response())
        )

        api = ConditionalOrderAPI(httpx.Client(), live_trading=True)
        order = _make_otoco_request()

        preview = api.preview_order(order)
        assert preview.all_validated
        conf_nums = preview.conf_nums
        assert len(conf_nums) == 3

        # Pass triggered-leg confNums (skip primary leg's confNum)
        place = api.place_order(order, conf_nums=conf_nums[1:])
        assert place.all_accepted
        assert len(place.conf_nums) == 3

        # Verify place request used the triggered-leg confNums
        place_body = json.loads(place_route.calls[0].request.content)
        triggered_legs = place_body["parameters"]["condOrderDetails"][1:]
        assert triggered_legs[0]["baseOrderDetail"]["confNum"] == "D02JRPBB"
        assert triggered_legs[1]["baseOrderDetail"]["confNum"] == "D02JRPBD"
