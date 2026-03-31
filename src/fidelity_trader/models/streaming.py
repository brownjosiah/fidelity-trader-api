from __future__ import annotations

from pydantic import BaseModel, Field


class StreamingAuthResponse(BaseModel):
    model_config = {"populate_by_name": True}

    streaming_host: str = Field(alias="StreamingHost")
    streaming_port: str = Field(alias="StreamingPort")
    polling_host: str = Field(alias="PollingHost")
    polling_port: str = Field(alias="PollingPort")
    access_token: str = Field(alias="AccessToken")
