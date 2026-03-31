"""Models for the ATN preferences API responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SystemMessage(BaseModel):
    """A system message from the preferences service."""
    model_config = {"populate_by_name": True}

    message: str = ""
    detail: str = ""
    source: str = ""
    code: str = ""
    type: str = ""


class PreferenceData(BaseModel):
    """A single preference path and its key-value data."""
    model_config = {"populate_by_name": True}

    preference_path: str = Field(default="", alias="preferencePath")
    data: list[dict] = Field(default_factory=list)


class PreferencesResponse(BaseModel):
    """Response from get/save/delete preference endpoints."""
    model_config = {"populate_by_name": True}

    sys_msgs: list[SystemMessage] = Field(default_factory=list)
    preference_data: list[PreferenceData] = Field(
        default_factory=list, alias="preferenceData"
    )

    @classmethod
    def from_api_response(cls, data: dict) -> PreferencesResponse:
        # Flatten sysMsgs wrapper
        sys_msgs_raw = data.get("sysMsgs", {}).get("sysMsg", [])
        return cls.model_validate({
            "sys_msgs": sys_msgs_raw,
            "preferenceData": data.get("preferenceData", []),
        })

    @property
    def is_success(self) -> bool:
        return any("Successful" in m.message for m in self.sys_msgs)
