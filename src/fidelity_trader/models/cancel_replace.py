"""Pydantic models for cancel-and-replace (order modification) request and response."""
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

from fidelity_trader.models.equity_order import (
    EquityRespPriceDetail,
    EquityEstCommissionDetail,
    EquityRespOrderDetail,
)


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class CancelReplaceRequest(BaseModel):
    """Parameters for a cancel-and-replace order preview or place request.

    Mirrors the ``request.parameter`` shape observed in captured Trader+ traffic
    for the ``/cancelandreplace/preview/v1`` and ``/cancelandreplace/place/v1``
    endpoints.
    """
    model_config = {"populate_by_name": True}

    acct_num: str = Field(alias="acctNum")
    order_num_orig: str = Field(alias="orderNumOrig")
    symbol: str
    cusip: Optional[str] = Field(default=None)
    order_action_code: str = Field(alias="orderActionCode")  # "B" or "S"
    acct_type_code: str = Field(default="M", alias="acctTypeCode")
    qty: float
    qty_type_code: str = Field(default="S", alias="qtyTypeCode")
    tif_code: str = Field(default="D", alias="tifCode")
    price_type_code: str = Field(default="L", alias="priceTypeCode")
    limit_price: Optional[float] = Field(default=None, alias="limitPrice")
    mkt_route_code: str = Field(default="", alias="mktRouteCode")

    def to_preview_body(self) -> dict:
        """Build the JSON body for the cancel-and-replace preview endpoint."""
        return {
            "request": {
                "parameter": {
                    "baseOrderDetail": {
                        "orderActionCode": self.order_action_code,
                        "acctTypeCode": self.acct_type_code,
                        "qty": self.qty,
                        "qtyTypeCode": self.qty_type_code,
                        "securityDetail": self._security_detail_dict(),
                    },
                    "tradableSecOrderDetail": {
                        "tifCode": self.tif_code,
                        "priceTypeDetail": self._price_type_detail_dict(),
                        "mktRouteCode": self.mkt_route_code,
                    },
                    "orderNumOrig": self.order_num_orig,
                    "acctNum": self.acct_num,
                }
            }
        }

    def to_place_body(self, conf_num: str) -> dict:
        """Build the JSON body for the cancel-and-replace place endpoint.

        *conf_num* is the confirmation number returned by the preview step.
        """
        return {
            "request": {
                "parameter": {
                    "baseOrderDetail": {
                        "orderActionCode": self.order_action_code,
                        "acctTypeCode": self.acct_type_code,
                        "qty": self.qty,
                        "qtyTypeCode": self.qty_type_code,
                        "securityDetail": self._security_detail_dict(),
                        "confNum": conf_num,
                    },
                    "tradableSecOrderDetail": {
                        "tifCode": self.tif_code,
                        "priceTypeDetail": self._price_type_detail_dict(),
                    },
                    "previewInd": True,
                    "confInd": True,
                    "orderNumOrig": self.order_num_orig,
                    "acctNum": self.acct_num,
                }
            }
        }

    def _security_detail_dict(self) -> dict:
        d: dict[str, Any] = {"symbol": self.symbol}
        if self.cusip is not None:
            d["cusip"] = self.cusip
        return d

    def _price_type_detail_dict(self) -> dict:
        d: dict[str, Any] = {"priceTypeCode": self.price_type_code}
        if self.limit_price is not None:
            d["limitPrice"] = self.limit_price
        return d


# ---------------------------------------------------------------------------
# Response sub-models — error messages
# ---------------------------------------------------------------------------

class OrderConfirmMessage(BaseModel):
    """A single error/warning message from the API."""
    model_config = {"populate_by_name": True}

    message: Optional[str] = None
    detail: Optional[str] = None
    source: Optional[str] = None
    code: Optional[str] = None
    type: Optional[str] = None


class CancelReplaceConfirmMsgs(BaseModel):
    """Wrapper for ``orderConfirmMsgs`` which contains a list of messages.

    The API nests messages under ``orderConfirmMsgs.orderConfirmMessage``.
    This model flattens that into a simple ``messages`` list.
    """
    model_config = {"populate_by_name": True}

    messages: List[OrderConfirmMessage] = Field(
        default_factory=list, alias="orderConfirmMessage"
    )


# ---------------------------------------------------------------------------
# Response sub-model — order confirm detail (extends equity with errorCategories)
# ---------------------------------------------------------------------------

class CancelReplaceOrderConfirmDetail(BaseModel):
    """The ``orderConfirmDetail`` object returned by cancel-and-replace endpoints.

    Shares the same sub-model shapes as the equity order confirm detail but also
    includes ``errorCategories`` for error responses.
    """
    model_config = {"populate_by_name": True}

    resp_type_code: Optional[str] = Field(default=None, alias="respTypeCode")
    error_categories: Optional[List[str]] = Field(default=None, alias="errorCategories")
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

class CancelReplacePreviewResponse(BaseModel):
    """Top-level response for ``POST /cancelandreplace/preview/v1``."""
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    order_num_orig: Optional[str] = Field(default=None, alias="orderNumOrig")
    confirm_msgs: Optional[CancelReplaceConfirmMsgs] = Field(
        default=None, alias="orderConfirmMsgs"
    )
    order_confirm_detail: Optional[CancelReplaceOrderConfirmDetail] = Field(
        default=None, alias="orderConfirmDetail"
    )

    @classmethod
    def from_api_response(cls, data: dict) -> "CancelReplacePreviewResponse":
        """Parse the raw API JSON: ``{"cancelandreplace": {...}}``."""
        inner = data.get("cancelandreplace") or {}
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

    @property
    def is_error(self) -> bool:
        """True when ``respTypeCode`` is ``"E"``."""
        if self.order_confirm_detail:
            return self.order_confirm_detail.resp_type_code == "E"
        return False

    @property
    def error_messages(self) -> List[OrderConfirmMessage]:
        """List of error/warning messages, empty if none."""
        if self.confirm_msgs:
            return self.confirm_msgs.messages
        return []


class CancelReplacePlaceResponse(BaseModel):
    """Top-level response for ``POST /cancelandreplace/place/v1``."""
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    order_num_orig: Optional[str] = Field(default=None, alias="orderNumOrig")
    confirm_msgs: Optional[CancelReplaceConfirmMsgs] = Field(
        default=None, alias="orderConfirmMsgs"
    )
    order_confirm_detail: Optional[CancelReplaceOrderConfirmDetail] = Field(
        default=None, alias="orderConfirmDetail"
    )

    @classmethod
    def from_api_response(cls, data: dict) -> "CancelReplacePlaceResponse":
        """Parse the raw API JSON: ``{"cancelandreplace": {...}}``."""
        inner = data.get("cancelandreplace") or {}
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

    @property
    def is_error(self) -> bool:
        """True when ``respTypeCode`` is ``"E"``."""
        if self.order_confirm_detail:
            return self.order_confirm_detail.resp_type_code == "E"
        return False

    @property
    def error_messages(self) -> List[OrderConfirmMessage]:
        """List of error/warning messages, empty if none."""
        if self.confirm_msgs:
            return self.confirm_msgs.messages
        return []
