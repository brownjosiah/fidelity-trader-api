from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class HolidayDetail(BaseModel):
    model_config = {"populate_by_name": True}

    country_code: str = Field(alias="countryCode")
    date: int = Field(description="Unix timestamp of the holiday")
    holiday_desc: str = Field(alias="holidayDesc")
    holiday_type: str = Field(alias="holidayType")
    early_close_tm: Optional[str] = Field(default=None, alias="earlyCloseTm")

    @property
    def is_full_holiday(self) -> bool:
        """True when the market is fully closed (holidayType == 'H')."""
        return self.holiday_type == "H"

    @property
    def is_abbreviated(self) -> bool:
        """True when trading ends early (holidayType == 'A')."""
        return self.holiday_type == "A"

    @property
    def date_str(self) -> str:
        """Convert the unix timestamp to a readable YYYY-MM-DD string (UTC)."""
        return datetime.fromtimestamp(self.date, tz=timezone.utc).strftime("%Y-%m-%d")


class HolidayCalendarResponse(BaseModel):
    holidays: list[HolidayDetail] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "HolidayCalendarResponse":
        detail_list = data.get("holidayCalendarDetails") or []
        return cls(
            holidays=[HolidayDetail.model_validate(d) for d in detail_list]
        )
