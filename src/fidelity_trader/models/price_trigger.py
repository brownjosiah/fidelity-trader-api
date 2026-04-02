"""Pydantic models for the price triggers list API."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class PriceTrigger(BaseModel):
    """A single price trigger entry.

    Field names are speculative — we only have an empty-list capture so far.
    All fields are Optional until a populated response is captured.
    """

    model_config = {"populate_by_name": True}

    trigger_id: Optional[str] = Field(default=None, alias="triggerId")
    symbol: Optional[str] = None
    trigger_type: Optional[str] = Field(default=None, alias="triggerType")
    trigger_price: Optional[float] = Field(default=None, alias="triggerPrice")
    status: Optional[str] = None
    created_date: Optional[str] = Field(default=None, alias="createdDate")


class PriceTriggerSummary(BaseModel):
    """The ``priceTrigger`` wrapper object from the API response."""

    model_config = {"populate_by_name": True}

    total_account: int = Field(default=0, alias="totalAccount")
    available_account: int = Field(default=0, alias="availableAccount")
    offset: int = 0
    triggers: List[PriceTrigger] = Field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """Return True when the trigger list contains no entries."""
        return len(self.triggers) == 0


class PriceTriggersResponse(BaseModel):
    """Top-level response wrapper for the price triggers list endpoint."""

    price_trigger: PriceTriggerSummary = Field(
        default_factory=PriceTriggerSummary,
        alias="priceTrigger",
    )

    model_config = {"populate_by_name": True}

    @classmethod
    def from_api_response(cls, data: dict) -> "PriceTriggersResponse":
        """Parse a raw API JSON response into a PriceTriggersResponse.

        Extracts the ``priceTrigger`` wrapper and validates its contents.
        Falls back to empty defaults when the key is missing.
        """
        raw_trigger = data.get("priceTrigger") or {}
        triggers_list = raw_trigger.get("triggers") or []
        triggers = [PriceTrigger.model_validate(t) for t in triggers_list]
        summary = PriceTriggerSummary(
            total_account=raw_trigger.get("totalAccount", 0),
            available_account=raw_trigger.get("availableAccount", 0),
            offset=raw_trigger.get("offset", 0),
            triggers=triggers,
        )
        return cls(price_trigger=summary)

    @property
    def is_empty(self) -> bool:
        """Convenience proxy — True when there are no triggers."""
        return self.price_trigger.is_empty
