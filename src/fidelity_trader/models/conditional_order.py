"""Pydantic models for conditional order (OTOCO/OTO/OCO) preview/place request and response.

Conditional orders use a different request shape from standard equity orders:
- Top-level key is ``parameters`` (plural), not ``request.parameter``
- Contains ``condOrderTypeCode`` to specify the conditional type
- Multiple legs in ``condOrderDetails`` array
- Preview confNums are applied to triggered legs only (index >= 1) in the place body
- Place body includes ``previewInd: false, confInd: false`` at the parameters level
- Stop orders use ``priceTypeCode: "S"`` with ``stopPrice`` (not limitPrice)
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ConditionalOrderLeg(BaseModel):
    """A single leg within a conditional order."""
    model_config = {"populate_by_name": True}

    acct_type_code: str = Field(default="M", alias="acctTypeCode")
    order_action_code: str = Field(alias="orderActionCode")  # "B" or "S"
    qty: float
    symbol: str
    tif_code: str = Field(default="D", alias="tifCode")
    price_type_code: str = Field(alias="priceTypeCode")  # "L"=Limit, "M"=Market, "S"=Stop
    limit_price: Optional[float] = Field(default=None, alias="limitPrice")
    stop_price: Optional[float] = Field(default=None, alias="stopPrice")

    def _to_order_detail(self) -> dict:
        """Build the per-leg dict for the ``condOrderDetails`` array."""
        base: dict[str, Any] = {
            "acctTypeCode": self.acct_type_code,
            "orderActionCode": self.order_action_code,
            "qty": self.qty,
            "secDetail": {"symbol": self.symbol},
        }
        price_detail: dict[str, Any] = {"priceTypeCode": self.price_type_code}
        if self.limit_price is not None:
            price_detail["limitPrice"] = self.limit_price
        if self.stop_price is not None:
            price_detail["stopPrice"] = self.stop_price
        return {
            "baseOrderDetail": base,
            "tradableSecOrderDetail": {
                "tifCode": self.tif_code,
                "priceTypeDetail": price_detail,
            },
        }

    def _to_place_detail(self, conf_num: Optional[str] = None) -> dict:
        """Build the per-leg dict for the place body, optionally injecting confNum."""
        detail = self._to_order_detail()
        if conf_num is not None:
            detail["baseOrderDetail"]["confNum"] = conf_num
        return detail


class ConditionalOrderRequest(BaseModel):
    """Parameters for a conditional order preview or place request.

    Mirrors the ``parameters`` shape observed in captured Trader+ traffic for
    OTOCO, OTO, and OCO conditional orders.
    """
    model_config = {"populate_by_name": True}

    cond_order_type_code: str = Field(alias="condOrderTypeCode")  # "OTOCO", "OTO", "OCO"
    acct_num: str = Field(alias="acctNum")
    legs: list[ConditionalOrderLeg]

    def to_preview_body(self) -> dict:
        """Build the JSON body for the conditional preview endpoint."""
        return {
            "parameters": {
                "condOrderTypeCode": self.cond_order_type_code,
                "acctNum": self.acct_num,
                "cntgntDetails": [],
                "condOrderDetail": {},
                "condOrderDetails": [
                    leg._to_order_detail() for leg in self.legs
                ],
            }
        }

    def to_place_body(self, conf_nums: list[str]) -> dict:
        """Build the JSON body for the conditional place endpoint.

        *conf_nums* are the confirmation numbers returned by preview.  They are
        applied to **triggered legs only** — the primary leg (index 0) does not
        receive a confNum.  The first conf_num goes to leg index 1, the second
        to leg index 2, etc.
        """
        details: list[dict] = []
        for i, leg in enumerate(self.legs):
            if i == 0:
                details.append(leg._to_place_detail())
            else:
                cn = conf_nums[i - 1] if (i - 1) < len(conf_nums) else None
                details.append(leg._to_place_detail(conf_num=cn))
        return {
            "parameters": {
                "condOrderTypeCode": self.cond_order_type_code,
                "acctNum": self.acct_num,
                "cntgntDetails": [],
                "condOrderDetail": {},
                "previewInd": False,
                "confInd": False,
                "condOrderDetails": details,
            }
        }


# ---------------------------------------------------------------------------
# Response sub-models
# ---------------------------------------------------------------------------

class CondOrderSysMsg(BaseModel):
    """A single system message from the conditional order response."""
    model_config = {"populate_by_name": True}

    message: Optional[str] = None
    detail: Optional[str] = None
    source: Optional[str] = None
    code: Optional[str] = None
    type: Optional[str] = None


class CondOrderEstCommDetail(BaseModel):
    """Estimated commission detail for a conditional order leg."""
    model_config = {"populate_by_name": True}

    amt: Optional[float] = None
    type_code: Optional[str] = Field(default=None, alias="typeCode")
    est_comm: Optional[float] = Field(default=None, alias="estComm")


class CondOrderPriceDetail(BaseModel):
    """Price detail for a conditional order leg response."""
    model_config = {"populate_by_name": True}

    price: Optional[float] = None
    price_date_time: Optional[int] = Field(default=None, alias="priceDateTime")
    bid_price: Optional[float] = Field(default=None, alias="bidPrice")
    ask_price: Optional[float] = Field(default=None, alias="askPrice")


class CondOrderSecDetail(BaseModel):
    """Security detail within a conditional order leg response."""
    model_config = {"populate_by_name": True}

    symbol: Optional[str] = None
    cusip: Optional[str] = None
    sec_desc: Optional[str] = Field(default=None, alias="secDesc")


class CondOrderBaseDetail(BaseModel):
    """Base order detail within a leg's order detail."""
    model_config = {"populate_by_name": True}

    order_action_code: Optional[str] = Field(default=None, alias="orderActionCode")
    qty: Optional[float] = None
    value_of_order: Optional[float] = Field(default=None, alias="valueOfOrder")
    sec_detail: Optional[CondOrderSecDetail] = Field(default=None, alias="secDetail")


class CondOrderPriceTypeDetail(BaseModel):
    """Price type detail within a leg's tradable security order detail."""
    model_config = {"populate_by_name": True}

    price_type_code: Optional[str] = Field(default=None, alias="priceTypeCode")
    limit_price: Optional[float] = Field(default=None, alias="limitPrice")
    stop_price: Optional[float] = Field(default=None, alias="stopPrice")


class CondOrderTradableSecDetail(BaseModel):
    """Tradable security order detail within a leg response."""
    model_config = {"populate_by_name": True}

    tif_code: Optional[str] = Field(default=None, alias="tifCode")
    price_type_detail: Optional[CondOrderPriceTypeDetail] = Field(
        default=None, alias="priceTypeDetail"
    )
    option_detail: Optional[dict] = Field(default=None, alias="optionDetail")


class CondOrderDetail(BaseModel):
    """The inner order detail within a leg's orderConfirmDetail."""
    model_config = {"populate_by_name": True}

    sys_msgs: Optional[dict] = Field(default=None, alias="sysMsgs")
    base_order_detail: Optional[CondOrderBaseDetail] = Field(
        default=None, alias="baseOrderDetail"
    )
    tradable_sec_order_detail: Optional[CondOrderTradableSecDetail] = Field(
        default=None, alias="tradableSecOrderDetail"
    )

    @property
    def warnings(self) -> list[CondOrderSysMsg]:
        """Extract warning-type system messages from this leg."""
        if not self.sys_msgs:
            return []
        msgs = self.sys_msgs.get("sysMsg", [])
        return [
            CondOrderSysMsg.model_validate(m)
            for m in msgs
            if m.get("type") == "warning"
        ]

    @property
    def all_sys_msgs(self) -> list[CondOrderSysMsg]:
        """Extract all system messages from this leg."""
        if not self.sys_msgs:
            return []
        msgs = self.sys_msgs.get("sysMsg", [])
        return [CondOrderSysMsg.model_validate(m) for m in msgs]


class CondOrderConfirmDetail(BaseModel):
    """The ``orderConfirmDetail`` for a single leg in the conditional response."""
    model_config = {"populate_by_name": True}

    resp_type_code: Optional[str] = Field(default=None, alias="respTypeCode")
    conf_num: Optional[str] = Field(default=None, alias="confNum")
    acct_type_code: Optional[str] = Field(default=None, alias="acctTypeCode")
    net_amt: Optional[float] = Field(default=None, alias="netAmt")
    total_cost: Optional[float] = Field(default=None, alias="totalCost")
    order_detail: Optional[CondOrderDetail] = Field(default=None, alias="orderDetail")
    est_comm_detail: Optional[CondOrderEstCommDetail] = Field(
        default=None, alias="estCommDetail"
    )
    price_detail: Optional[CondOrderPriceDetail] = Field(
        default=None, alias="priceDetail"
    )
    cond_order_detail: Optional[dict] = Field(default=None, alias="condOrderDetail")


class CondOrderLegResponse(BaseModel):
    """A single leg in the ``condOrderDetails`` response array."""
    model_config = {"populate_by_name": True}

    order_confirm_detail: Optional[CondOrderConfirmDetail] = Field(
        default=None, alias="orderConfirmDetail"
    )


# ---------------------------------------------------------------------------
# Top-level response models
# ---------------------------------------------------------------------------

class ConditionalPreviewResponse(BaseModel):
    """Top-level response for ``POST /conditional/preview/v1``."""
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    legs: list[CondOrderLegResponse] = Field(default_factory=list)
    top_sys_msgs: list[CondOrderSysMsg] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "ConditionalPreviewResponse":
        """Parse the raw API JSON: ``{"preview": {...}}``."""
        inner = data.get("preview") or {}
        acct_num = inner.get("acctNum")
        raw_legs = inner.get("condOrderDetails", [])
        legs = [CondOrderLegResponse.model_validate(leg) for leg in raw_legs]

        # Top-level sysMsgs
        top_msgs: list[CondOrderSysMsg] = []
        sys_msgs_raw = inner.get("sysMsgs", {})
        for m in sys_msgs_raw.get("sysMsg", []):
            top_msgs.append(CondOrderSysMsg.model_validate(m))

        return cls(acctNum=acct_num, legs=legs, top_sys_msgs=top_msgs)

    @property
    def conf_nums(self) -> list[str]:
        """All confirmation numbers from all legs, in order."""
        nums: list[str] = []
        for leg in self.legs:
            if leg.order_confirm_detail and leg.order_confirm_detail.conf_num:
                nums.append(leg.order_confirm_detail.conf_num)
        return nums

    @property
    def is_validated(self) -> bool:
        """True when the first leg has ``respTypeCode == "V"``."""
        if self.legs and self.legs[0].order_confirm_detail:
            return self.legs[0].order_confirm_detail.resp_type_code == "V"
        return False

    @property
    def all_validated(self) -> bool:
        """True when every leg has ``respTypeCode == "V"``."""
        if not self.legs:
            return False
        return all(
            leg.order_confirm_detail is not None
            and leg.order_confirm_detail.resp_type_code == "V"
            for leg in self.legs
        )


class ConditionalPlaceResponse(BaseModel):
    """Top-level response for ``POST /conditional/place/v1``."""
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    legs: list[CondOrderLegResponse] = Field(default_factory=list)
    top_sys_msgs: list[CondOrderSysMsg] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "ConditionalPlaceResponse":
        """Parse the raw API JSON: ``{"place": {...}}``."""
        inner = data.get("place") or {}
        acct_num = inner.get("acctNum")
        raw_legs = inner.get("condOrderDetails", [])
        legs = [CondOrderLegResponse.model_validate(leg) for leg in raw_legs]

        # Top-level sysMsgs
        top_msgs: list[CondOrderSysMsg] = []
        sys_msgs_raw = inner.get("sysMsgs", {})
        for m in sys_msgs_raw.get("sysMsg", []):
            top_msgs.append(CondOrderSysMsg.model_validate(m))

        return cls(acctNum=acct_num, legs=legs, top_sys_msgs=top_msgs)

    @property
    def conf_nums(self) -> list[str]:
        """All confirmation numbers from all legs, in order."""
        nums: list[str] = []
        for leg in self.legs:
            if leg.order_confirm_detail and leg.order_confirm_detail.conf_num:
                nums.append(leg.order_confirm_detail.conf_num)
        return nums

    @property
    def is_accepted(self) -> bool:
        """True when the first leg has ``respTypeCode == "A"``."""
        if self.legs and self.legs[0].order_confirm_detail:
            return self.legs[0].order_confirm_detail.resp_type_code == "A"
        return False

    @property
    def all_accepted(self) -> bool:
        """True when every leg has ``respTypeCode == "A"``."""
        if not self.legs:
            return False
        return all(
            leg.order_confirm_detail is not None
            and leg.order_confirm_detail.resp_type_code == "A"
            for leg in self.legs
        )
