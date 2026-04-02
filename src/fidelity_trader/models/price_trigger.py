"""Pydantic models for the price triggers API (list, create, delete)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------


class PriceTriggerDevice(BaseModel):
    """A notification device target for a price trigger."""

    name: str


DEFAULT_DEVICES: List[PriceTriggerDevice] = [
    PriceTriggerDevice(name="Active Trader Pro"),
    PriceTriggerDevice(name="Fidelity mobile applications"),
]


# ---------------------------------------------------------------------------
# List endpoint models (existing)
# ---------------------------------------------------------------------------


class PriceTrigger(BaseModel):
    """A single price trigger entry from the list endpoint.

    Originally speculative fields are preserved for backward compatibility.
    New fields from the create-response capture are also included.
    """

    model_config = {"populate_by_name": True}

    # Original speculative fields (list endpoint)
    trigger_id: Optional[str] = Field(default=None, alias="triggerId")
    symbol: Optional[str] = None
    trigger_type: Optional[str] = Field(default=None, alias="triggerType")
    trigger_price: Optional[float] = Field(default=None, alias="triggerPrice")
    status: Optional[str] = None
    created_date: Optional[str] = Field(default=None, alias="createdDate")

    # Fields now confirmed from create-response capture
    id: Optional[str] = None
    operator: Optional[str] = None
    value: Optional[float] = None
    currency: Optional[str] = None
    notes: Optional[str] = None
    create_time: Optional[int] = Field(default=None, alias="createTime")
    update_time: Optional[int] = Field(default=None, alias="updateTime")
    devices: Optional[List[PriceTriggerDevice]] = None


# ---------------------------------------------------------------------------
# Create endpoint models
# ---------------------------------------------------------------------------


class PriceTriggerCreateRequest(BaseModel):
    """Request body for the price trigger create endpoint.

    POST .../price-triggers/create
    Captured shape:
        {"triggers": [{...}], "devices": [{...}]}
    """

    model_config = {"populate_by_name": True}

    symbol: str
    operator: str
    value: float
    currency: str = "USD"
    notes: str = ""
    devices: List[PriceTriggerDevice] = Field(default_factory=lambda: list(DEFAULT_DEVICES))

    def to_api_payload(self) -> dict:
        """Serialize to the JSON shape expected by the Fidelity API."""
        return {
            "triggers": [
                {
                    "currency": self.currency,
                    "notes": self.notes,
                    "operator": self.operator,
                    "symbol": self.symbol,
                    "value": self.value,
                }
            ],
            "devices": [{"name": d.name} for d in self.devices],
        }


class CreatedPriceTrigger(BaseModel):
    """A single trigger entry returned from the create endpoint.

    Captured shape:
        {"id": "...", "symbol": "SPY", "operator": "lessThanPercent",
         "value": 4, "currency": "USD", "createTime": ..., "updateTime": ...,
         "devices": [...]}
    """

    model_config = {"populate_by_name": True}

    id: str
    symbol: str
    operator: str
    value: float
    currency: str
    create_time: int = Field(alias="createTime")
    update_time: int = Field(alias="updateTime")
    devices: List[PriceTriggerDevice] = Field(default_factory=list)


class PriceTriggerCreateResponse(BaseModel):
    """Top-level response wrapper for the price trigger create endpoint."""

    triggers: List[CreatedPriceTrigger] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "PriceTriggerCreateResponse":
        """Parse a raw API JSON response into a PriceTriggerCreateResponse."""
        raw_triggers = data.get("triggers") or []
        triggers = [CreatedPriceTrigger.model_validate(t) for t in raw_triggers]
        return cls(triggers=triggers)


# ---------------------------------------------------------------------------
# Delete endpoint models
# ---------------------------------------------------------------------------


class PriceTriggerDeleteRequest(BaseModel):
    """Request body for the price trigger delete endpoint.

    POST .../price-triggers/delete
    Modelled from the captured endpoint path; request body not fully
    extracted but inferred as a list of trigger IDs.
    """

    trigger_ids: List[str]

    def to_api_payload(self) -> dict:
        """Serialize to the JSON shape expected by the Fidelity API."""
        return {
            "triggers": [{"id": tid} for tid in self.trigger_ids],
        }


class PriceTriggerDeleteResponse(BaseModel):
    """Response from the price trigger delete endpoint.

    Body shape not fully captured; stores the raw data for inspection.
    """

    raw: dict = Field(default_factory=dict)

    @classmethod
    def from_api_response(cls, data: dict) -> "PriceTriggerDeleteResponse":
        """Parse a raw API JSON response into a PriceTriggerDeleteResponse."""
        return cls(raw=data)


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
