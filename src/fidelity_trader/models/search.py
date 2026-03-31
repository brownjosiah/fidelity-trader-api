from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Suggestion(BaseModel):
    model_config = {"populate_by_name": True}

    symbol: str
    cusip: Optional[str] = None
    desc: Optional[str] = None
    type: Optional[str] = None
    sub_type: Optional[str] = Field(default=None, alias="subType")
    exchange: Optional[str] = None
    nc: Optional[bool] = None
    intl: Optional[bool] = None
    trade_eligible: Optional[bool] = Field(default=None, alias="tradeEligible")
    options: Optional[List[str]] = None


class AutosuggestResponse(BaseModel):
    count: int = 0
    suggestions: List[Suggestion] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "AutosuggestResponse":
        quotes = data.get("quotes") or {}
        count = quotes.get("count", 0)
        raw_suggestions = quotes.get("suggestions") or []
        suggestions = [Suggestion.model_validate(s) for s in raw_suggestions]
        return cls(count=count, suggestions=suggestions)
