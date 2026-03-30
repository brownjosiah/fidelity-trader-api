"""Tests for pydantic models: FidelityStatus, LoginResponse, Account, Balance, Position."""
import pytest

from fidelity_trader.models.auth import FidelityStatus, LoginResponse, ResponseBaseInfo
from fidelity_trader.models.account import Account, Balance, Position, _parse_float, _parse_int


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


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

class TestAccount:
    def _account_payload(self) -> dict:
        return {
            "acctNum": "X12345678",
            "acctType": "BROKERAGE",
            "acct_sub_type": "INDIVIDUAL",
            "acct_sub_type_desc": "Individual Brokerage",
            "is_retirement": False,
            "preferenceDetail": {
                "acctNickName": "My Brokerage",
            },
            "acctTradeAttrDetail": {
                "optionLevel": "3",
                "mrgnEstb": "Y",
                "optionEstb": "Y",
            },
        }

    def test_account_parses(self):
        acct = Account.model_validate(self._account_payload())
        assert acct.acct_num == "X12345678"
        assert acct.acct_type == "BROKERAGE"
        assert acct.nickname == "My Brokerage"
        assert acct.option_level == 3
        assert acct.is_margin is True
        assert acct.is_options_enabled is True
        assert acct.is_retirement is False

    def test_account_no_nested_details(self):
        acct = Account.model_validate({"acctNum": "Y99999999", "acctType": "IRA"})
        assert acct.acct_num == "Y99999999"
        assert acct.nickname is None
        assert acct.option_level is None
        assert acct.is_margin is None

    def test_account_preference_detail_empty(self):
        payload = {
            "acctNum": "Z00000001",
            "acctType": "BROKERAGE",
            "preferenceDetail": {},
            "acctTradeAttrDetail": {},
        }
        acct = Account.model_validate(payload)
        assert acct.nickname is None
        assert acct.option_level is None

    def test_account_mrgnEstb_false(self):
        payload = {
            "acctNum": "Z00000002",
            "acctType": "BROKERAGE",
            "acctTradeAttrDetail": {
                "mrgnEstb": "N",
                "optionEstb": "N",
                "optionLevel": "0",
            },
        }
        acct = Account.model_validate(payload)
        assert acct.is_margin is False
        assert acct.is_options_enabled is False
        assert acct.option_level == 0


# ---------------------------------------------------------------------------
# Balance
# ---------------------------------------------------------------------------

class TestBalance:
    def test_balance_parses(self):
        data = {
            "totalAcctVal": "125000.50",
            "cashAvailForTrade": "10000.00",
            "intraDayBP": "20000.00",
            "mrgnBP": "50000.00",
            "nonMrgnBP": "10000.00",
            "isMrgnAcct": True,
        }
        bal = Balance.model_validate(data)
        assert bal.total_account_value == pytest.approx(125000.50)
        assert bal.cash_available == pytest.approx(10000.00)
        assert bal.intraday_buying_power == pytest.approx(20000.00)
        assert bal.margin_buying_power == pytest.approx(50000.00)
        assert bal.non_margin_buying_power == pytest.approx(10000.00)
        assert bal.is_margin_account is True

    def test_balance_comma_separated_values(self):
        data = {"totalAcctVal": "1,250,000.75", "isMrgnAcct": False}
        bal = Balance.model_validate(data)
        assert bal.total_account_value == pytest.approx(1250000.75)

    def test_balance_sentinel_strings(self):
        data = {
            "totalAcctVal": "--",
            "cashAvailForTrade": "N/A",
            "intraDayBP": "",
        }
        bal = Balance.model_validate(data)
        assert bal.total_account_value is None
        assert bal.cash_available is None
        assert bal.intraday_buying_power is None

    def test_balance_all_none(self):
        bal = Balance.model_validate({})
        assert bal.total_account_value is None
        assert bal.is_margin_account is None


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------

class TestPosition:
    def _position_payload(self) -> dict:
        return {
            "symbol": "AAPL",
            "securityType": "EQ",
            "quantity": "10",
            "lastPrice": "182.50",
            "marketValue": "1,825.00",
            "costBasis": "1,500.00",
            "gainLoss": "325.00",
            "gainLossPct": "21.67",
        }

    def test_position_parses(self):
        pos = Position.model_validate(self._position_payload())
        assert pos.symbol == "AAPL"
        assert pos.security_type == "EQ"
        assert pos.quantity == pytest.approx(10.0)
        assert pos.last_price == pytest.approx(182.50)
        assert pos.market_value == pytest.approx(1825.00)
        assert pos.cost_basis == pytest.approx(1500.00)
        assert pos.gain_loss == pytest.approx(325.00)
        assert pos.gain_loss_pct == pytest.approx(21.67)

    def test_position_sentinel_values(self):
        data = {
            "symbol": "TSLA",
            "securityType": "EQ",
            "quantity": "--",
            "lastPrice": "N/A",
            "marketValue": "",
        }
        pos = Position.model_validate(data)
        assert pos.quantity is None
        assert pos.last_price is None
        assert pos.market_value is None

    def test_position_negative_gain_loss(self):
        data = {
            "symbol": "META",
            "securityType": "EQ",
            "quantity": "5",
            "lastPrice": "400.00",
            "marketValue": "2,000.00",
            "costBasis": "2,500.00",
            "gainLoss": "-500.00",
            "gainLossPct": "-20.00",
        }
        pos = Position.model_validate(data)
        assert pos.gain_loss == pytest.approx(-500.00)
        assert pos.gain_loss_pct == pytest.approx(-20.00)
