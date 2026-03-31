"""Tests for the closed positions API models and ClosedPositionsAPI client."""
import json

import httpx
import pytest
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.closed_position import (
    WashUnadjustedGainLossDetail,
    GainLossDetail,
    CostBasisDetail,
    SecurityDetail,
    ClosedPositionDetail,
    AccountClosedPositionDetail,
    PortfolioGainLossDetail,
    PortfolioDetail,
    ClosedPositionsResponse,
)
from fidelity_trader.portfolio.closed_positions import ClosedPositionsAPI

_ENDPOINT = (
    f"{DPSERVICE_URL}/ftgw/dp/customer-am-position/v1/accounts/closedposition"
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_wash_detail(
    unadjusted_gain: float = 32.69,
    unadjusted_loss: float = -839.28,
    unadjusted_total: float = -806.59,
) -> dict:
    return {
        "unadjustedGain": unadjusted_gain,
        "unadjustedLoss": unadjusted_loss,
        "unadjustedTotalGainLoss": unadjusted_total,
    }


def _make_gain_loss_detail(
    realized_gain: float = 32.69,
    realized_loss: float = -839.28,
    disallowed_loss: float = 0.0,
    total_gain_loss: float = -806.59,
    include_wash: bool = True,
) -> dict:
    d: dict = {
        "realizedGain": realized_gain,
        "realizedLoss": realized_loss,
        "disallowedLoss": disallowed_loss,
        "totalGainLoss": total_gain_loss,
    }
    if include_wash:
        d["washUnadjustedGainLossDetail"] = _make_wash_detail(
            realized_gain, realized_loss, total_gain_loss
        )
    return d


def _make_closed_position_detail(
    symbol: str = "SPY",
    cusip: str = "78462F103",
    quantity: float = 10.831,
    proceeds_amt: float = 7326.73,
    cost_basis: float = 7345.86,
    total_gain_loss: float = -19.13,
) -> dict:
    return {
        "symbol": symbol,
        "cusip": cusip,
        "securityDescription": "STATE STREET SPDR S&P 500 ETF UNITS",
        "securityType": "Stocks/ETFs",
        "quantity": quantity,
        "proceedsAmt": proceeds_amt,
        "isAllBasisAvailable": True,
        "isWashSaleAdjusted": False,
        "intradayEligibilityCode": "SUCCESSFUL_RECALC",
        "securityDetail": {
            "assetId": "110769",
            "securityShortDescription": "STATE STRE",
        },
        "costBasisDetail": {
            "costBasis": cost_basis,
            "unadjustedCostBasis": cost_basis,
            "disallowedAmount": 0.0,
        },
        "longTermGainLossDetail": {
            "totalGainLoss": total_gain_loss,
            "unadjustedTotalGainLoss": total_gain_loss,
        },
        "totalGainLossDetail": {
            "totalGainLoss": total_gain_loss,
            "unadjustedTotalGainLoss": total_gain_loss,
        },
        "todayGainLossSincePurchase": "0.000",
        "todayGainLossSincePriorClose": "0.000",
    }


def _make_account_detail(
    acct_num: str = "250357290",
    is_retirement: bool = False,
    closed_position_count: int = 1,
    closed_positions: list[dict] = None,
    proceeds_amt_total: float = 13034.26,
    cost_basis_total: float = 13840.85,
) -> dict:
    if closed_positions is None:
        closed_positions = [_make_closed_position_detail()]
    return {
        "acctNum": acct_num,
        "closedPositionCount": closed_position_count,
        "proceedsAmtTotal": proceeds_amt_total,
        "costBasisTotal": cost_basis_total,
        "longTermGainLossDetail": _make_gain_loss_detail(),
        "totalGainLossDetail": _make_gain_loss_detail(),
        "closedPositionDetails": closed_positions,
    }


def _make_api_response(acct_details: list[dict]) -> dict:
    return {
        "closedPosition": {
            "portfolioDetail": {
                "portfolioGainLossDetail": {
                    "shortTermTotalGainLoss": 18217.5,
                    "longTermTotalGainLoss": -16839.7,
                    "totalGainLoss": 1377.8,
                },
                "proceedsAmtTotal": 3756639.85,
                "costBasisTotal": 3755262.05,
            },
            "acctDetails": {
                "acctDetail": acct_details,
            },
        }
    }


# ---------------------------------------------------------------------------
# WashUnadjustedGainLossDetail
# ---------------------------------------------------------------------------


class TestWashUnadjustedGainLossDetail:
    def test_parses_all_fields(self):
        w = WashUnadjustedGainLossDetail.model_validate(
            {"unadjustedGain": 32.69, "unadjustedLoss": -839.28, "unadjustedTotalGainLoss": -806.59}
        )
        assert w.unadjusted_gain == pytest.approx(32.69)
        assert w.unadjusted_loss == pytest.approx(-839.28)
        assert w.unadjusted_total_gain_loss == pytest.approx(-806.59)

    def test_optional_fields_default_none(self):
        w = WashUnadjustedGainLossDetail.model_validate({})
        assert w.unadjusted_gain is None
        assert w.unadjusted_loss is None
        assert w.unadjusted_total_gain_loss is None

    def test_coerces_string_values(self):
        w = WashUnadjustedGainLossDetail.model_validate({"unadjustedGain": "32.69"})
        assert w.unadjusted_gain == pytest.approx(32.69)

    def test_sentinel_strings_become_none(self):
        w = WashUnadjustedGainLossDetail.model_validate(
            {"unadjustedGain": "--", "unadjustedLoss": "N/A"}
        )
        assert w.unadjusted_gain is None
        assert w.unadjusted_loss is None


# ---------------------------------------------------------------------------
# GainLossDetail
# ---------------------------------------------------------------------------


class TestGainLossDetail:
    def test_parses_all_fields(self):
        gld = GainLossDetail.model_validate(_make_gain_loss_detail())
        assert gld.realized_gain == pytest.approx(32.69)
        assert gld.realized_loss == pytest.approx(-839.28)
        assert gld.disallowed_loss == pytest.approx(0.0)
        assert gld.total_gain_loss == pytest.approx(-806.59)
        assert gld.wash_unadjusted_gain_loss_detail is not None

    def test_nested_wash_detail(self):
        gld = GainLossDetail.model_validate(_make_gain_loss_detail())
        w = gld.wash_unadjusted_gain_loss_detail
        assert w.unadjusted_gain == pytest.approx(32.69)
        assert w.unadjusted_loss == pytest.approx(-839.28)

    def test_optional_fields_default_none(self):
        gld = GainLossDetail.model_validate({})
        assert gld.realized_gain is None
        assert gld.total_gain_loss is None
        assert gld.wash_unadjusted_gain_loss_detail is None

    def test_without_wash_detail(self):
        gld = GainLossDetail.model_validate(
            {"totalGainLoss": -19.13, "unadjustedTotalGainLoss": -19.13}
        )
        assert gld.total_gain_loss == pytest.approx(-19.13)
        assert gld.unadjusted_total_gain_loss == pytest.approx(-19.13)
        assert gld.wash_unadjusted_gain_loss_detail is None

    def test_negative_values(self):
        gld = GainLossDetail.model_validate({"realizedGain": 0.0, "realizedLoss": -5000.0, "totalGainLoss": -5000.0})
        assert gld.realized_loss == pytest.approx(-5000.0)
        assert gld.total_gain_loss == pytest.approx(-5000.0)


# ---------------------------------------------------------------------------
# CostBasisDetail
# ---------------------------------------------------------------------------


class TestCostBasisDetail:
    def test_parses_all_fields(self):
        cb = CostBasisDetail.model_validate(
            {"costBasis": 7345.86, "unadjustedCostBasis": 7345.86, "disallowedAmount": 0.0}
        )
        assert cb.cost_basis == pytest.approx(7345.86)
        assert cb.unadjusted_cost_basis == pytest.approx(7345.86)
        assert cb.disallowed_amount == pytest.approx(0.0)

    def test_optional_fields_default_none(self):
        cb = CostBasisDetail.model_validate({})
        assert cb.cost_basis is None
        assert cb.unadjusted_cost_basis is None
        assert cb.disallowed_amount is None

    def test_coerces_string_cost_basis(self):
        cb = CostBasisDetail.model_validate({"costBasis": "1234.56"})
        assert cb.cost_basis == pytest.approx(1234.56)


# ---------------------------------------------------------------------------
# SecurityDetail
# ---------------------------------------------------------------------------


class TestSecurityDetail:
    def test_parses_fields(self):
        sd = SecurityDetail.model_validate(
            {"assetId": "110769", "securityShortDescription": "STATE STRE"}
        )
        assert sd.asset_id == "110769"
        assert sd.security_short_description == "STATE STRE"

    def test_optional_fields_default_none(self):
        sd = SecurityDetail.model_validate({})
        assert sd.asset_id is None
        assert sd.security_short_description is None


# ---------------------------------------------------------------------------
# ClosedPositionDetail
# ---------------------------------------------------------------------------


class TestClosedPositionDetail:
    def test_full_position_parses(self):
        cp = ClosedPositionDetail.model_validate(_make_closed_position_detail())
        assert cp.symbol == "SPY"
        assert cp.cusip == "78462F103"
        assert cp.security_description == "STATE STREET SPDR S&P 500 ETF UNITS"
        assert cp.security_type == "Stocks/ETFs"
        assert cp.quantity == pytest.approx(10.831)
        assert cp.proceeds_amt == pytest.approx(7326.73)
        assert cp.is_all_basis_available is True
        assert cp.is_wash_sale_adjusted is False
        assert cp.intraday_eligibility_code == "SUCCESSFUL_RECALC"

    def test_nested_security_detail(self):
        cp = ClosedPositionDetail.model_validate(_make_closed_position_detail())
        assert cp.security_detail is not None
        assert cp.security_detail.asset_id == "110769"

    def test_nested_cost_basis_detail(self):
        cp = ClosedPositionDetail.model_validate(_make_closed_position_detail())
        assert cp.cost_basis_detail is not None
        assert cp.cost_basis_detail.cost_basis == pytest.approx(7345.86)
        assert cp.cost_basis_detail.disallowed_amount == pytest.approx(0.0)

    def test_nested_gain_loss_details(self):
        cp = ClosedPositionDetail.model_validate(_make_closed_position_detail())
        assert cp.long_term_gain_loss_detail is not None
        assert cp.long_term_gain_loss_detail.total_gain_loss == pytest.approx(-19.13)
        assert cp.total_gain_loss_detail is not None
        assert cp.total_gain_loss_detail.total_gain_loss == pytest.approx(-19.13)

    def test_today_gain_loss_string_coercion(self):
        cp = ClosedPositionDetail.model_validate(_make_closed_position_detail())
        assert cp.today_gain_loss_since_purchase == pytest.approx(0.0)
        assert cp.today_gain_loss_since_prior_close == pytest.approx(0.0)

    def test_optional_fields_default_none(self):
        cp = ClosedPositionDetail.model_validate({"acctNum": "X"})
        assert cp.symbol is None
        assert cp.cusip is None
        assert cp.security_detail is None

    def test_different_symbol(self):
        cp = ClosedPositionDetail.model_validate(
            _make_closed_position_detail(
                symbol="QQQ", cusip="46090E103", quantity=5.0, proceeds_amt=2100.0
            )
        )
        assert cp.symbol == "QQQ"
        assert cp.quantity == pytest.approx(5.0)
        assert cp.proceeds_amt == pytest.approx(2100.0)


# ---------------------------------------------------------------------------
# AccountClosedPositionDetail
# ---------------------------------------------------------------------------


class TestAccountClosedPositionDetail:
    def test_parses_account_with_one_position(self):
        acpd = AccountClosedPositionDetail.model_validate(_make_account_detail())
        assert acpd.acct_num == "250357290"
        assert acpd.closed_position_count == 1
        assert acpd.proceeds_amt_total == pytest.approx(13034.26)
        assert acpd.cost_basis_total == pytest.approx(13840.85)
        assert len(acpd.closed_positions) == 1
        assert acpd.closed_positions[0].symbol == "SPY"

    def test_nested_gain_loss_summaries(self):
        acpd = AccountClosedPositionDetail.model_validate(_make_account_detail())
        assert acpd.long_term_gain_loss_detail is not None
        assert acpd.long_term_gain_loss_detail.realized_gain == pytest.approx(32.69)
        assert acpd.total_gain_loss_detail is not None
        assert acpd.total_gain_loss_detail.total_gain_loss == pytest.approx(-806.59)

    def test_multiple_positions_in_account(self):
        positions = [
            _make_closed_position_detail("SPY", quantity=10.831),
            _make_closed_position_detail("QQQ", "46090E103", quantity=5.0, proceeds_amt=2100.0),
        ]
        acpd = AccountClosedPositionDetail.model_validate(
            _make_account_detail(
                closed_positions=positions,
                closed_position_count=2,
            )
        )
        assert len(acpd.closed_positions) == 2
        assert acpd.closed_positions[0].symbol == "SPY"
        assert acpd.closed_positions[1].symbol == "QQQ"

    def test_empty_closed_positions_list(self):
        data = {
            "acctNum": "X00000001",
            "closedPositionCount": 0,
            "closedPositionDetails": [],
        }
        acpd = AccountClosedPositionDetail.model_validate(data)
        assert acpd.closed_positions == []

    def test_missing_closed_positions_key(self):
        data = {
            "acctNum": "X00000001",
            "closedPositionCount": 0,
        }
        acpd = AccountClosedPositionDetail.model_validate(data)
        assert acpd.closed_positions == []


# ---------------------------------------------------------------------------
# PortfolioGainLossDetail
# ---------------------------------------------------------------------------


class TestPortfolioGainLossDetail:
    def test_parses_all_fields(self):
        pgl = PortfolioGainLossDetail.model_validate(
            {
                "shortTermTotalGainLoss": 18217.5,
                "longTermTotalGainLoss": -16839.7,
                "totalGainLoss": 1377.8,
            }
        )
        assert pgl.short_term_total_gain_loss == pytest.approx(18217.5)
        assert pgl.long_term_total_gain_loss == pytest.approx(-16839.7)
        assert pgl.total_gain_loss == pytest.approx(1377.8)

    def test_optional_fields_default_none(self):
        pgl = PortfolioGainLossDetail.model_validate({})
        assert pgl.short_term_total_gain_loss is None
        assert pgl.long_term_total_gain_loss is None
        assert pgl.total_gain_loss is None

    def test_coerces_string_values(self):
        pgl = PortfolioGainLossDetail.model_validate({"totalGainLoss": "1377.80"})
        assert pgl.total_gain_loss == pytest.approx(1377.80)


# ---------------------------------------------------------------------------
# PortfolioDetail
# ---------------------------------------------------------------------------


class TestPortfolioDetail:
    def test_parses_portfolio_detail(self):
        pd = PortfolioDetail.model_validate(
            {
                "portfolioGainLossDetail": {
                    "shortTermTotalGainLoss": 18217.5,
                    "longTermTotalGainLoss": -16839.7,
                    "totalGainLoss": 1377.8,
                },
                "proceedsAmtTotal": 3756639.85,
                "costBasisTotal": 3755262.05,
            }
        )
        assert pd.proceeds_amt_total == pytest.approx(3756639.85)
        assert pd.cost_basis_total == pytest.approx(3755262.05)
        assert pd.portfolio_gain_loss_detail is not None
        assert pd.portfolio_gain_loss_detail.total_gain_loss == pytest.approx(1377.8)

    def test_optional_fields_default_none(self):
        pd = PortfolioDetail.model_validate({})
        assert pd.portfolio_gain_loss_detail is None
        assert pd.proceeds_amt_total is None
        assert pd.cost_basis_total is None


# ---------------------------------------------------------------------------
# ClosedPositionsResponse — full integration parsing
# ---------------------------------------------------------------------------


class TestClosedPositionsResponse:
    def test_single_account_single_position(self):
        raw = _make_api_response([_make_account_detail("250357290")])
        resp = ClosedPositionsResponse.from_api_response(raw)
        assert resp.portfolio_detail is not None
        assert resp.portfolio_detail.proceeds_amt_total == pytest.approx(3756639.85)
        assert len(resp.accounts) == 1
        assert resp.accounts[0].acct_num == "250357290"
        assert len(resp.accounts[0].closed_positions) == 1
        assert resp.accounts[0].closed_positions[0].symbol == "SPY"

    def test_portfolio_level_gain_loss(self):
        raw = _make_api_response([_make_account_detail()])
        resp = ClosedPositionsResponse.from_api_response(raw)
        pgl = resp.portfolio_detail.portfolio_gain_loss_detail
        assert pgl.short_term_total_gain_loss == pytest.approx(18217.5)
        assert pgl.long_term_total_gain_loss == pytest.approx(-16839.7)
        assert pgl.total_gain_loss == pytest.approx(1377.8)

    def test_multiple_accounts(self):
        accts = [
            _make_account_detail("250357290", closed_positions=[_make_closed_position_detail("SPY")]),
            _make_account_detail(
                "Z21772945",
                closed_positions=[
                    _make_closed_position_detail("QQQ", "46090E103"),
                    _make_closed_position_detail("IWM", "464287655"),
                ],
                closed_position_count=2,
            ),
        ]
        raw = _make_api_response(accts)
        resp = ClosedPositionsResponse.from_api_response(raw)
        assert len(resp.accounts) == 2
        assert resp.accounts[0].acct_num == "250357290"
        assert resp.accounts[1].acct_num == "Z21772945"
        assert len(resp.accounts[1].closed_positions) == 2
        assert resp.accounts[1].closed_positions[0].symbol == "QQQ"
        assert resp.accounts[1].closed_positions[1].symbol == "IWM"

    def test_empty_response_body(self):
        resp = ClosedPositionsResponse.from_api_response({})
        assert resp.portfolio_detail is None
        assert resp.accounts == []

    def test_empty_accounts_list(self):
        raw = _make_api_response([])
        resp = ClosedPositionsResponse.from_api_response(raw)
        assert resp.accounts == []

    def test_account_with_no_closed_position_details_key(self):
        acct = {
            "acctNum": "X99999999",
            "closedPositionCount": 0,
        }
        raw = _make_api_response([acct])
        resp = ClosedPositionsResponse.from_api_response(raw)
        assert resp.accounts[0].closed_positions == []

    def test_missing_portfolio_detail(self):
        raw = {"closedPosition": {"acctDetails": {"acctDetail": []}}}
        resp = ClosedPositionsResponse.from_api_response(raw)
        assert resp.portfolio_detail is None
        assert resp.accounts == []

    def test_account_level_totals(self):
        raw = _make_api_response(
            [_make_account_detail("250357290", proceeds_amt_total=99000.0, cost_basis_total=100000.0)]
        )
        resp = ClosedPositionsResponse.from_api_response(raw)
        acct = resp.accounts[0]
        assert acct.proceeds_amt_total == pytest.approx(99000.0)
        assert acct.cost_basis_total == pytest.approx(100000.0)


# ---------------------------------------------------------------------------
# ClosedPositionsAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------


class TestClosedPositionsAPI:
    @respx.mock
    def test_get_closed_positions_makes_correct_request(self):
        raw_response = _make_api_response([_make_account_detail("250357290")])
        route = respx.post(_ENDPOINT).mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = ClosedPositionsAPI(client)
        result = api.get_closed_positions(
            account_numbers=["250357290"],
            start_date="2026-01-01",
            end_date="2026-03-30",
        )

        assert route.called
        assert isinstance(result, ClosedPositionsResponse)
        assert len(result.accounts) == 1
        assert result.accounts[0].acct_num == "250357290"

    @respx.mock
    def test_get_closed_positions_request_body_shape(self):
        raw_response = _make_api_response([_make_account_detail("250357290")])
        route = respx.post(_ENDPOINT).mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = ClosedPositionsAPI(client)
        api.get_closed_positions(
            account_numbers=["250357290"],
            start_date="2026-01-01",
            end_date="2026-03-30",
        )

        sent_body = json.loads(route.calls[0].request.content)
        params = sent_body["request"]["parameters"]
        assert params["startDate"] == "2026-01-01"
        assert params["endDate"] == "2026-03-30"
        assert params["dateType"] == "YTD"
        assert params["taxYear"] is None
        assert params["isExcludeWashSales"] is False
        acct_details = params["acctDetails"]
        assert len(acct_details) == 1
        assert acct_details[0]["acctNum"] == "250357290"
        assert acct_details[0]["isRetirementAcct"] is False

    @respx.mock
    def test_get_closed_positions_custom_date_type(self):
        raw_response = _make_api_response([_make_account_detail("250357290")])
        route = respx.post(_ENDPOINT).mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = ClosedPositionsAPI(client)
        api.get_closed_positions(
            account_numbers=["250357290"],
            start_date="2025-01-01",
            end_date="2025-12-31",
            date_type="CUSTOM",
        )

        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["request"]["parameters"]["dateType"] == "CUSTOM"

    @respx.mock
    def test_get_closed_positions_exclude_wash_sales(self):
        raw_response = _make_api_response([_make_account_detail("250357290")])
        route = respx.post(_ENDPOINT).mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = ClosedPositionsAPI(client)
        api.get_closed_positions(
            account_numbers=["250357290"],
            start_date="2026-01-01",
            end_date="2026-03-30",
            exclude_wash_sales=True,
        )

        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["request"]["parameters"]["isExcludeWashSales"] is True

    @respx.mock
    def test_get_closed_positions_retirement_flags(self):
        raw_response = _make_api_response(
            [
                _make_account_detail("250357290"),
                _make_account_detail("Z21772945"),
            ]
        )
        route = respx.post(_ENDPOINT).mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = ClosedPositionsAPI(client)
        api.get_closed_positions(
            account_numbers=["250357290", "Z21772945"],
            start_date="2026-01-01",
            end_date="2026-03-30",
            retirement_flags={"250357290": True, "Z21772945": False},
        )

        sent_body = json.loads(route.calls[0].request.content)
        acct_details = sent_body["request"]["parameters"]["acctDetails"]
        assert len(acct_details) == 2
        assert acct_details[0]["acctNum"] == "250357290"
        assert acct_details[0]["isRetirementAcct"] is True
        assert acct_details[1]["acctNum"] == "Z21772945"
        assert acct_details[1]["isRetirementAcct"] is False

    @respx.mock
    def test_get_closed_positions_raises_on_http_error(self):
        respx.post(_ENDPOINT).mock(return_value=httpx.Response(401))
        client = httpx.Client()
        api = ClosedPositionsAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_closed_positions(
                account_numbers=["250357290"],
                start_date="2026-01-01",
                end_date="2026-03-30",
            )

    @respx.mock
    def test_get_closed_positions_multiple_accounts_parsed(self):
        accts = [
            _make_account_detail("ACC001", closed_positions=[_make_closed_position_detail("SPY")]),
            _make_account_detail("ACC002", closed_positions=[_make_closed_position_detail("QQQ", "46090E103")]),
        ]
        respx.post(_ENDPOINT).mock(
            return_value=httpx.Response(200, json=_make_api_response(accts))
        )
        client = httpx.Client()
        api = ClosedPositionsAPI(client)
        result = api.get_closed_positions(
            account_numbers=["ACC001", "ACC002"],
            start_date="2026-01-01",
            end_date="2026-03-30",
        )

        assert len(result.accounts) == 2
        assert result.accounts[0].acct_num == "ACC001"
        assert result.accounts[1].acct_num == "ACC002"

    @respx.mock
    def test_get_closed_positions_empty_account_list(self):
        respx.post(_ENDPOINT).mock(
            return_value=httpx.Response(200, json=_make_api_response([]))
        )
        client = httpx.Client()
        api = ClosedPositionsAPI(client)
        result = api.get_closed_positions(
            account_numbers=[],
            start_date="2026-01-01",
            end_date="2026-03-30",
        )

        assert result.accounts == []
