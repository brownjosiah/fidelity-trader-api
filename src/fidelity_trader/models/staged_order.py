"""Pydantic models for staged/saved order retrieval."""
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class StagedOrderMessage(BaseModel):
    """A message entry returned by the staged-order API."""

    model_config = {"populate_by_name": True}

    code: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None


class StagedOrderDetail(BaseModel):
    """A single staged/saved order.

    The exact shape is not yet captured (only the empty-response case has been
    observed).  Fields are kept intentionally flexible so future captures can
    be modelled without breaking existing callers.
    """

    model_config = {"populate_by_name": True}

    stage_id: Optional[str] = Field(default=None, alias="stageId")
    stage_type: Optional[str] = Field(default=None, alias="stageType")
    # Catch-all for any additional fields returned by the API.
    raw: Optional[dict[str, Any]] = Field(default=None, exclude=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StagedOrderDetail":
        """Build from a raw API dict, preserving unknown fields in *raw*."""
        instance = cls.model_validate(data)
        instance.raw = data
        return instance


class StagedOrdersResponse(BaseModel):
    """Top-level response for ``POST .../staged-order/get``."""

    model_config = {"populate_by_name": True}

    messages: List[StagedOrderMessage] = Field(default_factory=list)
    staged_orders: Optional[List[StagedOrderDetail]] = Field(
        default=None, alias="stagedOrders"
    )

    @classmethod
    def from_api_response(cls, data: dict) -> "StagedOrdersResponse":
        """Parse the raw API JSON response.

        Handles both the empty-result shape (``messages`` array with code
        ``"204"``) and the populated shape (``stagedOrders`` array).
        """
        messages_raw = data.get("messages") or []
        messages = [StagedOrderMessage.model_validate(m) for m in messages_raw]

        staged_raw = data.get("stagedOrders")
        staged_orders: Optional[List[StagedOrderDetail]] = None
        if staged_raw is not None:
            staged_orders = [StagedOrderDetail.from_dict(item) for item in staged_raw]

        return cls(messages=messages, stagedOrders=staged_orders)

    @property
    def is_empty(self) -> bool:
        """True when there are no staged orders.

        Considers both the explicit ``"204"`` message code (no data) and the
        absence of any items in ``staged_orders``.
        """
        if any(m.code == "204" for m in self.messages):
            return True
        if self.staged_orders is None or len(self.staged_orders) == 0:
            return True
        return False
