"""Pydantic models for order cancellation request and response."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class CancelConfirmDetail(BaseModel):
    """A single entry in the ``cancelConfirmDetail`` list returned by the cancel endpoint."""
    model_config = {"populate_by_name": True}

    resp_type_code: Optional[str] = Field(default=None, alias="respTypeCode")
    conf_num: Optional[str] = Field(default=None, alias="confNum")
    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    action_code: Optional[str] = Field(default=None, alias="actionCode")
    action_code_desc: Optional[str] = Field(default=None, alias="actionCodeDesc")
    orig_qty: Optional[float] = Field(default=None, alias="origQty")
    exec_qty: Optional[float] = Field(default=None, alias="execQty")
    remaining_qty: Optional[float] = Field(default=None, alias="remainingQty")

    @property
    def is_accepted(self) -> bool:
        """True when ``respTypeCode`` is ``"A"`` (cancellation accepted)."""
        return self.resp_type_code == "A"


class CancelResponse(BaseModel):
    """Top-level response for ``POST /cancel/place/v1``."""
    model_config = {"populate_by_name": True}

    cancel_confirm_detail: List[CancelConfirmDetail] = Field(
        default_factory=list, alias="cancelConfirmDetail"
    )

    @classmethod
    def from_api_response(cls, data: dict) -> "CancelResponse":
        """Parse the raw API JSON: ``{"place": {...}}``."""
        inner = data.get("place") or {}
        return cls.model_validate(inner)

    @property
    def is_accepted(self) -> bool:
        """True when at least one confirm detail has ``respTypeCode == "A"``."""
        return any(d.is_accepted for d in self.cancel_confirm_detail)
