"""Pydantic models for equity order preview/place request and response."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class EquitySecurityDetail(BaseModel):
    """Security detail used in the order request body."""
    model_config = {"populate_by_name": True}

    symbol: str


class EquityPriceTypeDetail(BaseModel):
    """Price type detail within a tradable security order detail."""
    model_config = {"populate_by_name": True}

    price_type_code: str = Field(alias="priceTypeCode")
    limit_price: Optional[float] = Field(default=None, alias="limitPrice")

    def to_api_dict(self) -> dict:
        d: dict[str, Any] = {"priceTypeCode": self.price_type_code}
        if self.limit_price is not None:
            d["limitPrice"] = self.limit_price
        return d


class EquityOrderRequest(BaseModel):
    """Parameters for an equity order preview or place request.

    Mirrors the ``request.parameter`` shape observed in captured Trader+ traffic.
    """
    model_config = {"populate_by_name": True}

    acct_num: str = Field(alias="acctNum")
    symbol: str
    order_action_code: str = Field(alias="orderActionCode")  # "B" or "S"
    acct_type_code: str = Field(default="M", alias="acctTypeCode")  # "M"=Margin, "C"=Cash
    qty: float
    qty_type_code: str = Field(default="S", alias="qtyTypeCode")  # "S"=Shares
    tif_code: str = Field(default="D", alias="tifCode")  # "D"=Day, "G"=GTC
    price_type_code: str = Field(default="L", alias="priceTypeCode")  # "L"=Limit, "M"=Market
    limit_price: Optional[float] = Field(default=None, alias="limitPrice")
    mkt_route_code: str = Field(default="", alias="mktRouteCode")

    def to_preview_body(self) -> dict:
        """Build the JSON body for the preview endpoint."""
        return {
            "request": {
                "parameter": {
                    "baseOrderDetail": {
                        "orderActionCode": self.order_action_code,
                        "acctTypeCode": self.acct_type_code,
                        "qty": self.qty,
                        "qtyTypeCode": self.qty_type_code,
                        "securityDetail": {"symbol": self.symbol},
                    },
                    "tradableSecOrderDetail": {
                        "tifCode": self.tif_code,
                        "priceTypeDetail": self._price_type_detail_dict(),
                        "mktRouteCode": self.mkt_route_code,
                    },
                    "priceDetail": {},
                    "acctNum": self.acct_num,
                }
            }
        }

    def to_place_body(self, conf_num: str) -> dict:
        """Build the JSON body for the place endpoint, injecting the confNum."""
        return {
            "request": {
                "parameter": {
                    "baseOrderDetail": {
                        "orderActionCode": self.order_action_code,
                        "acctTypeCode": self.acct_type_code,
                        "qty": self.qty,
                        "qtyTypeCode": self.qty_type_code,
                        "securityDetail": {"symbol": self.symbol},
                        "confNum": conf_num,
                    },
                    "tradableSecOrderDetail": {
                        "tifCode": self.tif_code,
                        "priceTypeDetail": self._price_type_detail_dict(),
                        "mktRouteCode": self.mkt_route_code,
                    },
                    "priceDetail": {},
                    "previewInd": True,
                    "confInd": True,
                    "acctNum": self.acct_num,
                }
            }
        }

    def _price_type_detail_dict(self) -> dict:
        d: dict[str, Any] = {"priceTypeCode": self.price_type_code}
        if self.limit_price is not None:
            d["limitPrice"] = self.limit_price
        return d


# ---------------------------------------------------------------------------
# Response sub-models — shared by preview and place
# ---------------------------------------------------------------------------

class EquityRespPriceDetail(BaseModel):
    """Price detail within an order confirm response."""
    model_config = {"populate_by_name": True}

    price: Optional[float] = None
    price_date_time: Optional[int] = Field(default=None, alias="priceDateTime")
    bid_price: Optional[float] = Field(default=None, alias="bidPrice")
    ask_price: Optional[float] = Field(default=None, alias="askPrice")


class EquityEstCommissionDetail(BaseModel):
    """Estimated commission detail within an order confirm response."""
    model_config = {"populate_by_name": True}

    est_commission: Optional[float] = Field(default=None, alias="estCommission")
    type_code: Optional[str] = Field(default=None, alias="typeCode")


class EquityRespPriceTypeDetail(BaseModel):
    """Price type detail in the response order detail."""
    model_config = {"populate_by_name": True}

    price_type_code: Optional[str] = Field(default=None, alias="priceTypeCode")
    price_type_desc: Optional[str] = Field(default=None, alias="priceTypeDesc")
    limit_price: Optional[float] = Field(default=None, alias="limitPrice")


class EquityRespTradableSecOrderDetail(BaseModel):
    """Tradable security order detail within a response order detail."""
    model_config = {"populate_by_name": True}

    price_type_detail: Optional[EquityRespPriceTypeDetail] = Field(
        default=None, alias="priceTypeDetail"
    )
    tif_code: Optional[str] = Field(default=None, alias="tifCode")
    mkt_route_code: Optional[str] = Field(default=None, alias="mktRouteCode")


class EquityRespSecurityDetail(BaseModel):
    """Security detail within the response order detail."""
    model_config = {"populate_by_name": True}

    symbol: Optional[str] = None
    cusip: Optional[str] = None
    sec_desc: Optional[str] = Field(default=None, alias="secDesc")


class EquityRespBaseOrderDetail(BaseModel):
    """Base order detail within the response order detail."""
    model_config = {"populate_by_name": True}

    order_action_code: Optional[str] = Field(default=None, alias="orderActionCode")
    action_code_desc: Optional[str] = Field(default=None, alias="actionCodeDesc")
    qty: Optional[float] = None
    qty_type_code: Optional[str] = Field(default=None, alias="qtyTypeCode")
    val_of_order: Optional[float] = Field(default=None, alias="valOfOrder")
    security_detail: Optional[EquityRespSecurityDetail] = Field(
        default=None, alias="securityDetail"
    )


class EquityRespOrderDetail(BaseModel):
    """Full order detail nested inside the confirm response."""
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    base_order_detail: Optional[EquityRespBaseOrderDetail] = Field(
        default=None, alias="baseOrderDetail"
    )
    tradable_sec_order_detail: Optional[EquityRespTradableSecOrderDetail] = Field(
        default=None, alias="tradableSecOrderDetail"
    )


class EquityOrderConfirmDetail(BaseModel):
    """The ``orderConfirmDetail`` object returned by both preview and place."""
    model_config = {"populate_by_name": True}

    resp_type_code: Optional[str] = Field(default=None, alias="respTypeCode")
    conf_num: Optional[str] = Field(default=None, alias="confNum")
    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    acct_type_code: Optional[str] = Field(default=None, alias="acctTypeCode")
    price_detail: Optional[EquityRespPriceDetail] = Field(
        default=None, alias="priceDetail"
    )
    est_commission_detail: Optional[EquityEstCommissionDetail] = Field(
        default=None, alias="estCommissionDetail"
    )
    dtc_est_fee: Optional[float] = Field(default=None, alias="dtcEstFee")
    net_amount: Optional[float] = Field(default=None, alias="netAmount")
    net_proceeds_inclusive: Optional[float] = Field(
        default=None, alias="netProceedsInclusive"
    )
    order_detail: Optional[EquityRespOrderDetail] = Field(
        default=None, alias="orderDetail"
    )


# ---------------------------------------------------------------------------
# Top-level response models
# ---------------------------------------------------------------------------

class EquityPreviewResponse(BaseModel):
    """Top-level response for ``POST /equity/preview/v1``."""
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    order_confirm_detail: Optional[EquityOrderConfirmDetail] = Field(
        default=None, alias="orderConfirmDetail"
    )

    @classmethod
    def from_api_response(cls, data: dict) -> "EquityPreviewResponse":
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


class EquityPlaceResponse(BaseModel):
    """Top-level response for ``POST /equity/place/v1``."""
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    order_confirm_detail: Optional[EquityOrderConfirmDetail] = Field(
        default=None, alias="orderConfirmDetail"
    )

    @classmethod
    def from_api_response(cls, data: dict) -> "EquityPlaceResponse":
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
