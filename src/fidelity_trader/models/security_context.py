"""Models for the security context / entitlements API response."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PersonaReference(BaseModel):
    """A persona reference entry (realm + role)."""
    model_config = {"populate_by_name": True}

    realm: str = ""
    role: str = ""


class Entitlement(BaseModel):
    """A single entitlement entry."""
    model_config = {"populate_by_name": True}

    value: str = ""
    display: str = ""
    classification: str = ""


class InternalSystemId(BaseModel):
    """An internal system identifier."""
    model_config = {"populate_by_name": True}

    type: str = Field(default="", alias="type")
    id: str = Field(default="", alias="ID")


class SecurityContextResponse(BaseModel):
    """Security context / entitlements response.

    Returned by POST /ftgw/digital/pico/api/v1/context/security.
    Contains user entitlements (ATP access, real-time quotes, etc.)
    and internal identifiers.
    """
    model_config = {"populate_by_name": True}

    employee_indicator: str = Field(default="", alias="employeeIndicator")
    persona_references: list[PersonaReference] = Field(
        default_factory=list, alias="personaReferences"
    )
    entitlements: list[Entitlement] = Field(default_factory=list)
    internal_system_ids: list[InternalSystemId] = Field(
        default_factory=list, alias="internalSystemIds"
    )
    errors: list = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> SecurityContextResponse:
        return cls.model_validate(data)

    def has_entitlement(self, display: str) -> bool:
        """Check if a specific entitlement is enabled."""
        for e in self.entitlements:
            if e.display == display and e.value.lower() == "true":
                return True
        return False

    @property
    def has_realtime_quotes(self) -> bool:
        return self.has_entitlement("RTQ")

    @property
    def has_atp_access(self) -> bool:
        return self.has_entitlement("ATP")
