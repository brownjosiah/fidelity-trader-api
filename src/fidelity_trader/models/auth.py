from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class FidelityStatus(BaseModel):
    model_config = {"populate_by_name": True}

    code: int
    message: str
    request_identifier: Optional[str] = Field(default=None, alias="requestIdentifier")
    context: Optional[str] = Field(default=None, alias="Context")

    @property
    def is_success(self) -> bool:
        return self.code == 1200


class ResponseBaseInfo(BaseModel):
    model_config = {"populate_by_name": True}

    session_tokens: Optional[dict] = Field(default=None, alias="sessionTokens")
    status: FidelityStatus
    links: list = Field(default_factory=list)


class LoginResponse(BaseModel):
    model_config = {"populate_by_name": True}

    response_base_info: ResponseBaseInfo = Field(alias="responseBaseInfo")
    authenticators: list = Field(default_factory=list)
    location: Optional[str] = None
    reference_id: Optional[str] = Field(default=None, alias="referenceId")
    callbacks: list = Field(default_factory=list)

    @property
    def status(self) -> FidelityStatus:
        return self.response_base_info.status
