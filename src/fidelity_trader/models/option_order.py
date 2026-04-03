"""Pydantic models for multi-leg option order preview/place request and response."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class OptionLegPriceDetail(BaseModel):
    """Price detail for a single option leg in the request."""
    model_config = {"populate_by_name": True}

    price: float
    price_date_time: int = Field(alias="priceDateTime")
    bid_price: float = Field(alias="bidPrice")
    ask_price: float = Field(alias="askPrice")

    def to_api_dict(self) -> dict:
        return {
            "price": self.price,
            "priceDateTime": self.price_date_time,
            "bidPrice": self.bid_price,
            "askPrice": self.ask_price,
        }


class OptionLegSecurityDetail(BaseModel):
    """Security detail for a single option leg in the request."""
    model_config = {"populate_by_name": True}

    symbol_cusip_code: str = Field(default="S", alias="symbolCUSIPCode")
    symbol: str

    def to_api_dict(self) -> dict:
        return {
            "symbolCUSIPCode": self.symbol_cusip_code,
            "symbol": self.symbol,
        }


class OptionLeg(BaseModel):
    """A single leg within a multi-leg option order.

    orderActionCode values:
        - ``"BO"`` — Buy to Open
        - ``"SO"`` — Sell to Open
        - ``"BC"`` — Buy to Close
        - ``"SC"`` — Sell to Close
    """
    model_config = {"populate_by_name": True}

    type: str = Field(default="O")
    order_action_code: str = Field(alias="orderActionCode")
    qty: int
    security_detail: OptionLegSecurityDetail = Field(alias="securityDetail")
    price_detail: OptionLegPriceDetail = Field(alias="priceDetail")

    def to_api_dict(self) -> dict:
        return {
            "type": self.type,
            "orderActionCode": self.order_action_code,
            "qty": self.qty,
            "securityDetail": self.security_detail.to_api_dict(),
            "priceDetail": self.price_detail.to_api_dict(),
        }


class MultiLegOptionOrderRequest(BaseModel):
    """Parameters for a multi-leg option order preview or place request.

    Mirrors the ``parameters`` shape observed in captured Trader+ traffic for
    ``POST /ftgw/dp/orderentry/multilegoption/preview/v1``.

    strategyType values:
        - ``"CU"`` — Custom

    dbCrEvenCode values:
        - ``"DB"`` — Debit
        - ``"CR"`` — Credit
    """
    model_config = {"populate_by_name": True}

    acct_num: str = Field(alias="acctNum")
    legs: List[OptionLeg]
    net_amount: float = Field(alias="netAmount")
    tif_code: str = Field(default="D", alias="tifCode")
    db_cr_even_code: str = Field(default="DB", alias="dbCrEvenCode")
    destination_code: str = Field(default="", alias="destinationCode")
    strategy_type: str = Field(default="CU", alias="strategyType")
    acct_type_code: str = Field(default="M", alias="acctTypeCode")
    exp_date_default_ind: bool = Field(default=True, alias="expDateDefaultInd")
    exp_time_default_ind: bool = Field(default=True, alias="expTimeDefaultInd")

    def to_preview_body(self) -> dict:
        """Build the JSON body for the multi-leg option preview endpoint."""
        return {
            "parameters": {
                "acctNum": self.acct_num,
                "tradableSecOrderDetail": {
                    "tifCode": self.tif_code,
                    "dbCrEvenCode": self.db_cr_even_code,
                    "netAmount": self.net_amount,
                    "destinationCode": self.destination_code,
                },
                "expDateDefaultInd": self.exp_date_default_ind,
                "expTimeDefaultInd": self.exp_time_default_ind,
                "baseOrderDetail": {
                    "acctTypeCode": self.acct_type_code,
                    "reqTypeCode": "N",
                    "optionDetail": {
                        "strategyType": self.strategy_type,
                        "numOfLegs": len(self.legs),
                        "complexOrderDetails": [leg.to_api_dict() for leg in self.legs],
                    },
                },
            }
        }

    def to_place_body(self, conf_num: str) -> dict:
        """Build the JSON body for the multi-leg option place endpoint."""
        return {
            "parameters": {
                "acctNum": self.acct_num,
                "tradableSecOrderDetail": {
                    "tifCode": self.tif_code,
                    "dbCrEvenCode": self.db_cr_even_code,
                    "netAmount": self.net_amount,
                    "destinationCode": self.destination_code,
                },
                "expDateDefaultInd": self.exp_date_default_ind,
                "expTimeDefaultInd": self.exp_time_default_ind,
                "baseOrderDetail": {
                    "acctTypeCode": self.acct_type_code,
                    "reqTypeCode": "P",
                    "confNum": conf_num,
                    "optionDetail": {
                        "strategyType": self.strategy_type,
                        "numOfLegs": len(self.legs),
                        "complexOrderDetails": [leg.to_api_dict() for leg in self.legs],
                    },
                },
            }
        }


# ---------------------------------------------------------------------------
# Response sub-models — shared by preview and place
# ---------------------------------------------------------------------------

class OptionRespSecurityDetail(BaseModel):
    """Security detail within the response leg detail."""
    model_config = {"populate_by_name": True}

    symbol: Optional[str] = None
    etf_ind: Optional[bool] = Field(default=None, alias="etfInd")


class OptionRespPriceDetail(BaseModel):
    """Price detail within a response leg."""
    model_config = {"populate_by_name": True}

    price: Optional[float] = None
    bid_price: Optional[float] = Field(default=None, alias="bidPrice")
    ask_price: Optional[float] = Field(default=None, alias="askPrice")


class OptionRespEstCommissionDetail(BaseModel):
    """Estimated commission detail within a response leg."""
    model_config = {"populate_by_name": True}

    est_commission: Optional[float] = Field(default=None, alias="estCommission")


class OptionRespLeg(BaseModel):
    """A single leg within the response complexOrderDetails."""
    model_config = {"populate_by_name": True}

    order_action_code: Optional[str] = Field(default=None, alias="orderActionCode")
    type: Optional[str] = None
    qty: Optional[int] = None
    security_detail: Optional[OptionRespSecurityDetail] = Field(
        default=None, alias="securityDetail"
    )
    est_commission_detail: Optional[OptionRespEstCommissionDetail] = Field(
        default=None, alias="estCommissionDetail"
    )
    price_detail: Optional[OptionRespPriceDetail] = Field(
        default=None, alias="priceDetail"
    )


class OptionRespComplexDetail(BaseModel):
    """The complexOrderDetails block within the response optionDetail."""
    model_config = {"populate_by_name": True}

    complex_type: Optional[str] = Field(default=None, alias="complexType")
    num_of_legs: Optional[int] = Field(default=None, alias="numOfLegs")
    complex_order_details: Optional[List[OptionRespLeg]] = Field(
        default=None, alias="complexOrderDetails"
    )


class OptionRespBaseOrderDetail(BaseModel):
    """Base order detail within the response orderDetail."""
    model_config = {"populate_by_name": True}

    option_detail: Optional[OptionRespComplexDetail] = Field(
        default=None, alias="optionDetail"
    )


class OptionRespPriceTypeDetail(BaseModel):
    """Price type detail in the response tradableSecOrderDetail."""
    model_config = {"populate_by_name": True}

    price_type_code: Optional[str] = Field(default=None, alias="priceTypeCode")


class OptionRespTradableSecOrderDetail(BaseModel):
    """Tradable security order detail in the response orderDetail."""
    model_config = {"populate_by_name": True}

    tif_code: Optional[str] = Field(default=None, alias="tifCode")
    price_type_detail: Optional[OptionRespPriceTypeDetail] = Field(
        default=None, alias="priceTypeDetail"
    )
    db_cr_even_code: Optional[str] = Field(default=None, alias="dbCrEvenCode")
    aon_code: Optional[bool] = Field(default=None, alias="aonCode")
    destination_code: Optional[str] = Field(default=None, alias="destinationCode")


class OptionRespOrderDetail(BaseModel):
    """Full orderDetail nested inside the confirm response."""
    model_config = {"populate_by_name": True}

    base_order_detail: Optional[OptionRespBaseOrderDetail] = Field(
        default=None, alias="baseOrderDetail"
    )
    tradable_sec_order_detail: Optional[OptionRespTradableSecOrderDetail] = Field(
        default=None, alias="tradableSecOrderDetail"
    )


class OptionSysMsg(BaseModel):
    """A single system message from the API response."""
    model_config = {"populate_by_name": True}

    message: Optional[str] = None
    detail: Optional[str] = None
    source: Optional[str] = None
    code: Optional[str] = None
    type: Optional[str] = None


class OptionSysMsgs(BaseModel):
    """Container for system messages in the response."""
    model_config = {"populate_by_name": True}

    sys_msg: Optional[List[OptionSysMsg]] = Field(default=None, alias="sysMsg")


class MultiLegOptionOrderConfirmDetail(BaseModel):
    """The ``orderConfirmDetail`` object returned by both preview and place."""
    model_config = {"populate_by_name": True}

    resp_type_code: Optional[str] = Field(default=None, alias="respTypeCode")
    conf_num: Optional[str] = Field(default=None, alias="confNum")
    acct_type_code: Optional[str] = Field(default=None, alias="acctTypeCode")
    net_amount: Optional[float] = Field(default=None, alias="netAmount")
    net_ask: Optional[float] = Field(default=None, alias="netAsk")
    net_bid: Optional[float] = Field(default=None, alias="netBid")
    mid_point: Optional[float] = Field(default=None, alias="midPoint")
    gcd: Optional[int] = None
    final_total_val_of_order: Optional[float] = Field(
        default=None, alias="finalTotalValOfOrder"
    )
    total_est_commission: Optional[float] = Field(
        default=None, alias="totalEstCommission"
    )
    subtotal_val_of_order: Optional[float] = Field(
        default=None, alias="subtotalValOfOrder"
    )
    order_detail: Optional[OptionRespOrderDetail] = Field(
        default=None, alias="orderDetail"
    )


# ---------------------------------------------------------------------------
# Top-level response models
# ---------------------------------------------------------------------------

class MultiLegOptionPreviewResponse(BaseModel):
    """Top-level response for ``POST /multilegoption/preview/v1``."""
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    sys_msgs: Optional[OptionSysMsgs] = Field(default=None, alias="sysMsgs")
    order_confirm_detail: Optional[MultiLegOptionOrderConfirmDetail] = Field(
        default=None, alias="orderConfirmDetail"
    )

    @classmethod
    def from_api_response(cls, data: dict) -> "MultiLegOptionPreviewResponse":
        """Parse the raw API JSON: ``{"multiLegOptionResponse": {...}}``."""
        inner = data.get("multiLegOptionResponse") or {}
        return cls.model_validate(inner)

    @property
    def conf_num(self) -> Optional[str]:
        """Convenience accessor for the confirmation number."""
        if self.order_confirm_detail:
            return self.order_confirm_detail.conf_num
        return None

    @property
    def is_validated(self) -> bool:
        """True when ``respTypeCode`` is ``"V"`` (preview validated)."""
        if self.order_confirm_detail:
            return self.order_confirm_detail.resp_type_code == "V"
        return False


class MultiLegOptionPlaceResponse(BaseModel):
    """Top-level response for ``POST /multilegoption/place/v1``."""
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    sys_msgs: Optional[OptionSysMsgs] = Field(default=None, alias="sysMsgs")
    order_confirm_detail: Optional[MultiLegOptionOrderConfirmDetail] = Field(
        default=None, alias="orderConfirmDetail"
    )

    @classmethod
    def from_api_response(cls, data: dict) -> "MultiLegOptionPlaceResponse":
        """Parse the raw API JSON: ``{"multiLegOptionResponse": {...}}``."""
        inner = data.get("multiLegOptionResponse") or {}
        return cls.model_validate(inner)

    @property
    def conf_num(self) -> Optional[str]:
        """Convenience accessor for the confirmation number."""
        if self.order_confirm_detail:
            return self.order_confirm_detail.conf_num
        return None

    @property
    def is_accepted(self) -> bool:
        """True when ``respTypeCode`` is ``"A"`` (order accepted)."""
        if self.order_confirm_detail:
            return self.order_confirm_detail.resp_type_code == "A"
        return False
