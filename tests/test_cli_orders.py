"""Tests for the ft CLI order and options commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from fidelity_trader.cli import app
from tests.conftest import strip_ansi
from fidelity_trader.models.equity_order import (
    EquityOrderConfirmDetail,
    EquityEstCommissionDetail,
    EquityPreviewResponse,
    EquityPlaceResponse,
)
from fidelity_trader.models.single_option_order import (
    SingleOptionOrderConfirmDetail,
    SingleOptionEstCommissionDetail,
    SingleOptionPreviewResponse,
    SingleOptionPlaceResponse,
)
from fidelity_trader.models.cancel_order import CancelConfirmDetail, CancelResponse
from fidelity_trader.models.order import OrderStatusResponse

runner = CliRunner()


# ---------------------------------------------------------------------------
# Help output tests
# ---------------------------------------------------------------------------


class TestOrderHelpOutput:
    def test_orders_help(self):
        result = runner.invoke(app, ["orders", "--help"])
        assert result.exit_code == 0
        assert "ACCOUNT" in strip_ansi(result.output)

    def test_buy_help(self):
        result = runner.invoke(app, ["buy", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--limit" in output
        assert "--live" in output
        assert "--stop" in output
        assert "--tif" in output
        assert "SYMBOL" in output
        assert "QTY" in output

    def test_sell_help(self):
        result = runner.invoke(app, ["sell", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--limit" in output
        assert "--live" in output
        assert "SYMBOL" in output
        assert "QTY" in output

    def test_cancel_help(self):
        result = runner.invoke(app, ["cancel", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "CONF_NUM" in output
        assert "--account" in output


class TestOptionsHelpOutput:
    def test_options_help(self):
        result = runner.invoke(app, ["options", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "chain" in output
        assert "buy" in output
        assert "sell" in output

    def test_options_chain_help(self):
        result = runner.invoke(app, ["options", "chain", "--help"])
        assert result.exit_code == 0
        assert "SYMBOL" in strip_ansi(result.output)

    def test_options_buy_help(self):
        result = runner.invoke(app, ["options", "buy", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--limit" in output
        assert "--live" in output

    def test_options_sell_help(self):
        result = runner.invoke(app, ["options", "sell", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--limit" in output
        assert "--live" in output


# ---------------------------------------------------------------------------
# Root help includes new commands
# ---------------------------------------------------------------------------


class TestRootHelpIncludesOrders:
    def test_root_help_shows_order_commands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "buy" in output
        assert "sell" in output
        assert "orders" in output
        assert "cancel" in output
        assert "options" in output


# ---------------------------------------------------------------------------
# Equity buy -- dry-run (preview only)
# ---------------------------------------------------------------------------


class TestBuyDryRun:
    @patch("fidelity_trader.cli._orders.get_client")
    @patch("fidelity_trader.cli._orders.resolve_account", return_value="Z12345678")
    def test_buy_preview_dry_run(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()

        # Build a realistic preview response
        preview = EquityPreviewResponse(
            acct_num="Z12345678",
            order_confirm_detail=EquityOrderConfirmDetail(
                resp_type_code="V",
                conf_num="24A0TEST",
                acct_num="Z12345678",
                net_amount=1750.00,
                est_commission_detail=EquityEstCommissionDetail(est_commission=0.0),
            ),
        )
        mock_client.equity_orders.preview_order.return_value = preview
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["buy", "AAPL", "10", "--limit", "175.00"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "Order Preview" in output
        assert "Dry-run mode" in output
        # Should NOT have called place_order
        mock_client.equity_orders.place_order.assert_not_called()
        # get_client should have been called with live_trading=True
        mock_get_client.assert_called_once_with(live_trading=True)

    @patch("fidelity_trader.cli._orders.get_client")
    @patch("fidelity_trader.cli._orders.resolve_account", return_value="Z12345678")
    def test_buy_market_order_dry_run(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()

        preview = EquityPreviewResponse(
            acct_num="Z12345678",
            order_confirm_detail=EquityOrderConfirmDetail(
                resp_type_code="V",
                conf_num="24A0MKT1",
                acct_num="Z12345678",
                net_amount=850.00,
            ),
        )
        mock_client.equity_orders.preview_order.return_value = preview
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["buy", "MSFT", "5"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "Market" in output
        assert "Dry-run mode" in output


# ---------------------------------------------------------------------------
# Equity buy -- live mode with confirmation prompt
# ---------------------------------------------------------------------------


class TestBuyLive:
    @patch("fidelity_trader.cli._orders.get_client")
    @patch("fidelity_trader.cli._orders.resolve_account", return_value="Z12345678")
    def test_buy_live_prompts_confirmation(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()

        preview = EquityPreviewResponse(
            acct_num="Z12345678",
            order_confirm_detail=EquityOrderConfirmDetail(
                resp_type_code="V",
                conf_num="24A0LIVE",
                acct_num="Z12345678",
                net_amount=500.00,
            ),
        )
        place_resp = EquityPlaceResponse(
            acct_num="Z12345678",
            order_confirm_detail=EquityOrderConfirmDetail(
                resp_type_code="A",
                conf_num="24A0LIVE",
                acct_num="Z12345678",
            ),
        )
        mock_client.equity_orders.preview_order.return_value = preview
        mock_client.equity_orders.place_order.return_value = place_resp
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        # Answer "y" to the confirmation prompt
        result = runner.invoke(app, ["buy", "AAPL", "5", "--live"], input="y\n")
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "Order placed" in output
        assert "24A0LIVE" in output
        mock_client.equity_orders.place_order.assert_called_once()

    @patch("fidelity_trader.cli._orders.get_client")
    @patch("fidelity_trader.cli._orders.resolve_account", return_value="Z12345678")
    def test_buy_live_deny_cancels(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()

        preview = EquityPreviewResponse(
            acct_num="Z12345678",
            order_confirm_detail=EquityOrderConfirmDetail(
                resp_type_code="V",
                conf_num="24A0DENY",
                acct_num="Z12345678",
                net_amount=500.00,
            ),
        )
        mock_client.equity_orders.preview_order.return_value = preview
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        # Answer "n" to the confirmation prompt
        result = runner.invoke(app, ["buy", "AAPL", "5", "--live"], input="n\n")
        assert result.exit_code == 0
        assert "Order cancelled" in strip_ansi(result.output)
        mock_client.equity_orders.place_order.assert_not_called()

    @patch("fidelity_trader.cli._orders.get_client")
    @patch("fidelity_trader.cli._orders.resolve_account", return_value="Z12345678")
    def test_buy_live_yes_skips_prompt(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()

        preview = EquityPreviewResponse(
            acct_num="Z12345678",
            order_confirm_detail=EquityOrderConfirmDetail(
                resp_type_code="V",
                conf_num="24A0YES1",
                acct_num="Z12345678",
                net_amount=500.00,
            ),
        )
        place_resp = EquityPlaceResponse(
            acct_num="Z12345678",
            order_confirm_detail=EquityOrderConfirmDetail(
                resp_type_code="A",
                conf_num="24A0YES1",
                acct_num="Z12345678",
            ),
        )
        mock_client.equity_orders.preview_order.return_value = preview
        mock_client.equity_orders.place_order.return_value = place_resp
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        # No input needed -- --yes skips the prompt
        result = runner.invoke(app, ["buy", "AAPL", "5", "--live", "--yes"])
        assert result.exit_code == 0
        assert "Order placed" in strip_ansi(result.output)
        mock_client.equity_orders.place_order.assert_called_once()


# ---------------------------------------------------------------------------
# Equity sell -- dry-run
# ---------------------------------------------------------------------------


class TestSellDryRun:
    @patch("fidelity_trader.cli._orders.get_client")
    @patch("fidelity_trader.cli._orders.resolve_account", return_value="Z12345678")
    def test_sell_preview_dry_run(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()

        preview = EquityPreviewResponse(
            acct_num="Z12345678",
            order_confirm_detail=EquityOrderConfirmDetail(
                resp_type_code="V",
                conf_num="24A0SELL",
                acct_num="Z12345678",
                net_amount=1750.00,
            ),
        )
        mock_client.equity_orders.preview_order.return_value = preview
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["sell", "AAPL", "10", "--limit", "175.00"])
        assert result.exit_code == 0
        assert "Dry-run mode" in strip_ansi(result.output)
        mock_client.equity_orders.place_order.assert_not_called()

        # Verify the order was built with action code "S"
        call_args = mock_client.equity_orders.preview_order.call_args
        order = call_args[0][0]
        assert order.order_action_code == "S"


# ---------------------------------------------------------------------------
# Cancel order
# ---------------------------------------------------------------------------


class TestCancelCommand:
    @patch("fidelity_trader.cli._orders.get_client")
    @patch("fidelity_trader.cli._orders.resolve_account", return_value="Z12345678")
    def test_cancel_success(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()

        cancel_resp = CancelResponse(
            cancel_confirm_detail=[
                CancelConfirmDetail(
                    resp_type_code="A",
                    conf_num="24A0CNCL",
                    acct_num="Z12345678",
                )
            ]
        )
        mock_client.cancel_order.cancel_order.return_value = cancel_resp
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["cancel", "24A0CNCL"])
        assert result.exit_code == 0
        assert "cancelled" in strip_ansi(result.output)
        # Cancel does not require live_trading -- verify get_client() called without it
        mock_get_client.assert_called_once_with()


# ---------------------------------------------------------------------------
# Orders list
# ---------------------------------------------------------------------------


class TestOrdersCommand:
    @patch("fidelity_trader.cli._orders.get_client")
    @patch("fidelity_trader.cli._orders.resolve_account", return_value="Z12345678")
    def test_orders_empty(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()

        resp = OrderStatusResponse(account_summaries=[], orders=[])
        mock_client.order_status.get_order_status.return_value = resp
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["orders"])
        assert result.exit_code == 0
        assert "No open or recent orders" in strip_ansi(result.output)


# ---------------------------------------------------------------------------
# Options chain
# ---------------------------------------------------------------------------


class TestOptionsChainCommand:
    @patch("fidelity_trader.cli._options.get_client")
    def test_chain_empty(self, mock_get_client):
        mock_client = MagicMock()

        # Use a mock that behaves like an OptionChainResponse dataclass
        chain_resp = MagicMock()
        chain_resp.symbol = "AAPL"
        chain_resp.calls = []
        chain_resp.puts = []
        mock_client.option_chain.get_option_chain.return_value = chain_resp
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["options", "chain", "AAPL"])
        assert result.exit_code == 0
        assert "No options found" in strip_ansi(result.output)


# ---------------------------------------------------------------------------
# Options buy -- dry-run
# ---------------------------------------------------------------------------


class TestOptionsBuyDryRun:
    @patch("fidelity_trader.cli._options.get_client")
    @patch("fidelity_trader.cli._options.resolve_account", return_value="Z12345678")
    def test_options_buy_dry_run(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()

        preview = SingleOptionPreviewResponse(
            acct_num="Z12345678",
            order_confirm_detail=SingleOptionOrderConfirmDetail(
                resp_type_code="V",
                conf_num="24A0OPT1",
                acct_num="Z12345678",
                net_amount=250.00,
                est_commission_detail=SingleOptionEstCommissionDetail(est_commission=0.65),
            ),
        )
        mock_client.single_option_orders.preview_order.return_value = preview
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, [
            "options", "buy", "AAPL250418C00170000", "1", "--limit", "2.50",
        ])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "Option Order Preview" in output
        assert "Dry-run mode" in output
        mock_client.single_option_orders.place_order.assert_not_called()

        # Verify the order was built with action code "BC" (Buy Call)
        call_args = mock_client.single_option_orders.preview_order.call_args
        order = call_args[0][0]
        assert order.order_action_code == "BC"

    @patch("fidelity_trader.cli._options.get_client")
    @patch("fidelity_trader.cli._options.resolve_account", return_value="Z12345678")
    def test_options_buy_put_dry_run(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()

        preview = SingleOptionPreviewResponse(
            acct_num="Z12345678",
            order_confirm_detail=SingleOptionOrderConfirmDetail(
                resp_type_code="V",
                conf_num="24A0OPT2",
                acct_num="Z12345678",
                net_amount=150.00,
            ),
        )
        mock_client.single_option_orders.preview_order.return_value = preview
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, [
            "options", "buy", "AAPL250418P00170000", "1", "--limit", "1.50",
        ])
        assert result.exit_code == 0
        assert "Dry-run mode" in strip_ansi(result.output)

        # Verify action code is "BP" (Buy Put)
        call_args = mock_client.single_option_orders.preview_order.call_args
        order = call_args[0][0]
        assert order.order_action_code == "BP"


# ---------------------------------------------------------------------------
# Options sell -- dry-run
# ---------------------------------------------------------------------------


class TestOptionsSellDryRun:
    @patch("fidelity_trader.cli._options.get_client")
    @patch("fidelity_trader.cli._options.resolve_account", return_value="Z12345678")
    def test_options_sell_call_dry_run(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()

        preview = SingleOptionPreviewResponse(
            acct_num="Z12345678",
            order_confirm_detail=SingleOptionOrderConfirmDetail(
                resp_type_code="V",
                conf_num="24A0SC01",
                acct_num="Z12345678",
                net_amount=250.00,
            ),
        )
        mock_client.single_option_orders.preview_order.return_value = preview
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, [
            "options", "sell", "AAPL250418C00170000", "1", "--limit", "2.50",
        ])
        assert result.exit_code == 0
        assert "Dry-run mode" in strip_ansi(result.output)

        # Verify action code is "SC" (Sell Call)
        call_args = mock_client.single_option_orders.preview_order.call_args
        order = call_args[0][0]
        assert order.order_action_code == "SC"


# ---------------------------------------------------------------------------
# Price type resolution
# ---------------------------------------------------------------------------


class TestPriceTypeResolution:
    """Verify that CLI flags map to the correct Fidelity priceTypeCode."""

    @patch("fidelity_trader.cli._orders.get_client")
    @patch("fidelity_trader.cli._orders.resolve_account", return_value="Z12345678")
    def test_market_order(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()
        preview = EquityPreviewResponse(
            acct_num="Z12345678",
            order_confirm_detail=EquityOrderConfirmDetail(
                resp_type_code="V", conf_num="MKT1", acct_num="Z12345678",
            ),
        )
        mock_client.equity_orders.preview_order.return_value = preview
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        runner.invoke(app, ["buy", "AAPL", "10"])
        order = mock_client.equity_orders.preview_order.call_args[0][0]
        assert order.price_type_code == "M"
        assert order.limit_price is None

    @patch("fidelity_trader.cli._orders.get_client")
    @patch("fidelity_trader.cli._orders.resolve_account", return_value="Z12345678")
    def test_limit_order(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()
        preview = EquityPreviewResponse(
            acct_num="Z12345678",
            order_confirm_detail=EquityOrderConfirmDetail(
                resp_type_code="V", conf_num="LMT1", acct_num="Z12345678",
            ),
        )
        mock_client.equity_orders.preview_order.return_value = preview
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        runner.invoke(app, ["buy", "AAPL", "10", "--limit", "175.00"])
        order = mock_client.equity_orders.preview_order.call_args[0][0]
        assert order.price_type_code == "L"
        assert order.limit_price == 175.00

    @patch("fidelity_trader.cli._orders.get_client")
    @patch("fidelity_trader.cli._orders.resolve_account", return_value="Z12345678")
    def test_stop_order(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()
        preview = EquityPreviewResponse(
            acct_num="Z12345678",
            order_confirm_detail=EquityOrderConfirmDetail(
                resp_type_code="V", conf_num="STP1", acct_num="Z12345678",
            ),
        )
        mock_client.equity_orders.preview_order.return_value = preview
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        runner.invoke(app, ["buy", "AAPL", "10", "--stop", "160.00"])
        order = mock_client.equity_orders.preview_order.call_args[0][0]
        assert order.price_type_code == "S"

    @patch("fidelity_trader.cli._orders.get_client")
    @patch("fidelity_trader.cli._orders.resolve_account", return_value="Z12345678")
    def test_stop_limit_order(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()
        preview = EquityPreviewResponse(
            acct_num="Z12345678",
            order_confirm_detail=EquityOrderConfirmDetail(
                resp_type_code="V", conf_num="SL01", acct_num="Z12345678",
            ),
        )
        mock_client.equity_orders.preview_order.return_value = preview
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        runner.invoke(app, ["buy", "AAPL", "10", "--limit", "165.00", "--stop", "160.00"])
        order = mock_client.equity_orders.preview_order.call_args[0][0]
        assert order.price_type_code == "SL"
        assert order.limit_price == 165.00

    @patch("fidelity_trader.cli._orders.get_client")
    @patch("fidelity_trader.cli._orders.resolve_account", return_value="Z12345678")
    def test_gtc_tif(self, mock_resolve, mock_get_client):
        mock_client = MagicMock()
        preview = EquityPreviewResponse(
            acct_num="Z12345678",
            order_confirm_detail=EquityOrderConfirmDetail(
                resp_type_code="V", conf_num="GTC1", acct_num="Z12345678",
            ),
        )
        mock_client.equity_orders.preview_order.return_value = preview
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        runner.invoke(app, ["buy", "AAPL", "10", "--tif", "gtc"])
        order = mock_client.equity_orders.preview_order.call_args[0][0]
        assert order.tif_code == "G"
