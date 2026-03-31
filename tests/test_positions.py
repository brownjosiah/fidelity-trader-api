"""Tests for the positions API models and PositionsAPI client."""
import pytest
import httpx
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.position import (
    PriceDetail,
    MarketValDetail,
    CostBasisDetail,
    PositionDetail,
    AccountGainLossDetail,
    AccountPositionDetail,
    PortfolioGainLossDetail,
    PortfolioDetail,
    PositionsResponse,
)
from fidelity_trader.portfolio.positions import PositionsAPI


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_position_detail(
    symbol: str = "SPAXX",
    quantity: float = 4925.02,
    last_price: float = 1.00,
    market_val: float = 4925.02,
    cost_basis: float = 0.00,
    total_gain_loss: float = 4925.02,
    holding_pct: float = 51.70,
) -> dict:
    return {
        "symbol": symbol,
        "securityType": "Core",
        "securitySubType": "Fidelity Mutual Fund",
        "securityDescription": "FIDELITY GOVERNMENT MONEY MARKET",
        "cusip": "31617H102",
        "quantity": quantity,
        "holdingPct": holding_pct,
        "priceDetail": {
            "lastPrice": last_price,
            "lastPriceChg": 0.00,
            "lastPriceChgPct": 0.00,
            "closingPrice": last_price,
            "prevClosePrice": last_price,
        },
        "marketValDetail": {
            "marketVal": market_val,
            "previousMarketVal": market_val,
            "totalGainLoss": total_gain_loss,
            "totalGainLossPct": 0.00,
            "todaysGainLoss": 0.00,
            "todaysGainLossPct": 0.00,
        },
        "costBasisDetail": {
            "avgCostPerShare": 0.00,
            "costBasis": cost_basis,
        },
    }


def _make_api_response(acct_details: list[dict], portfolio_position_count: int = 13) -> dict:
    return {
        "position": {
            "portfolioDetail": {
                "portfolioPositionCount": portfolio_position_count,
                "portfolioGainLossDetail": {
                    "totalGainLoss": 19160.62,
                    "totalGainLossPct": 15.05,
                    "costBasisTotal": 127281.18,
                    "portfolioTotalVal": 151042.05,
                    "todaysGainLoss": 517.72,
                    "todaysGainLossPct": 0.34,
                },
            },
            "acctDetails": {
                "acctDetail": acct_details,
            },
        }
    }


def _make_account_detail(
    acct_num: str = "Z33359950",
    positions: list[dict] = None,
    account_position_count: int = 1,
) -> dict:
    if positions is None:
        positions = [_make_position_detail()]
    return {
        "acctNum": acct_num,
        "accountPositionCount": account_position_count,
        "accountGainLossDetail": {
            "totalGainLoss": 4925.02,
            "costBasisTotal": 0.00,
            "accountMarketVal": 9525.27,
            "todaysGainLoss": 0.00,
        },
        "positionDetails": {
            "positionDetail": positions,
        },
    }


# ---------------------------------------------------------------------------
# PriceDetail
# ---------------------------------------------------------------------------

class TestPriceDetail:
    def test_parses_all_fields(self):
        pd = PriceDetail.model_validate({
            "lastPrice": 1.00,
            "lastPriceChg": 0.05,
            "lastPriceChgPct": 0.10,
            "closingPrice": 0.95,
            "prevClosePrice": 0.95,
        })
        assert pd.last_price == pytest.approx(1.00)
        assert pd.last_price_chg == pytest.approx(0.05)
        assert pd.last_price_chg_pct == pytest.approx(0.10)
        assert pd.closing_price == pytest.approx(0.95)
        assert pd.prev_close_price == pytest.approx(0.95)

    def test_optional_fields_default_none(self):
        pd = PriceDetail.model_validate({})
        assert pd.last_price is None
        assert pd.closing_price is None

    def test_coerces_string_values(self):
        pd = PriceDetail.model_validate({"lastPrice": "182.50"})
        assert pd.last_price == pytest.approx(182.50)

    def test_sentinel_strings_become_none(self):
        pd = PriceDetail.model_validate({"lastPrice": "--", "closingPrice": "N/A"})
        assert pd.last_price is None
        assert pd.closing_price is None


# ---------------------------------------------------------------------------
# MarketValDetail
# ---------------------------------------------------------------------------

class TestMarketValDetail:
    def test_parses_all_fields(self):
        mv = MarketValDetail.model_validate({
            "marketVal": 4925.02,
            "previousMarketVal": 4925.02,
            "totalGainLoss": 4925.02,
            "totalGainLossPct": 0.00,
            "todaysGainLoss": 0.00,
            "todaysGainLossPct": 0.00,
        })
        assert mv.market_val == pytest.approx(4925.02)
        assert mv.total_gain_loss == pytest.approx(4925.02)
        assert mv.todays_gain_loss == pytest.approx(0.00)

    def test_negative_gain_loss(self):
        mv = MarketValDetail.model_validate({
            "totalGainLoss": -1500.00,
            "totalGainLossPct": -12.50,
        })
        assert mv.total_gain_loss == pytest.approx(-1500.00)
        assert mv.total_gain_loss_pct == pytest.approx(-12.50)


# ---------------------------------------------------------------------------
# CostBasisDetail
# ---------------------------------------------------------------------------

class TestCostBasisDetail:
    def test_parses_fields(self):
        cb = CostBasisDetail.model_validate({"avgCostPerShare": 145.30, "costBasis": 1453.00})
        assert cb.avg_cost_per_share == pytest.approx(145.30)
        assert cb.cost_basis == pytest.approx(1453.00)

    def test_zero_cost_basis(self):
        cb = CostBasisDetail.model_validate({"avgCostPerShare": 0.00, "costBasis": 0.00})
        assert cb.cost_basis == pytest.approx(0.00)


# ---------------------------------------------------------------------------
# PositionDetail
# ---------------------------------------------------------------------------

class TestPositionDetail:
    def test_full_position_parses(self):
        pos = PositionDetail.model_validate(_make_position_detail())
        assert pos.symbol == "SPAXX"
        assert pos.security_type == "Core"
        assert pos.security_sub_type == "Fidelity Mutual Fund"
        assert pos.security_description == "FIDELITY GOVERNMENT MONEY MARKET"
        assert pos.cusip == "31617H102"
        assert pos.quantity == pytest.approx(4925.02)
        assert pos.holding_pct == pytest.approx(51.70)

    def test_price_detail_nested(self):
        pos = PositionDetail.model_validate(_make_position_detail())
        assert pos.price_detail is not None
        assert pos.price_detail.last_price == pytest.approx(1.00)

    def test_market_val_detail_nested(self):
        pos = PositionDetail.model_validate(_make_position_detail())
        assert pos.market_val_detail is not None
        assert pos.market_val_detail.market_val == pytest.approx(4925.02)

    def test_cost_basis_detail_nested(self):
        pos = PositionDetail.model_validate(_make_position_detail())
        assert pos.cost_basis_detail is not None
        assert pos.cost_basis_detail.cost_basis == pytest.approx(0.00)

    def test_equity_position(self):
        equity = {
            "symbol": "AAPL",
            "securityType": "Equity",
            "securitySubType": "Common Stock",
            "securityDescription": "APPLE INC",
            "cusip": "037833100",
            "quantity": 10.0,
            "holdingPct": 12.50,
            "priceDetail": {"lastPrice": 182.50, "lastPriceChg": 1.25, "lastPriceChgPct": 0.69,
                            "closingPrice": 181.25, "prevClosePrice": 181.25},
            "marketValDetail": {"marketVal": 1825.00, "previousMarketVal": 1812.50,
                                "totalGainLoss": 325.00, "totalGainLossPct": 21.67,
                                "todaysGainLoss": 12.50, "todaysGainLossPct": 0.69},
            "costBasisDetail": {"avgCostPerShare": 150.00, "costBasis": 1500.00},
        }
        pos = PositionDetail.model_validate(equity)
        assert pos.symbol == "AAPL"
        assert pos.quantity == pytest.approx(10.0)
        assert pos.price_detail.last_price == pytest.approx(182.50)
        assert pos.market_val_detail.total_gain_loss == pytest.approx(325.00)
        assert pos.cost_basis_detail.cost_basis == pytest.approx(1500.00)


# ---------------------------------------------------------------------------
# AccountGainLossDetail
# ---------------------------------------------------------------------------

class TestAccountGainLossDetail:
    def test_parses_all_fields(self):
        agl = AccountGainLossDetail.model_validate({
            "totalGainLoss": 4925.02,
            "totalGainLossPct": 5.00,
            "costBasisTotal": 0.00,
            "accountMarketVal": 9525.27,
            "todaysGainLoss": 0.00,
            "todaysGainLossPct": 0.00,
        })
        assert agl.total_gain_loss == pytest.approx(4925.02)
        assert agl.account_market_val == pytest.approx(9525.27)

    def test_optional_fields(self):
        agl = AccountGainLossDetail.model_validate({})
        assert agl.total_gain_loss is None
        assert agl.account_market_val is None


# ---------------------------------------------------------------------------
# AccountPositionDetail
# ---------------------------------------------------------------------------

class TestAccountPositionDetail:
    def test_parses_account_with_one_position(self):
        apd = AccountPositionDetail.model_validate(_make_account_detail())
        assert apd.acct_num == "Z33359950"
        assert apd.account_position_count == 1
        assert len(apd.positions) == 1
        assert apd.positions[0].symbol == "SPAXX"

    def test_account_gain_loss_detail_nested(self):
        apd = AccountPositionDetail.model_validate(_make_account_detail())
        assert apd.account_gain_loss_detail is not None
        assert apd.account_gain_loss_detail.account_market_val == pytest.approx(9525.27)

    def test_multiple_positions_in_account(self):
        positions = [
            _make_position_detail("SPAXX", 4925.02),
            _make_position_detail("AAPL", 10.0, last_price=182.50, market_val=1825.00),
        ]
        apd = AccountPositionDetail.model_validate(
            _make_account_detail(positions=positions, account_position_count=2)
        )
        assert len(apd.positions) == 2
        assert apd.positions[0].symbol == "SPAXX"
        assert apd.positions[1].symbol == "AAPL"

    def test_empty_position_list(self):
        data = {
            "acctNum": "X00000001",
            "accountPositionCount": 0,
            "positionDetails": {"positionDetail": []},
        }
        apd = AccountPositionDetail.model_validate(data)
        assert apd.positions == []


# ---------------------------------------------------------------------------
# PortfolioGainLossDetail
# ---------------------------------------------------------------------------

class TestPortfolioGainLossDetail:
    def test_parses_all_fields(self):
        pgl = PortfolioGainLossDetail.model_validate({
            "totalGainLoss": 19160.62,
            "totalGainLossPct": 15.05,
            "costBasisTotal": 127281.18,
            "portfolioTotalVal": 151042.05,
            "todaysGainLoss": 517.72,
            "todaysGainLossPct": 0.34,
        })
        assert pgl.total_gain_loss == pytest.approx(19160.62)
        assert pgl.total_gain_loss_pct == pytest.approx(15.05)
        assert pgl.cost_basis_total == pytest.approx(127281.18)
        assert pgl.portfolio_total_val == pytest.approx(151042.05)
        assert pgl.todays_gain_loss == pytest.approx(517.72)
        assert pgl.todays_gain_loss_pct == pytest.approx(0.34)


# ---------------------------------------------------------------------------
# PortfolioDetail
# ---------------------------------------------------------------------------

class TestPortfolioDetail:
    def test_parses_portfolio_detail(self):
        pd = PortfolioDetail.model_validate({
            "portfolioPositionCount": 13,
            "portfolioGainLossDetail": {
                "totalGainLoss": 19160.62,
                "totalGainLossPct": 15.05,
                "costBasisTotal": 127281.18,
                "portfolioTotalVal": 151042.05,
                "todaysGainLoss": 517.72,
                "todaysGainLossPct": 0.34,
            },
        })
        assert pd.portfolio_position_count == 13
        assert pd.portfolio_gain_loss_detail is not None
        assert pd.portfolio_gain_loss_detail.total_gain_loss == pytest.approx(19160.62)


# ---------------------------------------------------------------------------
# PositionsResponse — full integration parsing
# ---------------------------------------------------------------------------

class TestPositionsResponse:
    def test_single_account_single_position(self):
        raw = _make_api_response(
            [_make_account_detail("Z33359950", [_make_position_detail()])],
            portfolio_position_count=1,
        )
        resp = PositionsResponse.from_api_response(raw)
        assert resp.portfolio_detail is not None
        assert resp.portfolio_detail.portfolio_position_count == 1
        assert len(resp.accounts) == 1
        assert resp.accounts[0].acct_num == "Z33359950"
        assert len(resp.accounts[0].positions) == 1
        assert resp.accounts[0].positions[0].symbol == "SPAXX"

    def test_portfolio_level_gain_loss(self):
        raw = _make_api_response([_make_account_detail()])
        resp = PositionsResponse.from_api_response(raw)
        pgl = resp.portfolio_detail.portfolio_gain_loss_detail
        assert pgl.total_gain_loss == pytest.approx(19160.62)
        assert pgl.total_gain_loss_pct == pytest.approx(15.05)
        assert pgl.cost_basis_total == pytest.approx(127281.18)
        assert pgl.portfolio_total_val == pytest.approx(151042.05)
        assert pgl.todays_gain_loss == pytest.approx(517.72)
        assert pgl.todays_gain_loss_pct == pytest.approx(0.34)

    def test_position_price_detail_fields(self):
        raw = _make_api_response([_make_account_detail()])
        resp = PositionsResponse.from_api_response(raw)
        pos = resp.accounts[0].positions[0]
        assert pos.price_detail.last_price == pytest.approx(1.00)
        assert pos.price_detail.last_price_chg == pytest.approx(0.00)

    def test_multiple_accounts(self):
        accts = [
            _make_account_detail("A11111111", [_make_position_detail("SPAXX")]),
            _make_account_detail(
                "B22222222",
                [
                    _make_position_detail("AAPL", 10.0, last_price=182.50, market_val=1825.00),
                    _make_position_detail("MSFT", 5.0, last_price=380.00, market_val=1900.00),
                ],
                account_position_count=2,
            ),
        ]
        raw = _make_api_response(accts, portfolio_position_count=3)
        resp = PositionsResponse.from_api_response(raw)
        assert len(resp.accounts) == 2
        assert resp.accounts[0].acct_num == "A11111111"
        assert resp.accounts[1].acct_num == "B22222222"
        assert len(resp.accounts[1].positions) == 2
        assert resp.accounts[1].positions[0].symbol == "AAPL"
        assert resp.accounts[1].positions[1].symbol == "MSFT"

    def test_empty_response_body(self):
        resp = PositionsResponse.from_api_response({})
        assert resp.portfolio_detail is None
        assert resp.accounts == []

    def test_account_with_no_positions_key(self):
        """Account with missing positionDetails should yield empty positions list."""
        acct = {
            "acctNum": "X99999999",
            "accountPositionCount": 0,
        }
        raw = _make_api_response([acct], portfolio_position_count=0)
        resp = PositionsResponse.from_api_response(raw)
        assert resp.accounts[0].positions == []


# ---------------------------------------------------------------------------
# PositionsAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestPositionsAPI:
    @respx.mock
    def test_get_positions_makes_correct_request(self):
        raw_response = _make_api_response([_make_account_detail("257619270")])
        route = respx.post(f"{DPSERVICE_URL}/ftgw/dp/position/v2").mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = PositionsAPI(client)
        result = api.get_positions(["257619270"])

        assert route.called
        assert isinstance(result, PositionsResponse)
        assert len(result.accounts) == 1
        assert result.accounts[0].acct_num == "257619270"

    @respx.mock
    def test_get_positions_request_body_shape(self):
        raw_response = _make_api_response([_make_account_detail("257619270")])
        route = respx.post(f"{DPSERVICE_URL}/ftgw/dp/position/v2").mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = PositionsAPI(client)
        api.get_positions(["257619270"])

        import json
        sent_body = json.loads(route.calls[0].request.content)
        params = sent_body["request"]["parameter"]
        assert params["returnSecurityDetail"] is True
        assert params["returnPositionMarketValDetail"] is True
        assert params["returnPortfolioGainLossDetail"] is True
        acct_detail = params["acctDetails"]["acctDetail"]
        assert len(acct_detail) == 1
        assert acct_detail[0]["acctNum"] == "257619270"
        assert acct_detail[0]["acctType"] == "Brokerage"

    @respx.mock
    def test_get_positions_custom_account_types(self):
        raw_response = _make_api_response([_make_account_detail("IRA123")])
        route = respx.post(f"{DPSERVICE_URL}/ftgw/dp/position/v2").mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        custom_types = [
            {"retirementInd": True, "tradable": False, "acctNum": "IRA123",
             "acctType": "IRA", "acctSubType": "Roth", "isTradable": False}
        ]
        client = httpx.Client()
        api = PositionsAPI(client)
        api.get_positions(["IRA123"], account_types=custom_types)

        import json
        sent_body = json.loads(route.calls[0].request.content)
        acct_detail = sent_body["request"]["parameter"]["acctDetails"]["acctDetail"]
        assert acct_detail[0]["acctType"] == "IRA"
        assert acct_detail[0]["retirementInd"] is True

    @respx.mock
    def test_get_positions_raises_on_http_error(self):
        respx.post(f"{DPSERVICE_URL}/ftgw/dp/position/v2").mock(
            return_value=httpx.Response(401)
        )
        client = httpx.Client()
        api = PositionsAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_positions(["257619270"])

    @respx.mock
    def test_get_positions_multiple_accounts(self):
        accts = [
            _make_account_detail("ACC001", [_make_position_detail("SPAXX")]),
            _make_account_detail("ACC002", [_make_position_detail("AAPL", 5.0)]),
        ]
        raw_response = _make_api_response(accts, portfolio_position_count=2)
        respx.post(f"{DPSERVICE_URL}/ftgw/dp/position/v2").mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = PositionsAPI(client)
        result = api.get_positions(["ACC001", "ACC002"])

        assert len(result.accounts) == 2
