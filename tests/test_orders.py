"""Tests for the order status API models and OrderStatusAPI client."""
import json
import pytest
import httpx
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.order import (
    OrderAmountDetail,
    OrderStatusDetail,
    OrderIdDetail,
    SecurityDetail,
    SpecialOrderDetail,
    BaseOrderDetail,
    PriceTypeDetail,
    OptionDetail,
    TradableSecOrderDetail,
    OrderDetail,
    AccountOrderSummary,
    OrderStatusResponse,
)
from fidelity_trader.orders.status import OrderStatusAPI

_ORDER_STATUS_URL = (
    f"{DPSERVICE_URL}/ftgw/dp/retail-order-status/v3/accounts/orders/status-summary"
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_amount_detail(
    qty_remaining: float = 0,
    avg_exec_price: float = 2.96,
    qty: float = 1,
    qty_exec: float = 1,
    commission: float = 0.65,
    gross: float = 296,
    net: float = 296.67,
) -> dict:
    return {
        "qtyRemaining": qty_remaining,
        "avgExecPrice": avg_exec_price,
        "qty": qty,
        "qtyExec": qty_exec,
        "commission": commission,
        "gross": gross,
        "net": net,
    }


def _make_order_detail(
    acct_num: str = "Z21772945",
    status_code: str = "FILLED",
) -> dict:
    return {
        "acctNum": acct_num,
        "statusDetail": {
            "statusCode": status_code,
            "statusDesc": "Filled at $2.96",
            "cancelableInd": False,
            "replaceableInd": False,
            "amountDetail": _make_amount_detail(),
        },
        "idDetail": {
            "confNum": "C30QFHNX",
            "systemOrderId": "26089I2KBM",
            "orderSource": "WO#",
        },
        "baseOrderDetail": {
            "description": "Buy to Open 1 Contract of SPXW 30 Mar 2026 6,330 Put Net Credit Limit at $2.10 (Day)",
            "entryDatetime": 1774891279,
            "orderActionCode": "BP",
            "actionCodeDesc": "Buy Put",
            "qty": 1,
            "sellAllInd": False,
            "acctTypeCode": 2,
            "acctTypeDesc": "Margin",
            "origQty": 1,
            "securityDetail": {
                "cusip": "8550489BX",
                "symbol": "SPXW260330P6330",
                "secDesc": "PUT (SPXW) NEW S & P 500 INDEX MAR 30 26 $6330 (100 SHS)",
                "secType": "8",
            },
            "specialOrderDetail": {
                "specialOrderCode": "C",
                "specialOrderName": "COMPLEX_OPTION",
            },
        },
        "tradableSecOrderDetail": {
            "priceTypeDetail": {
                "priceTypeCode": "L",
                "priceTypeDesc": "Limit",
                "priceTypeDetailDesc": "Limit at $2.10",
                "limitPrice": 2.1,
                "pegInd": False,
            },
            "optionDetail": {
                "contractSymbol": "SPXW",
                "contractType": "P",
                "expireDate": 1774843200,
                "strikePrice": 6330,
                "strategyCode": "CONDOR",
            },
            "tifCode": "D",
            "tifDesc": "Day",
            "mktRouteCode": "GLOBAL EXECUTION BROKERS L.P.",
            "marketSessionCode": "S",
        },
    }


def _make_acct_summary(
    acct_num: str = "Z25485019",
    order_count: int = 1,
    open_count: int = 1,
    filled_count: int = 0,
    cancelled_count: int = 0,
) -> dict:
    return {
        "acctNum": acct_num,
        "acctLevel": "B",
        "orderSummary": {
            "orderCount": order_count,
            "openCount": open_count,
            "filledCount": filled_count,
            "cancelledCount": cancelled_count,
        },
    }


def _make_api_response(
    acct_summaries: list[dict] = None,
    order_details: list[dict] = None,
) -> dict:
    if acct_summaries is None:
        acct_summaries = [_make_acct_summary()]
    if order_details is None:
        order_details = [_make_order_detail()]
    return {
        "order": {
            "acctDetails": {
                "acctDetail": acct_summaries,
            },
            "orderDetails": {
                "orderDetail": order_details,
            },
        }
    }


# ---------------------------------------------------------------------------
# OrderAmountDetail
# ---------------------------------------------------------------------------

class TestOrderAmountDetail:
    def test_parses_all_fields(self):
        ad = OrderAmountDetail.model_validate(_make_amount_detail())
        assert ad.qty_remaining == pytest.approx(0)
        assert ad.avg_exec_price == pytest.approx(2.96)
        assert ad.qty == pytest.approx(1)
        assert ad.qty_exec == pytest.approx(1)
        assert ad.commission == pytest.approx(0.65)
        assert ad.gross == pytest.approx(296)
        assert ad.net == pytest.approx(296.67)

    def test_optional_fields_default_none(self):
        ad = OrderAmountDetail.model_validate({})
        assert ad.qty_remaining is None
        assert ad.avg_exec_price is None
        assert ad.commission is None


# ---------------------------------------------------------------------------
# OrderStatusDetail
# ---------------------------------------------------------------------------

class TestOrderStatusDetail:
    def test_parses_filled_status(self):
        sd = OrderStatusDetail.model_validate({
            "statusCode": "FILLED",
            "statusDesc": "Filled at $2.96",
            "cancelableInd": False,
            "replaceableInd": False,
            "amountDetail": _make_amount_detail(),
        })
        assert sd.status_code == "FILLED"
        assert sd.status_desc == "Filled at $2.96"
        assert sd.cancelable_ind is False
        assert sd.replaceable_ind is False
        assert sd.amount_detail is not None
        assert sd.amount_detail.avg_exec_price == pytest.approx(2.96)

    def test_open_order_status(self):
        sd = OrderStatusDetail.model_validate({
            "statusCode": "OPEN",
            "statusDesc": "Open",
            "cancelableInd": True,
            "replaceableInd": True,
        })
        assert sd.status_code == "OPEN"
        assert sd.cancelable_ind is True
        assert sd.amount_detail is None

    def test_defaults(self):
        sd = OrderStatusDetail.model_validate({})
        assert sd.cancelable_ind is False
        assert sd.replaceable_ind is False
        assert sd.amount_detail is None


# ---------------------------------------------------------------------------
# OrderIdDetail
# ---------------------------------------------------------------------------

class TestOrderIdDetail:
    def test_parses_all_fields(self):
        idd = OrderIdDetail.model_validate({
            "confNum": "C30QFHNX",
            "systemOrderId": "26089I2KBM",
            "orderSource": "WO#",
        })
        assert idd.conf_num == "C30QFHNX"
        assert idd.system_order_id == "26089I2KBM"
        assert idd.order_source == "WO#"

    def test_optional_defaults(self):
        idd = OrderIdDetail.model_validate({})
        assert idd.conf_num is None
        assert idd.system_order_id is None


# ---------------------------------------------------------------------------
# SecurityDetail
# ---------------------------------------------------------------------------

class TestSecurityDetail:
    def test_parses_option_security(self):
        sd = SecurityDetail.model_validate({
            "cusip": "8550489BX",
            "symbol": "SPXW260330P6330",
            "secDesc": "PUT (SPXW) NEW S & P 500 INDEX MAR 30 26 $6330 (100 SHS)",
            "secType": "8",
        })
        assert sd.cusip == "8550489BX"
        assert sd.symbol == "SPXW260330P6330"
        assert sd.sec_type == "8"

    def test_optional_fields(self):
        sd = SecurityDetail.model_validate({})
        assert sd.cusip is None
        assert sd.symbol is None


# ---------------------------------------------------------------------------
# SpecialOrderDetail
# ---------------------------------------------------------------------------

class TestSpecialOrderDetail:
    def test_parses_complex_option(self):
        sod = SpecialOrderDetail.model_validate({
            "specialOrderCode": "C",
            "specialOrderName": "COMPLEX_OPTION",
        })
        assert sod.special_order_code == "C"
        assert sod.special_order_name == "COMPLEX_OPTION"


# ---------------------------------------------------------------------------
# BaseOrderDetail
# ---------------------------------------------------------------------------

class TestBaseOrderDetail:
    def test_parses_full_detail(self):
        bod = BaseOrderDetail.model_validate(
            _make_order_detail()["baseOrderDetail"]
        )
        assert bod.description.startswith("Buy to Open")
        assert bod.entry_datetime == 1774891279
        assert bod.order_action_code == "BP"
        assert bod.action_code_desc == "Buy Put"
        assert bod.qty == pytest.approx(1)
        assert bod.sell_all_ind is False
        assert bod.acct_type_desc == "Margin"
        assert bod.orig_qty == pytest.approx(1)
        assert bod.security_detail is not None
        assert bod.security_detail.symbol == "SPXW260330P6330"
        assert bod.special_order_detail is not None
        assert bod.special_order_detail.special_order_name == "COMPLEX_OPTION"

    def test_optional_special_order_detail(self):
        data = {
            "description": "Buy 10 AAPL",
            "qty": 10,
            "sellAllInd": False,
            "securityDetail": {"symbol": "AAPL"},
        }
        bod = BaseOrderDetail.model_validate(data)
        assert bod.special_order_detail is None


# ---------------------------------------------------------------------------
# PriceTypeDetail
# ---------------------------------------------------------------------------

class TestPriceTypeDetail:
    def test_parses_limit_order(self):
        ptd = PriceTypeDetail.model_validate({
            "priceTypeCode": "L",
            "priceTypeDesc": "Limit",
            "priceTypeDetailDesc": "Limit at $2.10",
            "limitPrice": 2.1,
            "pegInd": False,
        })
        assert ptd.price_type_code == "L"
        assert ptd.limit_price == pytest.approx(2.1)
        assert ptd.peg_ind is False

    def test_market_order_no_limit_price(self):
        ptd = PriceTypeDetail.model_validate({
            "priceTypeCode": "M",
            "priceTypeDesc": "Market",
            "priceTypeDetailDesc": "Market",
            "pegInd": False,
        })
        assert ptd.limit_price is None


# ---------------------------------------------------------------------------
# OptionDetail
# ---------------------------------------------------------------------------

class TestOptionDetail:
    def test_parses_option_detail(self):
        od = OptionDetail.model_validate({
            "contractSymbol": "SPXW",
            "contractType": "P",
            "expireDate": 1774843200,
            "strikePrice": 6330,
            "strategyCode": "CONDOR",
        })
        assert od.contract_symbol == "SPXW"
        assert od.contract_type == "P"
        assert od.expire_date == 1774843200
        assert od.strike_price == pytest.approx(6330)
        assert od.strategy_code == "CONDOR"

    def test_optional_strategy_code(self):
        od = OptionDetail.model_validate({
            "contractSymbol": "SPX",
            "contractType": "C",
            "expireDate": 1774843200,
            "strikePrice": 5000,
        })
        assert od.strategy_code is None


# ---------------------------------------------------------------------------
# TradableSecOrderDetail
# ---------------------------------------------------------------------------

class TestTradableSecOrderDetail:
    def test_parses_full_detail(self):
        tsd = TradableSecOrderDetail.model_validate(
            _make_order_detail()["tradableSecOrderDetail"]
        )
        assert tsd.tif_code == "D"
        assert tsd.tif_desc == "Day"
        assert tsd.mkt_route_code == "GLOBAL EXECUTION BROKERS L.P."
        assert tsd.market_session_code == "S"
        assert tsd.price_type_detail is not None
        assert tsd.price_type_detail.limit_price == pytest.approx(2.1)
        assert tsd.option_detail is not None
        assert tsd.option_detail.strategy_code == "CONDOR"

    def test_equity_order_no_option_detail(self):
        tsd = TradableSecOrderDetail.model_validate({
            "priceTypeDetail": {"priceTypeCode": "M", "priceTypeDesc": "Market", "pegInd": False},
            "tifCode": "D",
            "tifDesc": "Day",
            "mktRouteCode": "BEST",
            "marketSessionCode": "S",
        })
        assert tsd.option_detail is None


# ---------------------------------------------------------------------------
# OrderDetail
# ---------------------------------------------------------------------------

class TestOrderDetail:
    def test_parses_full_order_detail(self):
        od = OrderDetail.model_validate(_make_order_detail())
        assert od.acct_num == "Z21772945"
        assert od.status_detail is not None
        assert od.status_detail.status_code == "FILLED"
        assert od.id_detail is not None
        assert od.id_detail.conf_num == "C30QFHNX"
        assert od.base_order_detail is not None
        assert od.base_order_detail.order_action_code == "BP"
        assert od.tradable_sec_order_detail is not None
        assert od.tradable_sec_order_detail.tif_code == "D"

    def test_amount_detail_values(self):
        od = OrderDetail.model_validate(_make_order_detail())
        ad = od.status_detail.amount_detail
        assert ad.avg_exec_price == pytest.approx(2.96)
        assert ad.qty == pytest.approx(1)
        assert ad.commission == pytest.approx(0.65)
        assert ad.net == pytest.approx(296.67)


# ---------------------------------------------------------------------------
# AccountOrderSummary
# ---------------------------------------------------------------------------

class TestAccountOrderSummary:
    def test_parses_summary(self):
        s = AccountOrderSummary.model_validate(_make_acct_summary(
            acct_num="Z25485019",
            order_count=1,
            open_count=1,
            filled_count=0,
            cancelled_count=0,
        ))
        assert s.acct_num == "Z25485019"
        assert s.acct_level == "B"
        assert s.order_summary is not None
        assert s.order_summary.order_count == 1
        assert s.order_summary.open_count == 1
        assert s.order_summary.filled_count == 0
        assert s.order_summary.cancelled_count == 0

    def test_filled_account_summary(self):
        s = AccountOrderSummary.model_validate(_make_acct_summary(
            acct_num="Z21772945",
            order_count=23,
            open_count=0,
            filled_count=10,
            cancelled_count=13,
        ))
        assert s.order_summary.order_count == 23
        assert s.order_summary.filled_count == 10
        assert s.order_summary.cancelled_count == 13


# ---------------------------------------------------------------------------
# OrderStatusResponse — full integration parsing
# ---------------------------------------------------------------------------

class TestOrderStatusResponse:
    def test_parses_full_response(self):
        raw = _make_api_response()
        resp = OrderStatusResponse.from_api_response(raw)
        assert len(resp.account_summaries) == 1
        assert resp.account_summaries[0].acct_num == "Z25485019"
        assert len(resp.orders) == 1
        assert resp.orders[0].acct_num == "Z21772945"

    def test_multiple_accounts_and_orders(self):
        summaries = [
            _make_acct_summary("Z25485019", order_count=1, open_count=1),
            _make_acct_summary("Z21772945", order_count=23, open_count=0, filled_count=10, cancelled_count=13),
        ]
        orders = [
            _make_order_detail("Z21772945", "FILLED"),
            _make_order_detail("Z21772945", "CANCELLED"),
        ]
        raw = _make_api_response(summaries, orders)
        resp = OrderStatusResponse.from_api_response(raw)
        assert len(resp.account_summaries) == 2
        assert len(resp.orders) == 2
        assert resp.account_summaries[1].order_summary.filled_count == 10

    def test_empty_response_body(self):
        resp = OrderStatusResponse.from_api_response({})
        assert resp.account_summaries == []
        assert resp.orders == []

    def test_empty_order_details(self):
        raw = _make_api_response(order_details=[])
        resp = OrderStatusResponse.from_api_response(raw)
        assert resp.orders == []

    def test_order_security_detail(self):
        raw = _make_api_response()
        resp = OrderStatusResponse.from_api_response(raw)
        sec = resp.orders[0].base_order_detail.security_detail
        assert sec.symbol == "SPXW260330P6330"
        assert sec.cusip == "8550489BX"

    def test_option_detail_in_order(self):
        raw = _make_api_response()
        resp = OrderStatusResponse.from_api_response(raw)
        opt = resp.orders[0].tradable_sec_order_detail.option_detail
        assert opt.contract_symbol == "SPXW"
        assert opt.contract_type == "P"
        assert opt.strike_price == pytest.approx(6330)
        assert opt.strategy_code == "CONDOR"


# ---------------------------------------------------------------------------
# OrderStatusAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestOrderStatusAPI:
    @respx.mock
    def test_get_order_status_makes_correct_request(self):
        raw = _make_api_response()
        route = respx.post(_ORDER_STATUS_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = OrderStatusAPI(client)
        result = api.get_order_status(["Z25485019"])

        assert route.called
        assert isinstance(result, OrderStatusResponse)

    @respx.mock
    def test_request_body_shape(self):
        raw = _make_api_response()
        route = respx.post(_ORDER_STATUS_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = OrderStatusAPI(client)
        api.get_order_status(["Z25485019", "Z33359950"])

        sent_body = json.loads(route.calls[0].request.content)
        params = sent_body["request"]["parameter"]
        # Null filter fields present
        assert "fbOpenInd" in params
        assert params["fbOpenInd"] is None
        assert params["fvSymbol"] is None
        assert params["orderId"] is None
        # Account details
        acct_detail = params["acctDetails"]["acctDetail"]
        assert len(acct_detail) == 2
        assert acct_detail[0]["acctNum"] == "Z25485019"
        assert acct_detail[0]["accType"] is None
        assert acct_detail[1]["acctNum"] == "Z33359950"

    @respx.mock
    def test_single_account(self):
        raw = _make_api_response(
            acct_summaries=[_make_acct_summary("Z25485019")],
            order_details=[_make_order_detail("Z25485019", "OPEN")],
        )
        respx.post(_ORDER_STATUS_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = OrderStatusAPI(client)
        result = api.get_order_status(["Z25485019"])

        assert len(result.account_summaries) == 1
        assert result.account_summaries[0].acct_num == "Z25485019"

    @respx.mock
    def test_raises_on_http_error(self):
        respx.post(_ORDER_STATUS_URL).mock(
            return_value=httpx.Response(401)
        )
        client = httpx.Client()
        api = OrderStatusAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_order_status(["Z25485019"])

    @respx.mock
    def test_empty_order_list_response(self):
        raw = _make_api_response(order_details=[])
        respx.post(_ORDER_STATUS_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = OrderStatusAPI(client)
        result = api.get_order_status(["Z25485019"])
        assert result.orders == []
