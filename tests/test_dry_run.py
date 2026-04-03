"""Tests for the dry-run safety mechanism on order placement."""

import httpx
import pytest
import respx

from fidelity_trader import FidelityClient, DryRunError, FidelityError
from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.equity_order import EquityOrderRequest
from fidelity_trader.models.single_option_order import SingleOptionOrderRequest
from fidelity_trader.models.option_order import (
    MultiLegOptionOrderRequest,
    OptionLeg,
    OptionLegSecurityDetail,
    OptionLegPriceDetail,
)
from fidelity_trader.models.cancel_replace import CancelReplaceRequest
from fidelity_trader.models.conditional_order import (
    ConditionalOrderRequest,
    ConditionalOrderLeg,
)


# ---------------------------------------------------------------------------
# Fixtures — minimal request objects for each order type
# ---------------------------------------------------------------------------

@pytest.fixture
def equity_order():
    return EquityOrderRequest(
        acctNum="Z12345678",
        symbol="AAPL",
        orderActionCode="B",
        qty=10,
    )


@pytest.fixture
def single_option_order():
    return SingleOptionOrderRequest(
        acctNum="Z12345678",
        symbol="AAPL250418C00170000",
        orderActionCode="BC",
        qty=1,
    )


@pytest.fixture
def multi_leg_order():
    return MultiLegOptionOrderRequest(
        acctNum="Z12345678",
        netAmount=1.50,
        legs=[
            OptionLeg(
                orderActionCode="BO",
                qty=1,
                securityDetail=OptionLegSecurityDetail(symbol="AAPL250418C00170000"),
                priceDetail=OptionLegPriceDetail(
                    price=3.50, priceDateTime=0, bidPrice=3.40, askPrice=3.60
                ),
            ),
            OptionLeg(
                orderActionCode="SO",
                qty=1,
                securityDetail=OptionLegSecurityDetail(symbol="AAPL250418C00175000"),
                priceDetail=OptionLegPriceDetail(
                    price=2.00, priceDateTime=0, bidPrice=1.90, askPrice=2.10
                ),
            ),
        ],
    )


@pytest.fixture
def cancel_replace_order():
    return CancelReplaceRequest(
        acctNum="Z12345678",
        orderNumOrig="ABC123",
        symbol="AAPL",
        orderActionCode="B",
        qty=10,
        limitPrice=150.00,
    )


@pytest.fixture
def conditional_order():
    return ConditionalOrderRequest(
        condOrderTypeCode="OTOCO",
        acctNum="Z12345678",
        legs=[
            ConditionalOrderLeg(
                orderActionCode="B",
                qty=10,
                symbol="AAPL",
                priceTypeCode="L",
                limitPrice=150.00,
            ),
            ConditionalOrderLeg(
                orderActionCode="S",
                qty=10,
                symbol="AAPL",
                priceTypeCode="S",
                stopPrice=140.00,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Default mode tests
# ---------------------------------------------------------------------------

def test_dry_run_is_default():
    client = FidelityClient()
    try:
        assert client._live_trading is False
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Dry-run blocks place methods
# ---------------------------------------------------------------------------

def test_dry_run_blocks_equity_place(equity_order):
    with FidelityClient() as client:
        with pytest.raises(DryRunError):
            client.equity_orders.place_order(equity_order, conf_num="CONF1")


def test_dry_run_blocks_single_option_place(single_option_order):
    with FidelityClient() as client:
        with pytest.raises(DryRunError):
            client.single_option_orders.place_order(single_option_order, conf_num="CONF1")


def test_dry_run_blocks_multi_leg_place(multi_leg_order):
    with FidelityClient() as client:
        with pytest.raises(DryRunError):
            client.option_orders.place_order(multi_leg_order, conf_num="CONF1")


def test_dry_run_blocks_cancel_replace_place(cancel_replace_order):
    with FidelityClient() as client:
        with pytest.raises(DryRunError):
            client.cancel_replace.place_order(cancel_replace_order, conf_num="CONF1")


def test_dry_run_blocks_conditional_place(conditional_order):
    with FidelityClient() as client:
        with pytest.raises(DryRunError):
            client.conditional_orders.place_order(conditional_order, conf_nums=["CONF1"])


# ---------------------------------------------------------------------------
# Preview methods always work (dry-run does not block)
# ---------------------------------------------------------------------------

@respx.mock
def test_dry_run_allows_preview(equity_order):
    """Preview methods should work even in dry-run mode."""
    respx.post(f"{DPSERVICE_URL}/ftgw/dp/orderentry/equity/preview/v1").mock(
        return_value=httpx.Response(
            200,
            json={
                "preview": {
                    "acctNum": "Z12345678",
                    "orderConfirmDetail": {
                        "respTypeCode": "V",
                        "confNum": "PREVIEW123",
                    },
                }
            },
        )
    )
    with FidelityClient() as client:
        result = client.equity_orders.preview_order(equity_order)
        assert result.conf_num == "PREVIEW123"


# ---------------------------------------------------------------------------
# Live trading flag allows place
# ---------------------------------------------------------------------------

@respx.mock
def test_live_trading_flag_allows_place(equity_order):
    """When live_trading=True, place methods should proceed normally."""
    respx.post(f"{DPSERVICE_URL}/ftgw/dp/orderentry/equity/place/v1").mock(
        return_value=httpx.Response(
            200,
            json={
                "place": {
                    "acctNum": "Z12345678",
                    "orderConfirmDetail": {
                        "respTypeCode": "A",
                        "confNum": "PLACE123",
                    },
                }
            },
        )
    )
    with FidelityClient(live_trading=True) as client:
        result = client.equity_orders.place_order(equity_order, conf_num="CONF1")
        assert result.is_accepted
        assert result.conf_num == "PLACE123"


# ---------------------------------------------------------------------------
# Environment variable
# ---------------------------------------------------------------------------

def test_env_var_enables_live_trading(monkeypatch):
    monkeypatch.setenv("FIDELITY_LIVE_TRADING", "true")
    client = FidelityClient()
    try:
        assert client._live_trading is True
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Cancel is NOT gated
# ---------------------------------------------------------------------------

@respx.mock
def test_cancel_not_gated():
    """Cancel should work in dry-run mode (never gated)."""
    respx.post(f"{DPSERVICE_URL}/ftgw/dp/orderentry/cancel/place/v1").mock(
        return_value=httpx.Response(
            200,
            json={
                "place": {
                    "cancelConfirmDetail": [
                        {
                            "respTypeCode": "A",
                            "confNum": "CANCEL1",
                            "acctNum": "Z12345678",
                        }
                    ]
                }
            },
        )
    )
    with FidelityClient() as client:
        result = client.cancel_order.cancel_order(
            conf_num="ORIG1", acct_num="Z12345678", action_code="B"
        )
        assert result.is_accepted


# ---------------------------------------------------------------------------
# DryRunError hierarchy and message
# ---------------------------------------------------------------------------

def test_dry_run_error_is_fidelity_error():
    assert issubclass(DryRunError, FidelityError)
    err = DryRunError("test")
    assert isinstance(err, FidelityError)


def test_dry_run_error_message(equity_order):
    with FidelityClient() as client:
        with pytest.raises(DryRunError, match="dry-run mode is active"):
            client.equity_orders.place_order(equity_order, conf_num="CONF1")
