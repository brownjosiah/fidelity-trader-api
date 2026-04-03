"""Tests for CLI Phase 3: market data, research, and stream commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from fidelity_trader.cli import app
from tests.conftest import strip_ansi

runner = CliRunner()


# ---------------------------------------------------------------------------
# Help output tests
# ---------------------------------------------------------------------------


class TestHelpOutput:
    def test_quote_help(self):
        result = runner.invoke(app, ["quote", "--help"])
        assert result.exit_code == 0
        assert "SYMBOLS" in strip_ansi(result.output)

    def test_chart_help(self):
        result = runner.invoke(app, ["chart", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--bars" in output
        assert "--days" in output

    def test_search_help(self):
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "QUERY" in strip_ansi(result.output)

    def test_earnings_help(self):
        result = runner.invoke(app, ["earnings", "--help"])
        assert result.exit_code == 0
        assert "SYMBOLS" in strip_ansi(result.output)

    def test_dividends_help(self):
        result = runner.invoke(app, ["dividends", "--help"])
        assert result.exit_code == 0
        assert "SYMBOLS" in strip_ansi(result.output)

    def test_stream_help(self):
        result = runner.invoke(app, ["stream", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--fields" in output
        assert "SYMBOLS" in output


# ---------------------------------------------------------------------------
# Quote command tests
# ---------------------------------------------------------------------------


class TestQuoteCommand:
    @patch("fidelity_trader.cli._market_data.get_client")
    def test_quote_table_output(self, mock_get_client):
        mock_client = MagicMock()

        mock_symbol_info = MagicMock()
        mock_symbol_info.identifier = "AAPL"
        mock_symbol_info.last_trade = 175.50
        mock_symbol_info.net_change = 2.30
        mock_symbol_info.net_change_pct = 1.33
        mock_symbol_info.day_open = 173.20
        mock_symbol_info.day_high = 176.00
        mock_symbol_info.day_low = 172.80
        mock_symbol_info.previous_close = 173.20

        mock_chart_resp = MagicMock()
        mock_chart_resp.symbol_info = mock_symbol_info
        mock_client.chart.get_chart.return_value = mock_chart_resp

        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["quote", "AAPL"])
        assert result.exit_code == 0
        assert "AAPL" in strip_ansi(result.output)

    @patch("fidelity_trader.cli._market_data.get_client")
    def test_quote_multiple_symbols(self, mock_get_client):
        mock_client = MagicMock()

        def make_chart_resp(symbol):
            info = MagicMock()
            info.identifier = symbol
            info.last_trade = 100.0
            info.net_change = 1.0
            info.net_change_pct = 1.0
            info.day_open = 99.0
            info.day_high = 101.0
            info.day_low = 98.0
            info.previous_close = 99.0
            resp = MagicMock()
            resp.symbol_info = info
            return resp

        mock_client.chart.get_chart.side_effect = [
            make_chart_resp("AAPL"),
            make_chart_resp("MSFT"),
        ]

        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["quote", "AAPL", "MSFT"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "AAPL" in output
        assert "MSFT" in output

    @patch("fidelity_trader.cli._market_data.get_client")
    def test_quote_json_output(self, mock_get_client):
        mock_client = MagicMock()

        mock_symbol_info = MagicMock()
        mock_symbol_info.identifier = "SPY"
        mock_symbol_info.last_trade = 450.0
        mock_symbol_info.net_change = -3.5
        mock_symbol_info.net_change_pct = -0.77
        mock_symbol_info.day_open = 453.5
        mock_symbol_info.day_high = 454.0
        mock_symbol_info.day_low = 449.0
        mock_symbol_info.previous_close = 453.5

        mock_chart_resp = MagicMock()
        mock_chart_resp.symbol_info = mock_symbol_info
        mock_client.chart.get_chart.return_value = mock_chart_resp

        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["--format", "json", "quote", "SPY"])
        assert result.exit_code == 0
        assert "SPY" in strip_ansi(result.output)


# ---------------------------------------------------------------------------
# Chart command tests
# ---------------------------------------------------------------------------


class TestChartCommand:
    @patch("fidelity_trader.cli._market_data.get_client")
    def test_chart_table_output(self, mock_get_client):
        mock_client = MagicMock()

        mock_bar = MagicMock()
        mock_bar.timestamp = "2026/04/01-09:30:00"
        mock_bar.open = 173.0
        mock_bar.high = 175.0
        mock_bar.low = 172.5
        mock_bar.close = 174.5
        mock_bar.volume = 1000000

        mock_symbol_info = MagicMock()
        mock_symbol_info.identifier = "AAPL"

        mock_chart_resp = MagicMock()
        mock_chart_resp.symbol_info = mock_symbol_info
        mock_chart_resp.bars = [mock_bar]
        mock_client.chart.get_chart.return_value = mock_chart_resp

        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["chart", "AAPL"])
        assert result.exit_code == 0
        assert "AAPL" in strip_ansi(result.output)

    @patch("fidelity_trader.cli._market_data.get_client")
    def test_chart_with_bars_and_days(self, mock_get_client):
        mock_client = MagicMock()

        mock_symbol_info = MagicMock()
        mock_symbol_info.identifier = "MSFT"

        mock_chart_resp = MagicMock()
        mock_chart_resp.symbol_info = mock_symbol_info
        mock_chart_resp.bars = []
        mock_client.chart.get_chart.return_value = mock_chart_resp

        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["chart", "MSFT", "--bars", "5", "--days", "3"])
        assert result.exit_code == 0

    def test_chart_invalid_bar_width(self):
        result = runner.invoke(app, ["chart", "AAPL", "--bars", "99"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Search command tests
# ---------------------------------------------------------------------------


class TestSearchCommand:
    @patch("fidelity_trader.cli._market_data.get_client")
    def test_search_table_output(self, mock_get_client):
        mock_client = MagicMock()

        mock_suggestion = MagicMock()
        mock_suggestion.symbol = "AAPL"
        mock_suggestion.desc = "APPLE INC"
        mock_suggestion.type = "EQ"
        mock_suggestion.exchange = "NASDAQ"

        mock_resp = MagicMock()
        mock_resp.count = 1
        mock_resp.suggestions = [mock_suggestion]
        mock_client.search.autosuggest.return_value = mock_resp

        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["search", "apple"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "AAPL" in output
        assert "APPLE" in output

    @patch("fidelity_trader.cli._market_data.get_client")
    def test_search_no_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.count = 0
        mock_resp.suggestions = []
        mock_client.search.autosuggest.return_value = mock_resp

        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["search", "xyznonexistent"])
        assert result.exit_code == 1

    @patch("fidelity_trader.cli._market_data.get_client")
    def test_search_json_output(self, mock_get_client):
        mock_client = MagicMock()

        mock_suggestion = MagicMock()
        mock_suggestion.symbol = "MSFT"
        mock_suggestion.model_dump.return_value = {"symbol": "MSFT", "desc": "MICROSOFT CORP"}

        mock_resp = MagicMock()
        mock_resp.count = 1
        mock_resp.suggestions = [mock_suggestion]
        mock_client.search.autosuggest.return_value = mock_resp

        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["--format", "json", "search", "microsoft"])
        assert result.exit_code == 0
        assert "MSFT" in strip_ansi(result.output)


# ---------------------------------------------------------------------------
# Earnings command tests
# ---------------------------------------------------------------------------


class TestEarningsCommand:
    @patch("fidelity_trader.cli._research.get_client")
    def test_earnings_table_output(self, mock_get_client):
        mock_client = MagicMock()

        mock_sec = MagicMock()
        mock_sec.symbol = "AAPL"

        mock_q1 = MagicMock()
        mock_q1.fiscal_qtr = 1
        mock_q1.fiscal_yr = 2026
        mock_q1.report_date = "2026-01-30"
        mock_q1.adjusted_eps = 2.10
        mock_q1.consensus_est = 2.05

        mock_q2 = MagicMock()
        mock_q2.fiscal_qtr = 2
        mock_q2.fiscal_yr = 2026
        mock_q2.report_date = "2026-04-25"
        mock_q2.adjusted_eps = None
        mock_q2.consensus_est = 1.95

        mock_detail = MagicMock()
        mock_detail.sec_detail = mock_sec
        mock_detail.quarters = [mock_q1, mock_q2]

        mock_resp = MagicMock()
        mock_resp.earnings = [mock_detail]
        mock_client.research.get_earnings.return_value = mock_resp

        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["earnings", "AAPL"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "AAPL" in output
        assert "Q1 2026" in output

    @patch("fidelity_trader.cli._research.get_client")
    def test_earnings_json_output(self, mock_get_client):
        mock_client = MagicMock()

        mock_detail = MagicMock()
        mock_detail.model_dump.return_value = {"symbol": "AAPL", "quarters": []}

        mock_resp = MagicMock()
        mock_resp.earnings = [mock_detail]
        mock_client.research.get_earnings.return_value = mock_resp

        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["--format", "json", "earnings", "AAPL"])
        assert result.exit_code == 0
        assert "AAPL" in strip_ansi(result.output)


# ---------------------------------------------------------------------------
# Dividends command tests
# ---------------------------------------------------------------------------


class TestDividendsCommand:
    @patch("fidelity_trader.cli._research.get_client")
    def test_dividends_table_output(self, mock_get_client):
        mock_client = MagicMock()

        mock_sec = MagicMock()
        mock_sec.symbol = "AAPL"

        mock_hist = MagicMock()
        mock_hist.ex_date = "2026-02-10"
        mock_hist.pay_date = "2026-02-15"
        mock_hist.amt = 0.25
        mock_hist.freq_name = "Quarterly"
        mock_hist.type = "Regular"

        mock_detail = MagicMock()
        mock_detail.sec_detail = mock_sec
        mock_detail.amt = 0.25
        mock_detail.ex_div_date = "2026-02-10"
        mock_detail.yld_ttm = 0.0055
        mock_detail.indicated_ann_div = 1.00
        mock_detail.history = [mock_hist]

        mock_resp = MagicMock()
        mock_resp.dividends = [mock_detail]
        mock_client.research.get_dividends.return_value = mock_resp

        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["dividends", "AAPL"])
        assert result.exit_code == 0
        assert "AAPL" in strip_ansi(result.output)

    @patch("fidelity_trader.cli._research.get_client")
    def test_dividends_json_output(self, mock_get_client):
        mock_client = MagicMock()

        mock_detail = MagicMock()
        mock_detail.model_dump.return_value = {"symbol": "AAPL", "amt": 0.25}

        mock_resp = MagicMock()
        mock_resp.dividends = [mock_detail]
        mock_client.research.get_dividends.return_value = mock_resp

        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["--format", "json", "dividends", "AAPL"])
        assert result.exit_code == 0
        assert "AAPL" in strip_ansi(result.output)


# ---------------------------------------------------------------------------
# All new commands visible in root help
# ---------------------------------------------------------------------------


class TestRootHelp:
    def test_new_commands_in_root_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        for cmd in ("quote", "chart", "search", "earnings", "dividends", "stream"):
            assert cmd in output, f"'{cmd}' not found in --help output"
