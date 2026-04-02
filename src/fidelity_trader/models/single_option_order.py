"""Pydantic models for single-leg option order preview/place request and response."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class SingleOptionOrderRequest(BaseModel):
    """Parameters for a single-leg option order preview or place request.

    Mirrors the ``request.parameter`` shape observed in captured Trader+ traffic
    for ``POST /ftgw/dp/orderentry/option/preview/v2``.

    orderActionCode values:
        - ``"BC"`` -- Buy Call
        - ``"BP"`` -- Buy Put
        - ``"SC"`` -- Sell Call
        - ``"SP"`` -- Sell Put
    """
    model_config = {"populate_by_name": True}

    acct_num: str = Field(alias="acctNum")
    symbol: str
    order_action_code: str = Field(alias="orderActionCode")  # "BC", "BP", "SC", "SP"
    acct_type_code: str = Field(default="M", alias="acctTypeCode")  # "M"=Margin, "C"=Cash
    qty: int
    qty_type_code: str = Field(default="S", alias="qtyTypeCode")
    tif_code: str = Field(default="D", alias="tifCode")  # "D"=Day, "G"=GTC
    price_type_code: str = Field(default="M", alias="priceTypeCode")  # "M"=Market, "L"=Limit
    limit_price: Optional[float] = Field(default=None, alias="limitPrice")
    mkt_route_code: str = Field(default="", alias="mktRouteCode")
    destination_code: str = Field(default="", alias="destinationCode")

    def to_preview_body(self) -> dict:
        """Build the JSON body for the option preview endpoint."""
        return {
            "request": {
                "parameter": {
                    "baseOrderDetail": {
                        "orderActionCode": self.order_action_code,
                        "acctTypeCode": self.acct_type_code,
                        "qty": self.qty,
                        "qtyTypeCode": self.qty_type_code,
                        "securityDetail": {"symbol": self.symbol},
                        "specificShrDetail": {},
                    },
                    "tradableSecOrderDetail": {
                        "tifCode": self.tif_code,
                        "priceTypeDetail": self._price_type_detail_dict(),
                        "mktRouteCode": self.mkt_route_code,
                        "destinationCode": self.destination_code,
                        "optionDetail": {"type": "O"},
                    },
                    "priceDetail": {},
                    "acctNum": self.acct_num,
                }
            }
        }

    def to_place_body(self, conf_num: str) -> dict:
        """Build the JSON body for the option place endpoint, injecting the confNum."""
        return {
            "request": {
                "parameter": {
                    "tradableSecOrderDetail": {
                        "tifCode": self.tif_code,
                        "priceTypeDetail": self._price_type_detail_dict(),
                        "mktRouteCode": self.mkt_route_code,
                        "destinationCode": self.destination_code,
                        "optionDetail": {"type": "O"},
                    },
                    "priceDetail": {},
                    "acctNum": self.acct_num,
                    "baseOrderDetail": {
                        "orderActionCode": self.order_action_code,
                        "acctTypeCode": self.acct_type_code,
                        "qty": self.qty,
                        "qtyTypeCode": self.qty_type_code,
                        "securityDetail": {"symbol": self.symbol},
                        "specificShrDetail": {},
                        "confNum": conf_num,
                    },
                    "previewInd": False,
                    "confInd": False,
                }
            }
        }

    def _price_type_detail_dict(self) -> dict:
        d: dict[str, Any] = {"priceTypeCode": self.price_type_code}
        if self.limit_price is not None:
            d["limitPrice"] = self.limit_price
        return d


# ---------------------------------------------------------------------------
# Response sub-models -- shared by preview and place
# ---------------------------------------------------------------------------

class SingleOptionRespPriceDetail(BaseModel):
    """Price detail within an option order confirm response."""
    model_config = {"populate_by_name": True}

    price: Optional[float] = None
    price_date_time: Optional[int] = Field(default=None, alias="priceDateTime")
    bid_price: Optional[float] = Field(default=None, alias="bidPrice")
    ask_price: Optional[float] = Field(default=None, alias="askPrice")


class SingleOptionEstCommissionDetail(BaseModel):
    """Estimated commission detail within an option order confirm response."""
    model_config = {"populate_by_name": True}

    est_commission: Optional[float] = Field(default=None, alias="estCommission")
    type_code: Optional[str] = Field(default=None, alias="typeCode")


class SingleOptionRespPriceTypeDetail(BaseModel):
    """Price type detail in the response order detail."""
    model_config = {"populate_by_name": True}

    price_type_code: Optional[str] = Field(default=None, alias="priceTypeCode")
    price_type_desc: Optional[str] = Field(default=None, alias="priceTypeDesc")
    limit_price: Optional[float] = Field(default=None, alias="limitPrice")


class SingleOptionRespOptionDetail(BaseModel):
    """Option detail in the response tradable sec order detail."""
    model_config = {"populate_by_name": True}

    type: Optional[str] = None


class SingleOptionRespTradableSecOrderDetail(BaseModel):
    """Tradable security order detail within a response order detail."""
    model_config = {"populate_by_name": True}

    price_type_detail: Optional[SingleOptionRespPriceTypeDetail] = Field(
        default=None, alias="priceTypeDetail"
    )
    option_detail: Optional[SingleOptionRespOptionDetail] = Field(
        default=None, alias="optionDetail"
    )
    tif_code: Optional[str] = Field(default=None, alias="tifCode")
    mkt_route_code: Optional[str] = Field(default=None, alias="mktRouteCode")
    destination_code: Optional[str] = Field(default=None, alias="destinationCode")


class SingleOptionRespSecurityDetail(BaseModel):
    """Security detail within the response order detail."""
    model_config = {"populate_by_name": True}

    symbol: Optional[str] = None
    cusip: Optional[str] = None
    sec_desc: Optional[str] = Field(default=None, alias="secDesc")


class SingleOptionRespSpecificShrDetail(BaseModel):
    """Specific share detail within the response base order detail."""
    model_config = {"populate_by_name": True}

    tax_lot_details: Optional[list] = Field(default=None, alias="taxLotDetails")


class SingleOptionRespBaseOrderDetail(BaseModel):
    """Base order detail within the response order detail."""
    model_config = {"populate_by_name": True}

    order_action_code: Optional[str] = Field(default=None, alias="orderActionCode")
    action_code_desc: Optional[str] = Field(default=None, alias="actionCodeDesc")
    qty: Optional[int] = None
    qty_type_code: Optional[str] = Field(default=None, alias="qtyTypeCode")
    val_of_order: Optional[float] = Field(default=None, alias="valOfOrder")
    security_detail: Optional[SingleOptionRespSecurityDetail] = Field(
        default=None, alias="securityDetail"
    )
    specific_shr_detail: Optional[SingleOptionRespSpecificShrDetail] = Field(
        default=None, alias="specificShrDetail"
    )


class SingleOptionRespOrderDetail(BaseModel):
    """Full order detail nested inside the confirm response."""
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    base_order_detail: Optional[SingleOptionRespBaseOrderDetail] = Field(
        default=None, alias="baseOrderDetail"
    )
    tradable_sec_order_detail: Optional[SingleOptionRespTradableSecOrderDetail] = Field(
        default=None, alias="tradableSecOrderDetail"
    )


class SingleOptionOrderConfirmDetail(BaseModel):
    """The ``orderConfirmDetail`` object returned by both preview and place."""
    model_config = {"populate_by_name": True}

    resp_type_code: Optional[str] = Field(default=None, alias="respTypeCode")
    conf_num: Optional[str] = Field(default=None, alias="confNum")
    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    acct_type_code: Optional[str] = Field(default=None, alias="acctTypeCode")
    price_detail: Optional[SingleOptionRespPriceDetail] = Field(
        default=None, alias="priceDetail"
    )
    est_commission_detail: Optional[SingleOptionEstCommissionDetail] = Field(
        default=None, alias="estCommissionDetail"
    )
    net_amount: Optional[float] = Field(default=None, alias="netAmount")
    net_proceeds_inclusive: Optional[float] = Field(
        default=None, alias="netProceedsInclusive"
    )
    order_detail: Optional[SingleOptionRespOrderDetail] = Field(
        default=None, alias="orderDetail"
    )


# ---------------------------------------------------------------------------
# Top-level response models
# ---------------------------------------------------------------------------

class SingleOptionPreviewResponse(BaseModel):
    """Top-level response for ``POST /option/preview/v2``."""
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    order_confirm_detail: Optional[SingleOptionOrderConfirmDetail] = Field(
        default=None, alias="orderConfirmDetail"
    )

    @classmethod
    def from_api_response(cls, data: dict) -> "SingleOptionPreviewResponse":
        """Parse the raw API JSON: ``{"preview": {...}}``."""
        inner = data.get("preview") or {}
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


class SingleOptionPlaceResponse(BaseModel):
    """Top-level response for ``POST /option/place/v2``."""
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    order_confirm_detail: Optional[SingleOptionOrderConfirmDetail] = Field(
        default=None, alias="orderConfirmDetail"
    )

    @classmethod
    def from_api_response(cls, data: dict) -> "SingleOptionPlaceResponse":
        """Parse the raw API JSON: ``{"place": {...}}``."""
        inner = data.get("place") or {}
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
