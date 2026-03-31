from __future__ import annotations

import math
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator


def _parse_infinity(value: object) -> float:
    """Convert "Infinity"/"-Infinity" strings to float; pass floats through."""
    if isinstance(value, str):
        if value == "Infinity":
            return math.inf
        if value == "-Infinity":
            return -math.inf
        return float(value)
    return float(value)


class AnalyticsGreeks(BaseModel):
    model_config = {"populate_by_name": True}

    price: float = 0.0
    profit: float = 0.0
    delta: float = 0.0
    theta: float = 0.0
    gamma: float = 0.0
    vega: float = 0.0
    rho: float = 0.0
    prem: float = 0.0
    total_value: float = Field(default=0.0, alias="totalValue")
    prob_profit: float = Field(default=0.0, alias="probProfit")
    break_even: List[float] = Field(default_factory=list, alias="breakEven")
    max_profit: float = Field(default=0.0, alias="maxProfit")
    max_loss: float = Field(default=0.0, alias="maxLoss")
    max_profit_1sd: List[float] = Field(default_factory=list, alias="maxProfit1sd")
    max_loss_1sd: List[float] = Field(default_factory=list, alias="maxLoss1sd")
    iv: Optional[float] = None

    @field_validator("max_profit", "max_loss", mode="before")
    @classmethod
    def _coerce_infinity(cls, v: object) -> float:
        return _parse_infinity(v)


class PositionAnalytics(BaseModel):
    model_config = {"populate_by_name": True}

    position_detail: AnalyticsGreeks = Field(alias="positionDetail")
    leg_details: List[AnalyticsGreeks] = Field(default_factory=list, alias="legDetails")

    @classmethod
    def from_api_dict(cls, data: dict) -> "PositionAnalytics":
        pos_detail = AnalyticsGreeks.model_validate(data.get("positionDetail") or {})
        legs = [
            AnalyticsGreeks.model_validate(leg)
            for leg in (data.get("legDetails") or [])
        ]
        return cls(position_detail=pos_detail, leg_details=legs)


class AnalyticsEvaluation(BaseModel):
    model_config = {"populate_by_name": True}

    eval_date: str = Field(alias="evalDate")
    position_details: List[PositionAnalytics] = Field(
        default_factory=list, alias="positionDetails"
    )

    @classmethod
    def from_api_dict(cls, data: dict) -> "AnalyticsEvaluation":
        eval_date = data.get("evalDate", "")
        pos_details = [
            PositionAnalytics.from_api_dict(p)
            for p in (data.get("positionDetails") or [])
        ]
        return cls(eval_date=eval_date, position_details=pos_details)


class AnalyticsResponse(BaseModel):
    evaluations: List[AnalyticsEvaluation] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "AnalyticsResponse":
        raw_list = data.get("positionsAnalyticsDataDetails") or []
        evaluations = [AnalyticsEvaluation.from_api_dict(e) for e in raw_list]
        return cls(evaluations=evaluations)
