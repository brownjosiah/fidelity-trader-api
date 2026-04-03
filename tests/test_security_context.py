"""Tests for the security context / entitlements API."""

import httpx
import respx

from fidelity_trader.auth.security_context import SecurityContextAPI
from fidelity_trader.models.security_context import (
    SecurityContextResponse,
    PersonaReference,
    Entitlement,
    InternalSystemId,
)
from fidelity_trader._http import BASE_URL


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_entitlement(display="ATP", value="true", classification="access"):
    return {"value": value, "display": display, "classification": classification}


def _make_api_response(**overrides):
    base = {
        "employeeIndicator": "NON_EMPLOYEE",
        "personaReferences": [
            {"realm": "InstPart", "role": "FidCust"},
            {"realm": "Retail", "role": "FidCust"},
        ],
        "entitlements": [
            _make_entitlement("ATP", "true"),
            _make_entitlement("RTQ", "true"),
            _make_entitlement("ATBT", "true"),
            _make_entitlement("ProfessionalQuotes", "false"),
            _make_entitlement("InternationalQuotes", "true"),
            {"value": "AP012321", "display": "ALL", "classification": "fortress"},
        ],
        "internalSystemIds": [
            {"type": "MID", "ID": "ee629881ce0a8830"},
            {"type": "TRACKER_ID", "ID": "68f3ec43fbab51bc"},
        ],
        "errors": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestPersonaReference:
    def test_parse(self):
        ref = PersonaReference.model_validate({"realm": "Retail", "role": "FidCust"})
        assert ref.realm == "Retail"
        assert ref.role == "FidCust"

    def test_defaults(self):
        ref = PersonaReference.model_validate({})
        assert ref.realm == ""
        assert ref.role == ""


class TestEntitlement:
    def test_parse(self):
        e = Entitlement.model_validate(
            {"value": "true", "display": "ATP", "classification": "access"}
        )
        assert e.value == "true"
        assert e.display == "ATP"
        assert e.classification == "access"


class TestInternalSystemId:
    def test_parse(self):
        sid = InternalSystemId.model_validate({"type": "MID", "ID": "abc123"})
        assert sid.type == "MID"
        assert sid.id == "abc123"

    def test_alias_id_uppercase(self):
        sid = InternalSystemId.model_validate({"type": "MID", "ID": "xyz"})
        assert sid.id == "xyz"


class TestSecurityContextResponse:
    def test_from_api_response(self):
        data = _make_api_response()
        resp = SecurityContextResponse.from_api_response(data)
        assert resp.employee_indicator == "NON_EMPLOYEE"
        assert len(resp.persona_references) == 2
        assert len(resp.entitlements) == 6
        assert len(resp.internal_system_ids) == 2
        assert resp.errors == []

    def test_has_entitlement_true(self):
        resp = SecurityContextResponse.from_api_response(_make_api_response())
        assert resp.has_entitlement("ATP") is True
        assert resp.has_entitlement("RTQ") is True

    def test_has_entitlement_false_value(self):
        resp = SecurityContextResponse.from_api_response(_make_api_response())
        assert resp.has_entitlement("ProfessionalQuotes") is False

    def test_has_entitlement_missing(self):
        resp = SecurityContextResponse.from_api_response(_make_api_response())
        assert resp.has_entitlement("NonExistent") is False

    def test_has_realtime_quotes(self):
        resp = SecurityContextResponse.from_api_response(_make_api_response())
        assert resp.has_realtime_quotes is True

    def test_has_atp_access(self):
        resp = SecurityContextResponse.from_api_response(_make_api_response())
        assert resp.has_atp_access is True

    def test_no_realtime_quotes(self):
        data = _make_api_response(entitlements=[
            _make_entitlement("RTQ", "false"),
        ])
        resp = SecurityContextResponse.from_api_response(data)
        assert resp.has_realtime_quotes is False

    def test_empty_entitlements(self):
        data = _make_api_response(entitlements=[])
        resp = SecurityContextResponse.from_api_response(data)
        assert resp.has_atp_access is False
        assert resp.has_realtime_quotes is False

    def test_empty_response(self):
        resp = SecurityContextResponse.from_api_response({})
        assert resp.employee_indicator == ""
        assert resp.persona_references == []
        assert resp.entitlements == []


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

class TestSecurityContextAPI:
    @respx.mock
    def test_get_context_returns_model(self):
        route = respx.post(
            f"{BASE_URL}/ftgw/digital/pico/api/v1/context/security"
        ).mock(return_value=httpx.Response(200, json=_make_api_response()))

        api = SecurityContextAPI(httpx.Client())
        try:
            result = api.get_context()
        finally:
            api._http.close()

        assert isinstance(result, SecurityContextResponse)
        assert result.employee_indicator == "NON_EMPLOYEE"
        assert result.has_atp_access is True
        assert route.called

    @respx.mock
    def test_get_context_sends_empty_json_body(self):
        route = respx.post(
            f"{BASE_URL}/ftgw/digital/pico/api/v1/context/security"
        ).mock(return_value=httpx.Response(200, json=_make_api_response()))

        api = SecurityContextAPI(httpx.Client())
        try:
            api.get_context()
        finally:
            api._http.close()

        import json
        body = json.loads(route.calls[0].request.content)
        assert body == {}
