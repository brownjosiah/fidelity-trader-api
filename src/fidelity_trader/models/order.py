from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Amount / Status sub-models
# ---------------------------------------------------------------------------

class OrderAmountDetail(BaseModel):
    model_config = {"populate_by_name": True}

    qty_remaining: Optional[float] = Field(default=None, alias="qtyRemaining")
    avg_exec_price: Optional[float] = Field(default=None, alias="avgExecPrice")
    qty: Optional[float] = None
    qty_exec: Optional[float] = Field(default=None, alias="qtyExec")
    commission: Optional[float] = None
    gross: Optional[float] = None
    net: Optional[float] = None


class OrderStatusDetail(BaseModel):
    model_config = {"populate_by_name": True}

    status_code: Optional[str] = Field(default=None, alias="statusCode")
    status_desc: Optional[str] = Field(default=None, alias="statusDesc")
    cancelable_ind: bool = Field(default=False, alias="cancelableInd")
    replaceable_ind: bool = Field(default=False, alias="replaceableInd")
    amount_detail: Optional[OrderAmountDetail] = Field(default=None, alias="amountDetail")


class OrderIdDetail(BaseModel):
    model_config = {"populate_by_name": True}

    conf_num: Optional[str] = Field(default=None, alias="confNum")
    system_order_id: Optional[str] = Field(default=None, alias="systemOrderId")
    order_source: Optional[str] = Field(default=None, alias="orderSource")


# ---------------------------------------------------------------------------
# Security / Base order sub-models
# ---------------------------------------------------------------------------

class SecurityDetail(BaseModel):
    model_config = {"populate_by_name": True}

    cusip: Optional[str] = None
    symbol: Optional[str] = None
    sec_desc: Optional[str] = Field(default=None, alias="secDesc")
    sec_type: Optional[str] = Field(default=None, alias="secType")


class SpecialOrderDetail(BaseModel):
    model_config = {"populate_by_name": True}

    special_order_code: Optional[str] = Field(default=None, alias="specialOrderCode")
    special_order_name: Optional[str] = Field(default=None, alias="specialOrderName")


class BaseOrderDetail(BaseModel):
    model_config = {"populate_by_name": True}

    description: Optional[str] = None
    entry_datetime: Optional[int] = Field(default=None, alias="entryDatetime")
    order_action_code: Optional[str] = Field(default=None, alias="orderActionCode")
    action_code_desc: Optional[str] = Field(default=None, alias="actionCodeDesc")
    qty: Optional[float] = None
    sell_all_ind: bool = Field(default=False, alias="sellAllInd")
    acct_type_desc: Optional[str] = Field(default=None, alias="acctTypeDesc")
    orig_qty: Optional[float] = Field(default=None, alias="origQty")
    security_detail: Optional[SecurityDetail] = Field(default=None, alias="securityDetail")
    special_order_detail: Optional[SpecialOrderDetail] = Field(default=None, alias="specialOrderDetail")


# ---------------------------------------------------------------------------
# Tradable security / price / option sub-models
# ---------------------------------------------------------------------------

class PriceTypeDetail(BaseModel):
    model_config = {"populate_by_name": True}

    price_type_code: Optional[str] = Field(default=None, alias="priceTypeCode")
    price_type_desc: Optional[str] = Field(default=None, alias="priceTypeDesc")
    price_type_detail_desc: Optional[str] = Field(default=None, alias="priceTypeDetailDesc")
    limit_price: Optional[float] = Field(default=None, alias="limitPrice")
    peg_ind: bool = Field(default=False, alias="pegInd")


class OptionDetail(BaseModel):
    model_config = {"populate_by_name": True}

    contract_symbol: Optional[str] = Field(default=None, alias="contractSymbol")
    contract_type: Optional[str] = Field(default=None, alias="contractType")
    expire_date: Optional[int] = Field(default=None, alias="expireDate")
    strike_price: Optional[float] = Field(default=None, alias="strikePrice")
    strategy_code: Optional[str] = Field(default=None, alias="strategyCode")


class TradableSecOrderDetail(BaseModel):
    model_config = {"populate_by_name": True}

    price_type_detail: Optional[PriceTypeDetail] = Field(default=None, alias="priceTypeDetail")
    option_detail: Optional[OptionDetail] = Field(default=None, alias="optionDetail")
    tif_code: Optional[str] = Field(default=None, alias="tifCode")
    tif_desc: Optional[str] = Field(default=None, alias="tifDesc")
    mkt_route_code: Optional[str] = Field(default=None, alias="mktRouteCode")
    market_session_code: Optional[str] = Field(default=None, alias="marketSessionCode")


# ---------------------------------------------------------------------------
# Top-level order detail
# ---------------------------------------------------------------------------

class OrderDetail(BaseModel):
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    status_detail: Optional[OrderStatusDetail] = Field(default=None, alias="statusDetail")
    id_detail: Optional[OrderIdDetail] = Field(default=None, alias="idDetail")
    base_order_detail: Optional[BaseOrderDetail] = Field(default=None, alias="baseOrderDetail")
    tradable_sec_order_detail: Optional[TradableSecOrderDetail] = Field(
        default=None, alias="tradableSecOrderDetail"
    )


# ---------------------------------------------------------------------------
# Account-level summary
# ---------------------------------------------------------------------------

class OrderSummary(BaseModel):
    model_config = {"populate_by_name": True}

    order_count: int = Field(default=0, alias="orderCount")
    open_count: int = Field(default=0, alias="openCount")
    filled_count: int = Field(default=0, alias="filledCount")
    cancelled_count: int = Field(default=0, alias="cancelledCount")


class AccountOrderSummary(BaseModel):
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    acct_level: Optional[str] = Field(default=None, alias="acctLevel")
    order_summary: Optional[OrderSummary] = Field(default=None, alias="orderSummary")


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------

class OrderStatusResponse(BaseModel):
    model_config = {"populate_by_name": True}

    account_summaries: list[AccountOrderSummary] = Field(default_factory=list)
    orders: list[OrderDetail] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "OrderStatusResponse":
        """Parse the full API JSON response into an OrderStatusResponse.

        Expected shape::

            {
                "order": {
                    "acctDetails": {
                        "acctDetail": [...]
                    },
                    "orderDetails": {
                        "orderDetail": [...]
                    }
                }
            }
        """
        order = data.get("order") or {}
        acct_list = (order.get("acctDetails") or {}).get("acctDetail") or []
        order_list = (order.get("orderDetails") or {}).get("orderDetail") or []
        return cls(
            account_summaries=[AccountOrderSummary.model_validate(a) for a in acct_list],
            orders=[OrderDetail.model_validate(o) for o in order_list],
        )
