"""Tests for AccountsAPI: discover_accounts, get_balances, get_positions."""
import pytest
import httpx
from unittest.mock import MagicMock, patch

from fidelity_trader.accounts import AccountsAPI
from fidelity_trader.models.account import Account, Balance, Position
from fidelity_trader.exceptions import APIError
from fidelity_trader._http import BASE_URL


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_DUMMY_REQUEST = httpx.Request("POST", "https://digital.fidelity.com/dummy")


def _make_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    """Build a minimal httpx.Response from a dict, with a request attached."""
    resp = httpx.Response(status_code, json=json_data)
    resp.request = _DUMMY_REQUEST
    return resp


def _make_error_response(status_code: int) -> httpx.Response:
    """Build an error httpx.Response with a request attached."""
    resp = httpx.Response(status_code)
    resp.request = _DUMMY_REQUEST
    return resp


def _accounts_payload() -> dict:
    return {
        "acctDetails": [
            {
                "acctNum": "X12345678",
                "acctType": "BROKERAGE",
                "acct_sub_type": "INDIVIDUAL",
                "acct_sub_type_desc": "Individual Brokerage",
                "is_retirement": False,
                "preferenceDetail": {"acctNickName": "My Brokerage"},
                "acctTradeAttrDetail": {
                    "optionLevel": "3",
                    "mrgnEstb": "Y",
                    "optionEstb": "Y",
                },
            },
            {
                "acctNum": "Y99999999",
                "acctType": "IRA",
                "acct_sub_type": "ROTH",
                "acct_sub_type_desc": "Roth IRA",
                "is_retirement": True,
                "preferenceDetail": {"acctNickName": "Roth IRA"},
                "acctTradeAttrDetail": {
                    "optionLevel": "1",
                    "mrgnEstb": "N",
                    "optionEstb": "N",
                },
            },
        ]
    }


def _balance_payload() -> dict:
    return {
        "totalAcctVal": "125000.50",
        "cashAvailForTrade": "10000.00",
        "intraDayBP": "20000.00",
        "mrgnBP": "50000.00",
        "nonMrgnBP": "10000.00",
        "isMrgnAcct": True,
    }


def _positions_payload() -> dict:
    return {
        "positionDetails": [
            {
                "symbol": "AAPL",
                "securityType": "EQ",
                "quantity": "10",
                "lastPrice": "182.50",
                "marketValue": "1825.00",
                "costBasis": "1500.00",
                "gainLoss": "325.00",
                "gainLossPct": "21.67",
            },
            {
                "symbol": "MSFT",
                "securityType": "EQ",
                "quantity": "5",
                "lastPrice": "400.00",
                "marketValue": "2000.00",
                "costBasis": "1800.00",
                "gainLoss": "200.00",
                "gainLossPct": "11.11",
            },
        ]
    }


# ---------------------------------------------------------------------------
# discover_accounts
# ---------------------------------------------------------------------------

class TestDiscoverAccounts:
    def test_discover_accounts_parses_two_accounts(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = _make_response(_accounts_payload())

        api = AccountsAPI(http=mock_client, csrf_token="tok123")
        accounts = api.discover_accounts()

        assert len(accounts) == 2
        mock_client.post.assert_called_once_with(
            f"{BASE_URL}/ftgw/digital/pico/api/v1/context/account",
            json={},
        )

    def test_discover_accounts_first_account_fields(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = _make_response(_accounts_payload())

        api = AccountsAPI(http=mock_client, csrf_token="tok123")
        accounts = api.discover_accounts()

        first = accounts[0]
        assert first.acct_num == "X12345678"
        assert first.acct_type == "BROKERAGE"
        assert first.nickname == "My Brokerage"
        assert first.option_level == 3
        assert first.is_margin is True
        assert first.is_options_enabled is True
        assert first.is_retirement is False

    def test_discover_accounts_second_account_fields(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = _make_response(_accounts_payload())

        api = AccountsAPI(http=mock_client, csrf_token="tok123")
        accounts = api.discover_accounts()

        second = accounts[1]
        assert second.acct_num == "Y99999999"
        assert second.acct_type == "IRA"
        assert second.nickname == "Roth IRA"
        assert second.is_retirement is True
        assert second.is_margin is False

    def test_discover_accounts_empty_acct_details(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = _make_response({"acctDetails": []})

        api = AccountsAPI(http=mock_client, csrf_token="tok123")
        accounts = api.discover_accounts()

        assert accounts == []

    def test_discover_accounts_missing_acct_details_key(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = _make_response({})

        api = AccountsAPI(http=mock_client, csrf_token="tok123")
        accounts = api.discover_accounts()

        assert accounts == []

    def test_discover_accounts_stores_internally(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = _make_response(_accounts_payload())

        api = AccountsAPI(http=mock_client)
        api.discover_accounts()

        assert len(api._accounts) == 2

    def test_discover_accounts_http_error_raises(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = _make_error_response(500)

        api = AccountsAPI(http=mock_client)
        with pytest.raises(httpx.HTTPStatusError):
            api.discover_accounts()


# ---------------------------------------------------------------------------
# get_account
# ---------------------------------------------------------------------------

class TestGetAccount:
    def test_get_account_found(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = _make_response(_accounts_payload())

        api = AccountsAPI(http=mock_client)
        acct = api.get_account("X12345678")

        assert acct.acct_num == "X12345678"

    def test_get_account_triggers_discover_when_empty(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = _make_response(_accounts_payload())

        api = AccountsAPI(http=mock_client)
        assert api._accounts == []
        api.get_account("X12345678")

        mock_client.post.assert_called_once()

    def test_get_account_not_found_raises(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = _make_response(_accounts_payload())

        api = AccountsAPI(http=mock_client)
        with pytest.raises(APIError, match="ZZZZZZZ not found"):
            api.get_account("ZZZZZZZ")


# ---------------------------------------------------------------------------
# get_balances
# ---------------------------------------------------------------------------

class TestGetBalances:
    def _setup_api_with_accounts(self) -> tuple[AccountsAPI, MagicMock]:
        """Return an AccountsAPI pre-loaded with accounts and a mock client."""
        mock_client = MagicMock(spec=httpx.Client)
        api = AccountsAPI(http=mock_client, csrf_token="csrf-abc")
        # Pre-load accounts to avoid a second POST call for discover
        api._accounts = [
            Account.model_validate(acct)
            for acct in _accounts_payload()["acctDetails"]
        ]
        return api, mock_client

    def test_get_balances_returns_balance_model(self):
        api, mock_client = self._setup_api_with_accounts()
        mock_client.post.return_value = _make_response(_balance_payload())

        balance = api.get_balances("X12345678")

        assert isinstance(balance, Balance)

    def test_get_balances_parses_values(self):
        api, mock_client = self._setup_api_with_accounts()
        mock_client.post.return_value = _make_response(_balance_payload())

        balance = api.get_balances("X12345678")

        assert balance.total_account_value == pytest.approx(125000.50)
        assert balance.cash_available == pytest.approx(10000.00)
        assert balance.intraday_buying_power == pytest.approx(20000.00)
        assert balance.margin_buying_power == pytest.approx(50000.00)
        assert balance.non_margin_buying_power == pytest.approx(10000.00)
        assert balance.is_margin_account is True

    def test_get_balances_sends_csrf_header(self):
        api, mock_client = self._setup_api_with_accounts()
        mock_client.post.return_value = _make_response(_balance_payload())

        api.get_balances("X12345678")

        _, kwargs = mock_client.post.call_args
        assert kwargs["headers"]["X-CSRF-TOKEN"] == "csrf-abc"

    def test_get_balances_posts_to_correct_url(self):
        api, mock_client = self._setup_api_with_accounts()
        mock_client.post.return_value = _make_response(_balance_payload())

        api.get_balances("X12345678")

        args, _ = mock_client.post.call_args
        assert args[0] == f"{BASE_URL}/ftgw/digital/trade-options/api/balances"

    def test_get_balances_no_csrf_raises(self):
        mock_client = MagicMock(spec=httpx.Client)
        api = AccountsAPI(http=mock_client, csrf_token=None)
        api._accounts = [
            Account.model_validate(acct)
            for acct in _accounts_payload()["acctDetails"]
        ]

        with pytest.raises(APIError, match="CSRF token required"):
            api.get_balances("X12345678")

    def test_get_balances_http_error_raises(self):
        api, mock_client = self._setup_api_with_accounts()
        mock_client.post.return_value = _make_error_response(403)

        with pytest.raises(httpx.HTTPStatusError):
            api.get_balances("X12345678")


# ---------------------------------------------------------------------------
# get_positions
# ---------------------------------------------------------------------------

class TestGetPositions:
    def _setup_api_with_accounts(self) -> tuple[AccountsAPI, MagicMock]:
        mock_client = MagicMock(spec=httpx.Client)
        api = AccountsAPI(http=mock_client, csrf_token="csrf-xyz")
        api._accounts = [
            Account.model_validate(acct)
            for acct in _accounts_payload()["acctDetails"]
        ]
        return api, mock_client

    def test_get_positions_returns_list(self):
        api, mock_client = self._setup_api_with_accounts()
        mock_client.post.return_value = _make_response(_positions_payload())

        positions = api.get_positions("X12345678")

        assert isinstance(positions, list)
        assert len(positions) == 2

    def test_get_positions_parses_models(self):
        api, mock_client = self._setup_api_with_accounts()
        mock_client.post.return_value = _make_response(_positions_payload())

        positions = api.get_positions("X12345678")

        assert all(isinstance(p, Position) for p in positions)

    def test_get_positions_first_position_fields(self):
        api, mock_client = self._setup_api_with_accounts()
        mock_client.post.return_value = _make_response(_positions_payload())

        positions = api.get_positions("X12345678")
        first = positions[0]

        assert first.symbol == "AAPL"
        assert first.security_type == "EQ"
        assert first.quantity == pytest.approx(10.0)
        assert first.last_price == pytest.approx(182.50)
        assert first.market_value == pytest.approx(1825.00)
        assert first.cost_basis == pytest.approx(1500.00)
        assert first.gain_loss == pytest.approx(325.00)
        assert first.gain_loss_pct == pytest.approx(21.67)

    def test_get_positions_second_position_fields(self):
        api, mock_client = self._setup_api_with_accounts()
        mock_client.post.return_value = _make_response(_positions_payload())

        positions = api.get_positions("X12345678")
        second = positions[1]

        assert second.symbol == "MSFT"
        assert second.quantity == pytest.approx(5.0)
        assert second.last_price == pytest.approx(400.00)

    def test_get_positions_sends_csrf_header(self):
        api, mock_client = self._setup_api_with_accounts()
        mock_client.post.return_value = _make_response(_positions_payload())

        api.get_positions("X12345678")

        _, kwargs = mock_client.post.call_args
        assert kwargs["headers"]["X-CSRF-TOKEN"] == "csrf-xyz"

    def test_get_positions_posts_to_correct_url(self):
        api, mock_client = self._setup_api_with_accounts()
        mock_client.post.return_value = _make_response(_positions_payload())

        api.get_positions("X12345678")

        args, _ = mock_client.post.call_args
        assert args[0] == f"{BASE_URL}/ftgw/digital/trade-options/api/positions"

    def test_get_positions_empty_response(self):
        api, mock_client = self._setup_api_with_accounts()
        mock_client.post.return_value = _make_response({"positionDetails": []})

        positions = api.get_positions("X12345678")

        assert positions == []

    def test_get_positions_missing_position_details_key(self):
        api, mock_client = self._setup_api_with_accounts()
        mock_client.post.return_value = _make_response({})

        positions = api.get_positions("X12345678")

        assert positions == []

    def test_get_positions_no_csrf_raises(self):
        mock_client = MagicMock(spec=httpx.Client)
        api = AccountsAPI(http=mock_client, csrf_token=None)
        api._accounts = [
            Account.model_validate(acct)
            for acct in _accounts_payload()["acctDetails"]
        ]

        with pytest.raises(APIError, match="CSRF token required"):
            api.get_positions("X12345678")

    def test_get_positions_http_error_raises(self):
        api, mock_client = self._setup_api_with_accounts()
        mock_client.post.return_value = _make_error_response(401)

        with pytest.raises(httpx.HTTPStatusError):
            api.get_positions("X12345678")
