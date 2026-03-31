"""Tests for the option summary API models and OptionSummaryAPI client."""
import json

import httpx
import pytest
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.option_summary import (
    GainLossDetail,
    LegPriceDetail,
    LegSecurityDetails,
    LegMarketValDetail,
    LegDetail,
    PairingSecurityDetails,
    PairingDetail,
    UnderlyingDetail,
    OptionAccountDetail,
    OptionSummaryResponse,
)
from fidelity_trader.portfolio.option_summary import OptionSummaryAPI


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

OPTION_SUMMARY_URL = (
    f"{DPSERVICE_URL}/ftgw/dp/retail-am-optionsummary/v1/accounts/positions/option-summary/get"
)


def _make_leg_detail(
    symbol: str = "UNH260618C350",
    description: str = "UNH JUN 18 2026 $350 CALL",
    buy_sell: str = "B",
    shares: float = 100.0,
    option_type: str = "CALL",
    strike: float = 350.0,
    option_price: float = 1.90,
    last_price: float = 1.80,
    expiry_date: str = "2026-06-18",
    expiry_days: int = 80,
    market_val: float = 16800.00,
    total_gain_loss: float = -259071.38,
    total_gain_loss_pct: float = -93.91,
) -> dict:
    return {
        "legBuySellInd": buy_sell,
        "legShares": shares,
        "legInTheMoneyIndex": "O",
        "legOptionSecurityTypeCode": option_type,
        "marketValDetail": {
            "marketVal": market_val,
            "totalGainLoss": total_gain_loss,
            "totalGainLossPct": total_gain_loss_pct,
        },
        "legSecurityDetails": {
            "legSymbol": symbol,
            "legSecurityDescription": description,
            "legSymbolExpiryDate": expiry_date,
            "legSymbolPCIndex": "C",
            "legSymbolStrike": strike,
            "delShares": 100,
        },
        "legPriceDetail": {
            "legOptionPrice": option_price,
            "legOptionLastPrice": last_price,
            "legOptionPriceChg": round(last_price - option_price, 2),
            "legExpirationDate": expiry_date,
            "legExpirationDays": expiry_days,
            "legOptionStrikePrice": strike,
        },
    }


def _make_pairing_detail(
    symbol: str = "UNH",
    description: str = "UNITEDHEALTH GROUP",
    match_code: str = "SPREAD",
    match_desc: str = "Debit Spread",
    total_gain_loss: float = -36934.76,
    total_market_value: float = 1700.00,
    total_cost_basis: float = 38634.76,
    legs: list = None,
) -> dict:
    if legs is None:
        legs = [_make_leg_detail()]
    return {
        "pairingSecurityDetails": {
            "symbol": symbol,
            "securityDescription": description,
            "priceDetail": {
                "ulPrice": 259.02,
                "lastPrice": 261.79,
                "lastPriceChg": 2.77,
                "lastPriceChgPct": 1.07,
            },
        },
        "optionPairMatchCode": match_code,
        "optionPairMatchCodeDescription": match_desc,
        "totalGainLoss": total_gain_loss,
        "totalMarketValue": total_market_value,
        "totalCostBasis": total_cost_basis,
        "legCount": len(legs),
        "legDetails": {"legDetail": legs},
    }


def _make_underlying_detail(
    expiry_date: str = "2026-06-18",
    expiry_days: int = 80,
    pairing_count: int = 1,
    total_gain_loss: float = -36934.76,
    total_gain_loss_pct: float = -95.60,
    total_market_value: float = 1700.00,
    total_cost_basis: float = 38634.76,
    pairings: list = None,
) -> dict:
    if pairings is None:
        pairings = [_make_pairing_detail()]
    return {
        "legExpirationDate": expiry_date,
        "legExpirationDays": expiry_days,
        "pairingCount": pairing_count,
        "totalGainLoss": total_gain_loss,
        "totalGainLossPct": total_gain_loss_pct,
        "totalMarketValue": total_market_value,
        "totalCostBasis": total_cost_basis,
        "pairingDetails": {"pairingDetail": pairings},
    }


def _make_account_detail(
    acct_num: str = "Z21772945",
    underlying_details: list = None,
) -> dict:
    if underlying_details is None:
        underlying_details = [_make_underlying_detail()]
    return {
        "acctNum": acct_num,
        "cycleDate": "20260328",
        "cycleTime": "033018",
        "underlyingCount": 5,
        "count": 4,
        "accountGainLossDetail": {
            "totalCostBasis": 326868.51,
            "totalGainLoss": -188354.50,
            "totalMarketValue": 138514.01,
            "totalGainLossPct": -57.62,
        },
        "optionGainLossDetail": {
            "totalCostBasis": 173927.60,
            "totalGainLoss": -165706.60,
            "totalMarketValue": 8221.00,
        },
        "underlyingDetails": {"underlyingDetail": underlying_details},
    }


def _make_api_response(account_details: list = None) -> dict:
    if account_details is None:
        account_details = [_make_account_detail()]
    return {
        "optionPairing": {
            "acctDetails": [
                {"acctDetail": detail} for detail in account_details
            ]
        }
    }


# ---------------------------------------------------------------------------
# GainLossDetail
# ---------------------------------------------------------------------------

class TestGainLossDetail:
    def test_parses_all_fields(self):
        gld = GainLossDetail.model_validate({
            "totalCostBasis": 326868.51,
            "totalGainLoss": -188354.50,
            "totalMarketValue": 138514.01,
            "totalGainLossPct": -57.62,
        })
        assert gld.total_cost_basis == pytest.approx(326868.51)
        assert gld.total_gain_loss == pytest.approx(-188354.50)
        assert gld.total_market_value == pytest.approx(138514.01)
        assert gld.total_gain_loss_pct == pytest.approx(-57.62)

    def test_optional_fields_default_none(self):
        gld = GainLossDetail.model_validate({})
        assert gld.total_cost_basis is None
        assert gld.total_gain_loss is None

    def test_coerces_string_values(self):
        gld = GainLossDetail.model_validate({"totalGainLoss": "-1234.56"})
        assert gld.total_gain_loss == pytest.approx(-1234.56)

    def test_sentinel_strings_become_none(self):
        gld = GainLossDetail.model_validate({"totalGainLoss": "--", "totalMarketValue": "N/A"})
        assert gld.total_gain_loss is None
        assert gld.total_market_value is None


# ---------------------------------------------------------------------------
# LegPriceDetail
# ---------------------------------------------------------------------------

class TestLegPriceDetail:
    def test_parses_all_fields(self):
        lpd = LegPriceDetail.model_validate({
            "legOptionPrice": 1.90,
            "legOptionLastPrice": 1.80,
            "legOptionPriceChg": -0.10,
            "legExpirationDate": "2026-06-18",
            "legExpirationDays": 80,
            "legOptionStrikePrice": 350.0,
        })
        assert lpd.leg_option_price == pytest.approx(1.90)
        assert lpd.leg_option_last_price == pytest.approx(1.80)
        assert lpd.leg_option_price_chg == pytest.approx(-0.10)
        assert lpd.leg_expiration_date == "2026-06-18"
        assert lpd.leg_expiration_days == 80
        assert lpd.leg_option_strike_price == pytest.approx(350.0)

    def test_optional_fields_default_none(self):
        lpd = LegPriceDetail.model_validate({})
        assert lpd.leg_option_price is None
        assert lpd.leg_expiration_date is None


# ---------------------------------------------------------------------------
# LegSecurityDetails
# ---------------------------------------------------------------------------

class TestLegSecurityDetails:
    def test_parses_all_fields(self):
        lsd = LegSecurityDetails.model_validate({
            "legSymbol": "UNH260618C350",
            "legSecurityDescription": "UNH JUN 18 2026 $350 CALL",
            "legSymbolExpiryDate": "2026-06-18",
            "legSymbolPCIndex": "C",
            "legSymbolStrike": 350.0,
            "delShares": 100,
        })
        assert lsd.leg_symbol == "UNH260618C350"
        assert lsd.leg_security_description == "UNH JUN 18 2026 $350 CALL"
        assert lsd.leg_symbol_expiry_date == "2026-06-18"
        assert lsd.leg_symbol_pc_index == "C"
        assert lsd.leg_symbol_strike == pytest.approx(350.0)
        assert lsd.del_shares == 100

    def test_optional_fields_default_none(self):
        lsd = LegSecurityDetails.model_validate({})
        assert lsd.leg_symbol is None
        assert lsd.leg_symbol_strike is None


# ---------------------------------------------------------------------------
# LegMarketValDetail
# ---------------------------------------------------------------------------

class TestLegMarketValDetail:
    def test_parses_all_fields(self):
        lmv = LegMarketValDetail.model_validate({
            "marketVal": 16800.00,
            "totalGainLoss": -259071.38,
            "totalGainLossPct": -93.91,
        })
        assert lmv.market_val == pytest.approx(16800.00)
        assert lmv.total_gain_loss == pytest.approx(-259071.38)
        assert lmv.total_gain_loss_pct == pytest.approx(-93.91)

    def test_optional_fields_default_none(self):
        lmv = LegMarketValDetail.model_validate({})
        assert lmv.market_val is None
        assert lmv.total_gain_loss is None


# ---------------------------------------------------------------------------
# LegDetail
# ---------------------------------------------------------------------------

class TestLegDetail:
    def test_parses_full_leg(self):
        leg = LegDetail.model_validate(_make_leg_detail())
        assert leg.leg_buy_sell_ind == "B"
        assert leg.leg_shares == pytest.approx(100.0)
        assert leg.leg_in_the_money_index == "O"
        assert leg.leg_option_security_type_code == "CALL"
        assert leg.market_val_detail is not None
        assert leg.market_val_detail.market_val == pytest.approx(16800.00)
        assert leg.leg_security_details is not None
        assert leg.leg_security_details.leg_symbol == "UNH260618C350"
        assert leg.leg_price_detail is not None
        assert leg.leg_price_detail.leg_option_price == pytest.approx(1.90)

    def test_put_leg(self):
        leg = LegDetail.model_validate(_make_leg_detail(
            symbol="UNH260618P250",
            description="UNH JUN 18 2026 $250 PUT",
            option_type="PUT",
            buy_sell="S",
            strike=250.0,
        ))
        assert leg.leg_buy_sell_ind == "S"
        assert leg.leg_option_security_type_code == "PUT"
        assert leg.leg_security_details.leg_symbol == "UNH260618P250"

    def test_optional_nested_models_default_none(self):
        leg = LegDetail.model_validate({
            "legBuySellInd": "B",
            "legShares": 10.0,
        })
        assert leg.market_val_detail is None
        assert leg.leg_security_details is None
        assert leg.leg_price_detail is None


# ---------------------------------------------------------------------------
# PairingSecurityDetails
# ---------------------------------------------------------------------------

class TestPairingSecurityDetails:
    def test_parses_with_price_detail_flattened(self):
        psd = PairingSecurityDetails.model_validate({
            "symbol": "UNH",
            "securityDescription": "UNITEDHEALTH GROUP",
            "priceDetail": {
                "ulPrice": 259.02,
                "lastPrice": 261.79,
                "lastPriceChg": 2.77,
                "lastPriceChgPct": 1.07,
            },
        })
        assert psd.symbol == "UNH"
        assert psd.security_description == "UNITEDHEALTH GROUP"
        assert psd.ul_price == pytest.approx(259.02)
        assert psd.last_price == pytest.approx(261.79)
        assert psd.last_price_chg == pytest.approx(2.77)
        assert psd.last_price_chg_pct == pytest.approx(1.07)

    def test_optional_fields_default_none(self):
        psd = PairingSecurityDetails.model_validate({"symbol": "AAPL"})
        assert psd.ul_price is None
        assert psd.last_price is None

    def test_no_price_detail_key(self):
        psd = PairingSecurityDetails.model_validate({
            "symbol": "SPY",
            "securityDescription": "SPDR S&P 500 ETF",
        })
        assert psd.symbol == "SPY"
        assert psd.ul_price is None


# ---------------------------------------------------------------------------
# PairingDetail
# ---------------------------------------------------------------------------

class TestPairingDetail:
    def test_parses_full_pairing(self):
        pd = PairingDetail.model_validate(_make_pairing_detail())
        assert pd.option_pair_match_code == "SPREAD"
        assert pd.option_pair_match_code_description == "Debit Spread"
        assert pd.total_gain_loss == pytest.approx(-36934.76)
        assert pd.total_market_value == pytest.approx(1700.00)
        assert pd.total_cost_basis == pytest.approx(38634.76)
        assert pd.leg_count == 1
        assert len(pd.legs) == 1
        assert pd.legs[0].leg_buy_sell_ind == "B"

    def test_pairing_security_details_nested(self):
        pd = PairingDetail.model_validate(_make_pairing_detail())
        assert pd.pairing_security_details is not None
        assert pd.pairing_security_details.symbol == "UNH"
        assert pd.pairing_security_details.ul_price == pytest.approx(259.02)

    def test_multiple_legs(self):
        legs = [
            _make_leg_detail("UNH260618C350", buy_sell="B"),
            _make_leg_detail("UNH260618C400", buy_sell="S", strike=400.0),
        ]
        pd = PairingDetail.model_validate(_make_pairing_detail(legs=legs))
        assert len(pd.legs) == 2
        assert pd.legs[0].leg_buy_sell_ind == "B"
        assert pd.legs[1].leg_buy_sell_ind == "S"

    def test_empty_legs(self):
        data = {
            "optionPairMatchCode": "SINGLE",
            "legCount": 0,
            "legDetails": {"legDetail": []},
        }
        pd = PairingDetail.model_validate(data)
        assert pd.legs == []


# ---------------------------------------------------------------------------
# UnderlyingDetail
# ---------------------------------------------------------------------------

class TestUnderlyingDetail:
    def test_parses_full_underlying(self):
        ud = UnderlyingDetail.model_validate(_make_underlying_detail())
        assert ud.leg_expiration_date == "2026-06-18"
        assert ud.leg_expiration_days == 80
        assert ud.pairing_count == 1
        assert ud.total_gain_loss == pytest.approx(-36934.76)
        assert ud.total_gain_loss_pct == pytest.approx(-95.60)
        assert ud.total_market_value == pytest.approx(1700.00)
        assert ud.total_cost_basis == pytest.approx(38634.76)
        assert len(ud.pairings) == 1

    def test_pairing_nested_correctly(self):
        ud = UnderlyingDetail.model_validate(_make_underlying_detail())
        assert ud.pairings[0].option_pair_match_code == "SPREAD"
        assert ud.pairings[0].pairing_security_details.symbol == "UNH"

    def test_multiple_pairings(self):
        pairings = [
            _make_pairing_detail("UNH", match_code="SPREAD"),
            _make_pairing_detail("SPY", match_code="SINGLE"),
        ]
        ud = UnderlyingDetail.model_validate(_make_underlying_detail(pairings=pairings))
        assert len(ud.pairings) == 2
        assert ud.pairings[0].pairing_security_details.symbol == "UNH"
        assert ud.pairings[1].pairing_security_details.symbol == "SPY"

    def test_empty_pairings(self):
        data = {
            "legExpirationDate": "2026-06-18",
            "legExpirationDays": 80,
            "pairingDetails": {"pairingDetail": []},
        }
        ud = UnderlyingDetail.model_validate(data)
        assert ud.pairings == []


# ---------------------------------------------------------------------------
# OptionAccountDetail
# ---------------------------------------------------------------------------

class TestOptionAccountDetail:
    def test_parses_account_with_underlying_details(self):
        oad = OptionAccountDetail.model_validate(_make_account_detail())
        assert oad.acct_num == "Z21772945"
        assert oad.cycle_date == "20260328"
        assert oad.cycle_time == "033018"
        assert oad.underlying_count == 5
        assert oad.count == 4
        assert len(oad.underlying_details) == 1

    def test_account_gain_loss_detail_nested(self):
        oad = OptionAccountDetail.model_validate(_make_account_detail())
        assert oad.account_gain_loss_detail is not None
        assert oad.account_gain_loss_detail.total_cost_basis == pytest.approx(326868.51)
        assert oad.account_gain_loss_detail.total_gain_loss == pytest.approx(-188354.50)

    def test_option_gain_loss_detail_nested(self):
        oad = OptionAccountDetail.model_validate(_make_account_detail())
        assert oad.option_gain_loss_detail is not None
        assert oad.option_gain_loss_detail.total_cost_basis == pytest.approx(173927.60)
        assert oad.option_gain_loss_detail.total_market_value == pytest.approx(8221.00)

    def test_deep_nesting_leg_access(self):
        oad = OptionAccountDetail.model_validate(_make_account_detail())
        leg = oad.underlying_details[0].pairings[0].legs[0]
        assert leg.leg_security_details.leg_symbol == "UNH260618C350"
        assert leg.leg_price_detail.leg_option_strike_price == pytest.approx(350.0)

    def test_empty_underlying_details(self):
        data = {
            "acctNum": "Z99999999",
            "underlyingDetails": {"underlyingDetail": []},
        }
        oad = OptionAccountDetail.model_validate(data)
        assert oad.underlying_details == []

    def test_missing_underlying_details_key(self):
        data = {"acctNum": "Z99999999"}
        oad = OptionAccountDetail.model_validate(data)
        assert oad.underlying_details == []


# ---------------------------------------------------------------------------
# OptionSummaryResponse — full integration parsing
# ---------------------------------------------------------------------------

class TestOptionSummaryResponse:
    def test_single_account(self):
        raw = _make_api_response([_make_account_detail("Z21772945")])
        resp = OptionSummaryResponse.from_api_response(raw)
        assert len(resp.accounts) == 1
        assert resp.accounts[0].acct_num == "Z21772945"

    def test_account_gain_loss_at_top_level(self):
        raw = _make_api_response([_make_account_detail()])
        resp = OptionSummaryResponse.from_api_response(raw)
        agl = resp.accounts[0].account_gain_loss_detail
        assert agl.total_cost_basis == pytest.approx(326868.51)
        assert agl.total_gain_loss == pytest.approx(-188354.50)
        assert agl.total_market_value == pytest.approx(138514.01)
        assert agl.total_gain_loss_pct == pytest.approx(-57.62)

    def test_option_gain_loss_at_account_level(self):
        raw = _make_api_response([_make_account_detail()])
        resp = OptionSummaryResponse.from_api_response(raw)
        ogl = resp.accounts[0].option_gain_loss_detail
        assert ogl.total_cost_basis == pytest.approx(173927.60)
        assert ogl.total_gain_loss == pytest.approx(-165706.60)
        assert ogl.total_market_value == pytest.approx(8221.00)

    def test_underlying_details_parsed(self):
        raw = _make_api_response([_make_account_detail()])
        resp = OptionSummaryResponse.from_api_response(raw)
        ud = resp.accounts[0].underlying_details[0]
        assert ud.leg_expiration_date == "2026-06-18"
        assert ud.leg_expiration_days == 80
        assert ud.pairing_count == 1

    def test_pairing_detail_parsed(self):
        raw = _make_api_response([_make_account_detail()])
        resp = OptionSummaryResponse.from_api_response(raw)
        pairing = resp.accounts[0].underlying_details[0].pairings[0]
        assert pairing.option_pair_match_code == "SPREAD"
        assert pairing.option_pair_match_code_description == "Debit Spread"
        assert pairing.pairing_security_details.symbol == "UNH"

    def test_leg_detail_parsed(self):
        raw = _make_api_response([_make_account_detail()])
        resp = OptionSummaryResponse.from_api_response(raw)
        leg = resp.accounts[0].underlying_details[0].pairings[0].legs[0]
        assert leg.leg_buy_sell_ind == "B"
        assert leg.leg_shares == pytest.approx(100.0)
        assert leg.leg_option_security_type_code == "CALL"
        assert leg.leg_security_details.leg_symbol == "UNH260618C350"
        assert leg.leg_price_detail.leg_option_price == pytest.approx(1.90)
        assert leg.leg_price_detail.leg_option_last_price == pytest.approx(1.80)
        assert leg.leg_price_detail.leg_option_strike_price == pytest.approx(350.0)

    def test_multiple_accounts(self):
        raw = _make_api_response([
            _make_account_detail("ACC001"),
            _make_account_detail("ACC002"),
        ])
        resp = OptionSummaryResponse.from_api_response(raw)
        assert len(resp.accounts) == 2
        assert resp.accounts[0].acct_num == "ACC001"
        assert resp.accounts[1].acct_num == "ACC002"

    def test_empty_response_body(self):
        resp = OptionSummaryResponse.from_api_response({})
        assert resp.accounts == []

    def test_empty_acct_details(self):
        resp = OptionSummaryResponse.from_api_response({"optionPairing": {"acctDetails": []}})
        assert resp.accounts == []


# ---------------------------------------------------------------------------
# OptionSummaryAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestOptionSummaryAPI:
    @respx.mock
    def test_get_option_summary_makes_correct_request(self):
        raw_response = _make_api_response([_make_account_detail("Z21772945")])
        route = respx.post(OPTION_SUMMARY_URL).mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = OptionSummaryAPI(client)
        result = api.get_option_summary(["Z21772945"])

        assert route.called
        assert isinstance(result, OptionSummaryResponse)
        assert len(result.accounts) == 1
        assert result.accounts[0].acct_num == "Z21772945"

    @respx.mock
    def test_get_option_summary_request_body_shape(self):
        raw_response = _make_api_response([_make_account_detail("Z21772945")])
        route = respx.post(OPTION_SUMMARY_URL).mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = OptionSummaryAPI(client)
        api.get_option_summary(["Z21772945"])

        sent_body = json.loads(route.calls[0].request.content)
        params = sent_body["request"]["parameter"]
        assert params["returnCostBasisDetails"] is True
        assert params["returnIntradayDetails"] is True
        assert params["view"] == "EXPIRATION"
        assert params["returnUnpairedPositions"] is True
        acct_detail = params["acctDetails"]["acctDetail"]
        assert len(acct_detail) == 1
        assert acct_detail[0]["acctNum"] == "Z21772945"

    @respx.mock
    def test_get_option_summary_multiple_accounts(self):
        raw_response = _make_api_response([
            _make_account_detail("ACC001"),
            _make_account_detail("ACC002"),
        ])
        route = respx.post(OPTION_SUMMARY_URL).mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = OptionSummaryAPI(client)
        result = api.get_option_summary(["ACC001", "ACC002"])

        sent_body = json.loads(route.calls[0].request.content)
        acct_detail = sent_body["request"]["parameter"]["acctDetails"]["acctDetail"]
        assert len(acct_detail) == 2
        assert acct_detail[0]["acctNum"] == "ACC001"
        assert acct_detail[1]["acctNum"] == "ACC002"
        assert len(result.accounts) == 2

    @respx.mock
    def test_get_option_summary_raises_on_http_error(self):
        respx.post(OPTION_SUMMARY_URL).mock(
            return_value=httpx.Response(401)
        )
        client = httpx.Client()
        api = OptionSummaryAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_option_summary(["Z21772945"])

    @respx.mock
    def test_get_option_summary_returns_correct_type(self):
        raw_response = _make_api_response([_make_account_detail("Z21772945")])
        respx.post(OPTION_SUMMARY_URL).mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = OptionSummaryAPI(client)
        result = api.get_option_summary(["Z21772945"])
        assert isinstance(result, OptionSummaryResponse)
