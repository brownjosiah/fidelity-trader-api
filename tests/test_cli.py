"""Tests for the ft CLI tool."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from fidelity_trader.cli import app
from fidelity_trader.cli._config import get_config_dir, SESSION_FILE_NAME
from tests.conftest import strip_ansi
from fidelity_trader.cli._errors import handle_errors
from fidelity_trader.cli._output import _format_currency, _format_number, _format_pct
from fidelity_trader.cli._session import (
    delete_session,
    load_session_data,
    save_session,
)
from fidelity_trader.exceptions import (
    APIError,
    AuthenticationError,
    CSRFTokenError,
    SessionExpiredError,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Help output tests
# ---------------------------------------------------------------------------


class TestHelpOutput:
    def test_root_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "Fidelity Trader+" in output
        assert "login" in output
        assert "positions" in output

    def test_login_help(self):
        result = runner.invoke(app, ["login", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--username" in output
        assert "--password" in output

    def test_logout_help(self):
        result = runner.invoke(app, ["logout", "--help"])
        assert result.exit_code == 0

    def test_status_help(self):
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0

    def test_accounts_help(self):
        result = runner.invoke(app, ["accounts", "--help"])
        assert result.exit_code == 0

    def test_positions_help(self):
        result = runner.invoke(app, ["positions", "--help"])
        assert result.exit_code == 0
        assert "ACCOUNT" in strip_ansi(result.output)

    def test_balances_help(self):
        result = runner.invoke(app, ["balances", "--help"])
        assert result.exit_code == 0
        assert "ACCOUNT" in strip_ansi(result.output)


# ---------------------------------------------------------------------------
# Config directory tests
# ---------------------------------------------------------------------------


class TestConfig:
    def test_get_config_dir_returns_path(self, tmp_path, monkeypatch):
        if os.name == "nt":
            monkeypatch.setenv("APPDATA", str(tmp_path))
        else:
            monkeypatch.setenv("HOME", str(tmp_path))

        config_dir = get_config_dir()
        assert config_dir.exists()
        assert config_dir.name == "ft"


# ---------------------------------------------------------------------------
# Session save/load roundtrip tests
# ---------------------------------------------------------------------------


class TestSession:
    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        """Write cookies, read them back."""
        # Point config dir to tmp
        monkeypatch.setattr(
            "fidelity_trader.cli._session.get_config_dir",
            lambda: tmp_path,
        )

        # Create a mock httpx client with cookies
        mock_client = MagicMock()
        cookie1 = MagicMock()
        cookie1.name = "ATC"
        cookie1.value = "abc123"
        cookie2 = MagicMock()
        cookie2.name = "FC"
        cookie2.value = "def456"
        mock_client.cookies.jar = [cookie1, cookie2]

        # Save
        save_session(mock_client)

        # Verify file exists
        session_file = tmp_path / SESSION_FILE_NAME
        assert session_file.exists()

        # Load
        data = load_session_data()
        assert data is not None
        assert data["version"] == 1
        assert data["cookies"]["ATC"] == "abc123"
        assert data["cookies"]["FC"] == "def456"
        assert "created_at" in data

    def test_load_missing_session(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "fidelity_trader.cli._session.get_config_dir",
            lambda: tmp_path,
        )
        data = load_session_data()
        assert data is None

    def test_load_corrupt_session(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "fidelity_trader.cli._session.get_config_dir",
            lambda: tmp_path,
        )
        (tmp_path / SESSION_FILE_NAME).write_text("not json", encoding="utf-8")
        data = load_session_data()
        assert data is None

    def test_delete_session(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "fidelity_trader.cli._session.get_config_dir",
            lambda: tmp_path,
        )
        session_file = tmp_path / SESSION_FILE_NAME
        session_file.write_text("{}", encoding="utf-8")
        assert delete_session() is True
        assert not session_file.exists()

    def test_delete_missing_session(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "fidelity_trader.cli._session.get_config_dir",
            lambda: tmp_path,
        )
        assert delete_session() is False


# ---------------------------------------------------------------------------
# Error handler decorator tests
# ---------------------------------------------------------------------------


class TestErrorHandler:
    def test_catches_authentication_error(self):
        @handle_errors
        def bad():
            raise AuthenticationError("wrong password")

        with pytest.raises(SystemExit, match="1"):
            bad()

    def test_catches_session_expired_error(self):
        @handle_errors
        def bad():
            raise SessionExpiredError()

        with pytest.raises(SystemExit, match="1"):
            bad()

    def test_catches_csrf_token_error(self):
        @handle_errors
        def bad():
            raise CSRFTokenError()

        with pytest.raises(SystemExit, match="1"):
            bad()

    def test_catches_api_error(self):
        @handle_errors
        def bad():
            raise APIError("something went wrong")

        with pytest.raises(SystemExit, match="1"):
            bad()

    def test_catches_file_not_found(self):
        @handle_errors
        def bad():
            raise FileNotFoundError("no session")

        with pytest.raises(SystemExit, match="1"):
            bad()

    def test_catches_keyboard_interrupt(self):
        @handle_errors
        def bad():
            raise KeyboardInterrupt()

        with pytest.raises(SystemExit, match="0"):
            bad()

    def test_passes_through_normal_return(self):
        @handle_errors
        def good():
            return 42

        assert good() == 42


# ---------------------------------------------------------------------------
# Output formatting tests
# ---------------------------------------------------------------------------


class TestOutputFormatting:
    def test_format_currency_positive(self):
        result = _format_currency(1234.56)
        assert "$1,234.56" in result
        assert "green" in result

    def test_format_currency_negative(self):
        result = _format_currency(-500.00)
        assert "$500.00" in result
        assert "red" in result

    def test_format_currency_zero(self):
        result = _format_currency(0.0)
        assert "$0.00" in result

    def test_format_currency_none(self):
        assert _format_currency(None) == "--"

    def test_format_number_positive(self):
        result = _format_number(100.5)
        assert "100.50" in result
        assert "green" in result

    def test_format_number_negative(self):
        result = _format_number(-42.1)
        assert "42.10" in result
        assert "red" in result

    def test_format_number_none(self):
        assert _format_number(None) == "--"

    def test_format_pct_positive(self):
        result = _format_pct(5.25)
        assert "5.25%" in result
        assert "green" in result

    def test_format_pct_negative(self):
        result = _format_pct(-3.10)
        assert "3.10%" in result
        assert "red" in result

    def test_format_pct_none(self):
        assert _format_pct(None) == "--"


# ---------------------------------------------------------------------------
# Command integration tests (with mocked SDK)
# ---------------------------------------------------------------------------


class TestLoginCommand:
    @patch("fidelity_trader.cli._auth.FidelityClient")
    @patch("fidelity_trader.cli._auth.save_session")
    def test_login_with_flags(self, mock_save, mock_client_cls):
        mock_client = MagicMock()
        mock_client.login.return_value = {"status": "ok"}
        mock_client.accounts.discover_accounts.return_value = MagicMock(accounts=[])
        mock_client_cls.return_value = mock_client

        result = runner.invoke(app, ["login", "--username", "user", "--password", "pass"])
        assert result.exit_code == 0
        assert "Login successful" in strip_ansi(result.output)
        mock_client.login.assert_called_once_with("user", "pass", totp_secret=None)
        mock_save.assert_called_once()

    @patch("fidelity_trader.cli._auth.FidelityClient")
    @patch("fidelity_trader.cli._auth.save_session")
    def test_login_with_env_vars(self, mock_save, mock_client_cls, monkeypatch):
        monkeypatch.setenv("FIDELITY_USERNAME", "envuser")
        monkeypatch.setenv("FIDELITY_PASSWORD", "envpass")
        monkeypatch.setenv("FIDELITY_TOTP_SECRET", "totp123")

        mock_client = MagicMock()
        mock_client.login.return_value = {"status": "ok"}
        mock_client.accounts.discover_accounts.return_value = MagicMock(accounts=[])
        mock_client_cls.return_value = mock_client

        result = runner.invoke(app, ["login"])
        assert result.exit_code == 0
        mock_client.login.assert_called_once_with("envuser", "envpass", totp_secret="totp123")


class TestLogoutCommand:
    @patch("fidelity_trader.cli._auth.get_client")
    @patch("fidelity_trader.cli._auth.delete_session", return_value=True)
    def test_logout_success(self, mock_delete, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["logout"])
        assert result.exit_code == 0
        assert "Logged out" in strip_ansi(result.output)

    @patch("fidelity_trader.cli._auth.get_client")
    @patch("fidelity_trader.cli._auth.delete_session", return_value=False)
    def test_logout_no_session(self, mock_delete, mock_get_client):
        mock_get_client.side_effect = FileNotFoundError()
        result = runner.invoke(app, ["logout"])
        assert result.exit_code == 0
        assert "No active session" in strip_ansi(result.output)


class TestAccountsCommand:
    @patch("fidelity_trader.cli._portfolio.get_client")
    def test_accounts_table_output(self, mock_get_client):
        mock_client = MagicMock()
        mock_acct = MagicMock()
        mock_acct.acct_num = "Z12345678"
        mock_acct.acct_type = "Brokerage"
        mock_acct.acct_sub_type_desc = "Individual"
        mock_acct.preference_detail = MagicMock(name="My Account")
        mock_acct.acct_trade_attr_detail = MagicMock(mrgn_estb=True, option_level=4)
        mock_client.accounts.discover_accounts.return_value = MagicMock(accounts=[mock_acct])
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["accounts"])
        assert result.exit_code == 0
        assert "Z12345678" in strip_ansi(result.output)

    @patch("fidelity_trader.cli._portfolio.get_client")
    def test_accounts_json_output(self, mock_get_client):
        mock_client = MagicMock()
        mock_acct = MagicMock()
        mock_acct.model_dump.return_value = {"acctNum": "Z12345678", "acctType": "Brokerage"}
        mock_client.accounts.discover_accounts.return_value = MagicMock(accounts=[mock_acct])
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["--format", "json", "accounts"])
        assert result.exit_code == 0
        assert "Z12345678" in strip_ansi(result.output)


class TestPositionsCommand:
    @patch("fidelity_trader.cli._portfolio.get_client")
    @patch("fidelity_trader.cli._portfolio.resolve_account", return_value="Z12345678")
    def test_positions_table_output(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()
        mock_pos = MagicMock()
        mock_pos.symbol = "AAPL"
        mock_pos.security_description = "APPLE INC"
        mock_pos.quantity = 100.0
        mock_pos.price_detail = MagicMock(last_price=175.50, last_price_chg=2.30, last_price_chg_pct=1.33)
        mock_pos.market_val_detail = MagicMock(
            market_val=17550.0, total_gain_loss=3550.0, total_gain_loss_pct=25.36
        )
        mock_pos.cost_basis_detail = MagicMock(avg_cost_per_share=140.0)

        mock_acct = MagicMock()
        mock_acct.acct_num = "Z12345678"
        mock_acct.positions = [mock_pos]

        mock_client.positions.get_positions.return_value = MagicMock(accounts=[mock_acct])
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["positions", "Z12345678"])
        assert result.exit_code == 0
        assert "AAPL" in strip_ansi(result.output)


class TestBalancesCommand:
    @patch("fidelity_trader.cli._portfolio.get_client")
    @patch("fidelity_trader.cli._portfolio.resolve_account", return_value="Z12345678")
    def test_balances_table_output(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()

        mock_acct_val = MagicMock(net_worth=50000.0, net_worth_chg=500.0, market_val=48000.0, market_val_chg=480.0)
        mock_cash = MagicMock(held_in_cash=2000.0, core_balance=2000.0)
        mock_bp = MagicMock(cash=25000.0, cash_chg=250.0, margin=50000.0, margin_chg=500.0, day_trade=None)
        mock_withdraw = MagicMock(cash_only=1500.0)
        mock_balance_detail = MagicMock(
            acct_val_detail=mock_acct_val,
            cash_detail=mock_cash,
            buying_power_detail=mock_bp,
            available_to_withdraw_detail=mock_withdraw,
        )

        mock_acct = MagicMock()
        mock_acct.acct_num = "Z12345678"
        mock_acct.recent_balance_detail = mock_balance_detail
        mock_acct.intraday_balance_detail = None
        mock_acct.close_balance_detail = None

        mock_client.balances.get_balances.return_value = MagicMock(accounts=[mock_acct])
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["balances", "Z12345678"])
        assert result.exit_code == 0
        assert "Z12345678" in strip_ansi(result.output)
