"""Tests for pydantic models: FidelityStatus, LoginResponse, and shared parse helpers."""
import pytest

from fidelity_trader.models.auth import FidelityStatus, LoginResponse
from fidelity_trader.models._parsers import _parse_float, _parse_int


# ---------------------------------------------------------------------------
# Helper / unit tests
# ---------------------------------------------------------------------------

class TestParseHelpers:
    def test_parse_float_none(self):
        assert _parse_float(None) is None

    def test_parse_float_empty_string(self):
        assert _parse_float("") is None

    def test_parse_float_dash(self):
        assert _parse_float("--") is None

    def test_parse_float_na(self):
        assert _parse_float("N/A") is None

    def test_parse_float_comma_separated(self):
        assert _parse_float("1,234,567.89") == pytest.approx(1234567.89)

    def test_parse_float_plain_string(self):
        assert _parse_float("125000.50") == pytest.approx(125000.50)

    def test_parse_float_int(self):
        assert _parse_float(100) == pytest.approx(100.0)

    def test_parse_int_none(self):
        assert _parse_int(None) is None

    def test_parse_int_empty_string(self):
        assert _parse_int("") is None

    def test_parse_int_valid(self):
        assert _parse_int("3") == 3

    def test_parse_int_float_string(self):
        assert _parse_int("2.0") == 2


# ---------------------------------------------------------------------------
# FidelityStatus
# ---------------------------------------------------------------------------

class TestFidelityStatus:
    def test_fidelity_status_parses(self):
        status = FidelityStatus.model_validate({"code": 1200, "message": "OK"})
        assert status.code == 1200
        assert status.message == "OK"
        assert status.is_success is True

    def test_fidelity_status_failure(self):
        status = FidelityStatus.model_validate({"code": 1400, "message": "Unauthorized"})
        assert status.code == 1400
        assert status.is_success is False

    def test_fidelity_status_optional_fields_default_none(self):
        status = FidelityStatus.model_validate({"code": 1200, "message": "OK"})
        assert status.request_identifier is None
        assert status.context is None

    def test_fidelity_status_optional_fields_parsed(self):
        status = FidelityStatus.model_validate(
            {
                "code": 1200,
                "message": "OK",
                "requestIdentifier": "abc-123",
                "Context": "login",
            }
        )
        assert status.request_identifier == "abc-123"
        assert status.context == "login"


# ---------------------------------------------------------------------------
# LoginResponse
# ---------------------------------------------------------------------------

class TestLoginResponse:
    def _full_payload(self, code: int = 1200, message: str = "Success") -> dict:
        return {
            "responseBaseInfo": {
                "sessionTokens": {"token": "abc"},
                "status": {"code": code, "message": message},
                "links": [],
            },
            "authenticators": [],
            "location": "/dashboard",
            "referenceId": "ref-001",
            "callbacks": [],
        }

    def test_login_response_parses(self):
        resp = LoginResponse.model_validate(self._full_payload())
        assert resp.status.code == 1200
        assert resp.status.is_success is True
        assert resp.location == "/dashboard"
        assert resp.reference_id == "ref-001"

    def test_login_response_failure_status(self):
        resp = LoginResponse.model_validate(self._full_payload(code=1400, message="Bad credentials"))
        assert resp.status.is_success is False
        assert resp.status.message == "Bad credentials"

    def test_login_response_status_delegates_to_response_base_info(self):
        resp = LoginResponse.model_validate(self._full_payload())
        assert resp.status is resp.response_base_info.status

    def test_login_response_optional_fields_default(self):
        payload = {
            "responseBaseInfo": {
                "status": {"code": 1200, "message": "OK"},
                "links": [],
            }
        }
        resp = LoginResponse.model_validate(payload)
        assert resp.location is None
        assert resp.reference_id is None
        assert resp.authenticators == []
        assert resp.callbacks == []

    def test_login_response_uses_fidelity_response_fixture(self, fidelity_response):
        """Ensure conftest fixture produces a valid LoginResponse."""
        payload = fidelity_response("Success", code=1200)
        resp = LoginResponse.model_validate(payload)
        assert resp.status.is_success is True

    def test_login_response_fixture_failure(self, fidelity_response):
        payload = fidelity_response("Error", code=1400)
        resp = LoginResponse.model_validate(payload)
        assert resp.status.is_success is False
