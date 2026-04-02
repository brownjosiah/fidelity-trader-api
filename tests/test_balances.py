"""Tests for the balances API models and BalancesAPI client."""
import json

import httpx
import pytest
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.balance import (
    AcctValDetail,
    CashDetail,
    BuyingPowerDetail,
    AvailableToWithdrawDetail,
    AddlInfoDetail,
    MarginMaintenanceDetail,
    MarginDetail,
    BondDetail,
    ShortDetail,
    OptionsDetail,
    SimplifiedMarginDetail,
    BalanceTimingDetail,
    AccountBalance,
    BalancesResponse,
)
from fidelity_trader.portfolio.balances import BalancesAPI


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_recent_balance_detail(
    net_worth: float = 7.47,
    core_balance: float = 7.47,
    cash_bp: float = 7.47,
    cash_only: float = 7.47,
) -> dict:
    return {
        "asOfDateTime": 1774912387,
        "acctValDetail": {
            "netWorth": net_worth,
            "netWorthChg": 0.00,
            "netWorthChgPct": 0.00,
            "marketVal": 0.00,
            "marketValChg": 0.00,
            "marketValChgPct": 0.00,
            "acctEqtyPct": 100.00,
            "hasUnpricedPosition": False,
            "regulatoryNetWorth": net_worth,
        },
        "cashDetail": {
            "heldInCash": 0.00,
            "coreBalance": core_balance,
            "creditDebit": 0.00,
            "settledAmt": core_balance,
            "cshMoneyMkt": core_balance,
        },
        "buyingPowerDetail": {
            "cash": cash_bp,
            "cashChg": 0.00,
            "cashCmtdToOpenOrder": 0.00,
        },
        "availableToWithdrawDetail": {
            "cashOnly": cash_only,
            "cashWithMargin": cash_only,
            "unsettledDeposit": 0.00,
        },
    }


def _make_brokerage_acct_detail(
    net_worth: float = 7.47,
    core_balance: float = 7.47,
) -> dict:
    return {
        "asOfDateTime": 1774912387,
        "addlInfoDetail": {
            "isTrustAccount": False,
            "isMarginAccount": False,
            "isLimitedMarginAccount": False,
            "isPortfolioMarginAccount": False,
            "isMultiMarginAccount": False,
            "hasIntradayActivity": False,
            "hasUnpricedOrder": False,
            "hasMarginCalls": False,
            "hasRealTimeBalances": True,
        },
        "recentBalanceDetail": _make_recent_balance_detail(net_worth, core_balance),
    }


def _make_margin_balance_detail() -> dict:
    """Build a recentBalanceDetail for a margin account with all detail blocks."""
    return {
        "asOfDateTime": 1774912387,
        "acctValDetail": {
            "netWorth": 149174.04,
            "netWorthChg": -10648.35,
            "netWorthChgPct": -6.66,
            "marketVal": 149174.04,
            "marketValChg": -10648.35,
            "marketValChgPct": -6.66,
            "acctEqtyPct": 99.79,
            "hasUnpricedPosition": False,
            "regulatoryNetWorth": 149174.04,
            "loanedSecMktVal": 223.21,
        },
        "cashDetail": {
            "heldInCash": 0.00,
            "coreBalance": 3064.58,
            "creditDebit": -317.61,
            "settledAmt": 3064.58,
            "cshMoneyMkt": 3064.58,
        },
        "buyingPowerDetail": {
            "cash": 3382.19,
            "cashChg": -443.33,
            "margin": 11714.40,
            "marginChg": -1037.33,
            "nonMargin": 3514.32,
            "nonMarginChg": -311.20,
            "dayTrade": 116529.58,
            "regulatoryDayTrade": 116852.25,
            "withoutMarginImpact": 3064.58,
            "withoutMarginImpactChg": -317.61,
            "dayTradeCallAmt": 0.0,
            "cashCmtdToOpenOrder": 0.0,
            "cashMarginCmtdToOpenOrder": 0.0,
        },
        "availableToWithdrawDetail": {
            "cashOnly": 3064.58,
            "cashWithMargin": 3064.58,
            "unsettledDeposit": 0.00,
        },
        "marginDetail": {
            "heldInMargin": 149174.04,
            "heldInMarginChg": -10648.35,
            "creditDebit": -317.61,
            "creditDebitChg": 2682.39,
            "equity": 148856.43,
            "equityPct": 99.79,
            "interestRate": 0.0,
            "interestAccruedMTD": 0.0,
            "interestAccruedDaily": 0.0,
            "isPhantomMarginCallsAddressed": True,
            "cashToCoverMarginCalls": 3382.19,
            "maintenanceDetail": {
                "houseCallSurplus": 3521.14,
                "houseCallSurplusChg": -304.38,
                "exchangeCallSurplus": 114930.58,
                "exchangeCallSurplusChg": -8303.86,
                "federalSpecialMemorandumAmt": 133872.56,
                "federalSpecialMemorandumAmtChg": -311.42,
                "houseSecurityRequirement": 148774.90,
            },
        },
        "bondDetail": {
            "corporate": 14057.28,
            "corporateChg": -1244.80,
            "municipal": 17571.60,
            "municipalChg": -1556.00,
            "government": 35143.20,
            "governmentChg": -3112.00,
        },
        "shortDetail": {
            "heldInShort": 0.0,
            "heldInShortChg": 0.0,
            "creditDebit": 0.0,
            "creditDebitChg": 0.0,
            "dailyMarkToMarket": 0.0,
            "dailyMarkToMarketChg": 0.0,
        },
        "optionsDetail": {
            "heldInOption": 14575.00,
            "heldInOptionChg": -37630.00,
            "optionInTheMoney": 0.0,
            "optionRequirement": 0.0,
            "cashCoveredPutReserve": 0.0,
            "cashSpreadReserve": 0.0,
        },
        "simplifiedMarginDetail": {
            "netMarketValue": 163749.04,
            "cashAndCredits": 3064.58,
            "isMarginDebtInGoodOrder": False,
            "nigoReasonCodes": ["RESTRICTION_81"],
            "netMarketValueChg": -48278.35,
            "cashAndCreditsChg": -317.61,
        },
    }


def _make_margin_brokerage_acct_detail() -> dict:
    """Build a full brokerageAcctDetail for a margin account."""
    return {
        "asOfDateTime": 1774912387,
        "addlInfoDetail": {
            "isTrustAccount": False,
            "isMarginAccount": True,
            "isLimitedMarginAccount": False,
            "isPortfolioMarginAccount": False,
            "isMultiMarginAccount": False,
            "hasIntradayActivity": True,
            "hasUnpricedOrder": True,
            "hasMarginCalls": False,
            "hasRealTimeBalances": False,
        },
        "recentBalanceDetail": _make_margin_balance_detail(),
    }


def _make_api_response(acct_nums_and_details: list[tuple[str, dict]]) -> dict:
    return {
        "balances": [
            {
                "acctNum": acct_num,
                "brokerageAcctDetail": detail,
            }
            for acct_num, detail in acct_nums_and_details
        ]
    }


def _make_single_account_response(
    acct_num: str = "257619270",
    net_worth: float = 7.47,
    core_balance: float = 7.47,
) -> dict:
    return _make_api_response([
        (acct_num, _make_brokerage_acct_detail(net_worth, core_balance))
    ])


# ---------------------------------------------------------------------------
# AcctValDetail
# ---------------------------------------------------------------------------

class TestAcctValDetail:
    def test_parses_all_fields(self):
        avd = AcctValDetail.model_validate({
            "netWorth": 7.47,
            "netWorthChg": 0.00,
            "netWorthChgPct": 0.00,
            "marketVal": 0.00,
            "marketValChg": 0.00,
            "marketValChgPct": 0.00,
            "acctEqtyPct": 100.00,
            "hasUnpricedPosition": False,
            "regulatoryNetWorth": 7.47,
        })
        assert avd.net_worth == pytest.approx(7.47)
        assert avd.net_worth_chg == pytest.approx(0.00)
        assert avd.net_worth_chg_pct == pytest.approx(0.00)
        assert avd.market_val == pytest.approx(0.00)
        assert avd.market_val_chg == pytest.approx(0.00)
        assert avd.market_val_chg_pct == pytest.approx(0.00)
        assert avd.acct_eqty_pct == pytest.approx(100.00)
        assert avd.has_unpriced_position is False
        assert avd.regulatory_net_worth == pytest.approx(7.47)

    def test_optional_fields_default_none(self):
        avd = AcctValDetail.model_validate({})
        assert avd.net_worth is None
        assert avd.market_val is None
        assert avd.has_unpriced_position is None

    def test_coerces_string_floats(self):
        avd = AcctValDetail.model_validate({"netWorth": "1234.56"})
        assert avd.net_worth == pytest.approx(1234.56)

    def test_sentinel_strings_become_none(self):
        avd = AcctValDetail.model_validate({"netWorth": "--", "marketVal": "N/A"})
        assert avd.net_worth is None
        assert avd.market_val is None

    def test_negative_net_worth(self):
        avd = AcctValDetail.model_validate({"netWorth": -500.00, "regulatoryNetWorth": -500.00})
        assert avd.net_worth == pytest.approx(-500.00)
        assert avd.regulatory_net_worth == pytest.approx(-500.00)

    def test_loaned_sec_mkt_val(self):
        avd = AcctValDetail.model_validate({"loanedSecMktVal": 223.21})
        assert avd.loaned_sec_mkt_val == pytest.approx(223.21)

    def test_loaned_sec_mkt_val_defaults_none(self):
        avd = AcctValDetail.model_validate({})
        assert avd.loaned_sec_mkt_val is None


# ---------------------------------------------------------------------------
# CashDetail
# ---------------------------------------------------------------------------

class TestCashDetail:
    def test_parses_all_fields(self):
        cd = CashDetail.model_validate({
            "heldInCash": 0.00,
            "coreBalance": 7.47,
            "creditDebit": 0.00,
            "settledAmt": 7.47,
            "cshMoneyMkt": 7.47,
        })
        assert cd.held_in_cash == pytest.approx(0.00)
        assert cd.core_balance == pytest.approx(7.47)
        assert cd.credit_debit == pytest.approx(0.00)
        assert cd.settled_amt == pytest.approx(7.47)
        assert cd.csh_money_mkt == pytest.approx(7.47)

    def test_optional_fields_default_none(self):
        cd = CashDetail.model_validate({})
        assert cd.core_balance is None
        assert cd.settled_amt is None

    def test_negative_credit_debit(self):
        cd = CashDetail.model_validate({"creditDebit": -250.00})
        assert cd.credit_debit == pytest.approx(-250.00)


# ---------------------------------------------------------------------------
# BuyingPowerDetail
# ---------------------------------------------------------------------------

class TestBuyingPowerDetail:
    def test_parses_all_fields(self):
        bp = BuyingPowerDetail.model_validate({
            "cash": 7.47,
            "cashChg": 0.00,
            "cashCmtdToOpenOrder": 0.00,
        })
        assert bp.cash == pytest.approx(7.47)
        assert bp.cash_chg == pytest.approx(0.00)
        assert bp.cash_cmtd_to_open_order == pytest.approx(0.00)

    def test_optional_fields_default_none(self):
        bp = BuyingPowerDetail.model_validate({})
        assert bp.cash is None
        assert bp.cash_chg is None
        assert bp.margin is None
        assert bp.day_trade is None

    def test_committed_to_open_order(self):
        bp = BuyingPowerDetail.model_validate({"cash": 1000.00, "cashCmtdToOpenOrder": 250.00})
        assert bp.cash == pytest.approx(1000.00)
        assert bp.cash_cmtd_to_open_order == pytest.approx(250.00)

    def test_margin_buying_power_fields(self):
        bp = BuyingPowerDetail.model_validate({
            "cash": 3382.19,
            "cashChg": -443.33,
            "margin": 11714.40,
            "marginChg": -1037.33,
            "nonMargin": 3514.32,
            "nonMarginChg": -311.20,
            "dayTrade": 116529.58,
            "regulatoryDayTrade": 116852.25,
            "withoutMarginImpact": 3064.58,
            "withoutMarginImpactChg": -317.61,
            "dayTradeCallAmt": 0.0,
            "cashCmtdToOpenOrder": 0.0,
            "cashMarginCmtdToOpenOrder": 0.0,
        })
        assert bp.margin == pytest.approx(11714.40)
        assert bp.margin_chg == pytest.approx(-1037.33)
        assert bp.non_margin == pytest.approx(3514.32)
        assert bp.non_margin_chg == pytest.approx(-311.20)
        assert bp.day_trade == pytest.approx(116529.58)
        assert bp.regulatory_day_trade == pytest.approx(116852.25)
        assert bp.without_margin_impact == pytest.approx(3064.58)
        assert bp.without_margin_impact_chg == pytest.approx(-317.61)
        assert bp.day_trade_call_amt == pytest.approx(0.0)
        assert bp.cash_margin_cmtd_to_open_order == pytest.approx(0.0)

    def test_non_margin_account_omits_margin_fields(self):
        bp = BuyingPowerDetail.model_validate({
            "cash": 7.47,
            "cashChg": 0.00,
            "cashCmtdToOpenOrder": 0.00,
        })
        assert bp.margin is None
        assert bp.margin_chg is None
        assert bp.day_trade is None
        assert bp.regulatory_day_trade is None
        assert bp.cash_margin_cmtd_to_open_order is None


# ---------------------------------------------------------------------------
# AvailableToWithdrawDetail
# ---------------------------------------------------------------------------

class TestAvailableToWithdrawDetail:
    def test_parses_all_fields(self):
        atw = AvailableToWithdrawDetail.model_validate({
            "cashOnly": 7.47,
            "cashWithMargin": 7.47,
            "unsettledDeposit": 0.00,
        })
        assert atw.cash_only == pytest.approx(7.47)
        assert atw.cash_with_margin == pytest.approx(7.47)
        assert atw.unsettled_deposit == pytest.approx(0.00)

    def test_optional_fields_default_none(self):
        atw = AvailableToWithdrawDetail.model_validate({})
        assert atw.cash_only is None

    def test_unsettled_deposit(self):
        atw = AvailableToWithdrawDetail.model_validate({"unsettledDeposit": 500.00})
        assert atw.unsettled_deposit == pytest.approx(500.00)


# ---------------------------------------------------------------------------
# AddlInfoDetail
# ---------------------------------------------------------------------------

class TestAddlInfoDetail:
    def test_parses_all_bool_fields(self):
        aid = AddlInfoDetail.model_validate({
            "isTrustAccount": False,
            "isMarginAccount": False,
            "isLimitedMarginAccount": False,
            "isPortfolioMarginAccount": False,
            "isMultiMarginAccount": False,
            "hasIntradayActivity": False,
            "hasUnpricedOrder": False,
            "hasMarginCalls": False,
            "hasRealTimeBalances": True,
        })
        assert aid.is_trust_account is False
        assert aid.is_margin_account is False
        assert aid.is_limited_margin_account is False
        assert aid.is_portfolio_margin_account is False
        assert aid.is_multi_margin_account is False
        assert aid.has_intraday_activity is False
        assert aid.has_unpriced_order is False
        assert aid.has_margin_calls is False
        assert aid.has_real_time_balances is True

    def test_margin_account_flag(self):
        aid = AddlInfoDetail.model_validate({"isMarginAccount": True})
        assert aid.is_margin_account is True

    def test_margin_account_all_flags(self):
        aid = AddlInfoDetail.model_validate({
            "isTrustAccount": False,
            "isMarginAccount": True,
            "isLimitedMarginAccount": False,
            "isPortfolioMarginAccount": False,
            "isMultiMarginAccount": False,
            "hasIntradayActivity": True,
            "hasUnpricedOrder": True,
            "hasMarginCalls": False,
            "hasRealTimeBalances": False,
        })
        assert aid.is_margin_account is True
        assert aid.is_multi_margin_account is False
        assert aid.has_intraday_activity is True
        assert aid.has_unpriced_order is True
        assert aid.has_real_time_balances is False

    def test_optional_fields_default_none(self):
        aid = AddlInfoDetail.model_validate({})
        assert aid.is_trust_account is None
        assert aid.has_real_time_balances is None
        assert aid.is_multi_margin_account is None
        assert aid.has_intraday_activity is None


# ---------------------------------------------------------------------------
# MarginMaintenanceDetail
# ---------------------------------------------------------------------------

class TestMarginMaintenanceDetail:
    def test_parses_all_fields(self):
        mmd = MarginMaintenanceDetail.model_validate({
            "houseCallSurplus": 3521.14,
            "houseCallSurplusChg": -304.38,
            "exchangeCallSurplus": 114930.58,
            "exchangeCallSurplusChg": -8303.86,
            "federalSpecialMemorandumAmt": 133872.56,
            "federalSpecialMemorandumAmtChg": -311.42,
            "houseSecurityRequirement": 148774.90,
        })
        assert mmd.house_call_surplus == pytest.approx(3521.14)
        assert mmd.house_call_surplus_chg == pytest.approx(-304.38)
        assert mmd.exchange_call_surplus == pytest.approx(114930.58)
        assert mmd.exchange_call_surplus_chg == pytest.approx(-8303.86)
        assert mmd.federal_special_memorandum_amt == pytest.approx(133872.56)
        assert mmd.federal_special_memorandum_amt_chg == pytest.approx(-311.42)
        assert mmd.house_security_requirement == pytest.approx(148774.90)

    def test_optional_fields_default_none(self):
        mmd = MarginMaintenanceDetail.model_validate({})
        assert mmd.house_call_surplus is None
        assert mmd.exchange_call_surplus is None
        assert mmd.federal_special_memorandum_amt is None
        assert mmd.house_security_requirement is None

    def test_coerces_string_floats(self):
        mmd = MarginMaintenanceDetail.model_validate({"houseCallSurplus": "3521.14"})
        assert mmd.house_call_surplus == pytest.approx(3521.14)

    def test_negative_change_values(self):
        mmd = MarginMaintenanceDetail.model_validate({
            "houseCallSurplusChg": -304.38,
            "exchangeCallSurplusChg": -8303.86,
        })
        assert mmd.house_call_surplus_chg == pytest.approx(-304.38)
        assert mmd.exchange_call_surplus_chg == pytest.approx(-8303.86)


# ---------------------------------------------------------------------------
# MarginDetail
# ---------------------------------------------------------------------------

class TestMarginDetail:
    def test_parses_all_fields(self):
        md = MarginDetail.model_validate({
            "heldInMargin": 149174.04,
            "heldInMarginChg": -10648.35,
            "creditDebit": -317.61,
            "creditDebitChg": 2682.39,
            "equity": 148856.43,
            "equityPct": 99.79,
            "interestRate": 0.0,
            "interestAccruedMTD": 0.0,
            "interestAccruedDaily": 0.0,
            "isPhantomMarginCallsAddressed": True,
            "cashToCoverMarginCalls": 3382.19,
            "maintenanceDetail": {
                "houseCallSurplus": 3521.14,
                "houseCallSurplusChg": -304.38,
                "exchangeCallSurplus": 114930.58,
                "exchangeCallSurplusChg": -8303.86,
                "federalSpecialMemorandumAmt": 133872.56,
                "federalSpecialMemorandumAmtChg": -311.42,
                "houseSecurityRequirement": 148774.90,
            },
        })
        assert md.held_in_margin == pytest.approx(149174.04)
        assert md.held_in_margin_chg == pytest.approx(-10648.35)
        assert md.credit_debit == pytest.approx(-317.61)
        assert md.credit_debit_chg == pytest.approx(2682.39)
        assert md.equity == pytest.approx(148856.43)
        assert md.equity_pct == pytest.approx(99.79)
        assert md.interest_rate == pytest.approx(0.0)
        assert md.interest_accrued_mtd == pytest.approx(0.0)
        assert md.interest_accrued_daily == pytest.approx(0.0)
        assert md.is_phantom_margin_calls_addressed is True
        assert md.cash_to_cover_margin_calls == pytest.approx(3382.19)
        assert md.maintenance_detail is not None
        assert md.maintenance_detail.house_call_surplus == pytest.approx(3521.14)

    def test_optional_fields_default_none(self):
        md = MarginDetail.model_validate({})
        assert md.held_in_margin is None
        assert md.equity is None
        assert md.maintenance_detail is None
        assert md.is_phantom_margin_calls_addressed is None

    def test_without_maintenance_detail(self):
        md = MarginDetail.model_validate({
            "heldInMargin": 5000.0,
            "equity": 4800.0,
        })
        assert md.held_in_margin == pytest.approx(5000.0)
        assert md.maintenance_detail is None

    def test_negative_credit_debit(self):
        md = MarginDetail.model_validate({"creditDebit": -317.61})
        assert md.credit_debit == pytest.approx(-317.61)

    def test_coerces_string_floats(self):
        md = MarginDetail.model_validate({"heldInMargin": "149174.04"})
        assert md.held_in_margin == pytest.approx(149174.04)


# ---------------------------------------------------------------------------
# BondDetail
# ---------------------------------------------------------------------------

class TestBondDetail:
    def test_parses_all_fields(self):
        bd = BondDetail.model_validate({
            "corporate": 14057.28,
            "corporateChg": -1244.80,
            "municipal": 17571.60,
            "municipalChg": -1556.00,
            "government": 35143.20,
            "governmentChg": -3112.00,
        })
        assert bd.corporate == pytest.approx(14057.28)
        assert bd.corporate_chg == pytest.approx(-1244.80)
        assert bd.municipal == pytest.approx(17571.60)
        assert bd.municipal_chg == pytest.approx(-1556.00)
        assert bd.government == pytest.approx(35143.20)
        assert bd.government_chg == pytest.approx(-3112.00)

    def test_optional_fields_default_none(self):
        bd = BondDetail.model_validate({})
        assert bd.corporate is None
        assert bd.municipal is None
        assert bd.government is None

    def test_coerces_string_floats(self):
        bd = BondDetail.model_validate({"corporate": "14057.28"})
        assert bd.corporate == pytest.approx(14057.28)

    def test_zero_values(self):
        bd = BondDetail.model_validate({
            "corporate": 0.0,
            "municipal": 0.0,
            "government": 0.0,
        })
        assert bd.corporate == pytest.approx(0.0)
        assert bd.municipal == pytest.approx(0.0)
        assert bd.government == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# ShortDetail
# ---------------------------------------------------------------------------

class TestShortDetail:
    def test_parses_all_fields(self):
        sd = ShortDetail.model_validate({
            "heldInShort": 5000.0,
            "heldInShortChg": -200.0,
            "creditDebit": 1000.0,
            "creditDebitChg": -50.0,
            "dailyMarkToMarket": 150.0,
            "dailyMarkToMarketChg": -10.0,
        })
        assert sd.held_in_short == pytest.approx(5000.0)
        assert sd.held_in_short_chg == pytest.approx(-200.0)
        assert sd.credit_debit == pytest.approx(1000.0)
        assert sd.credit_debit_chg == pytest.approx(-50.0)
        assert sd.daily_mark_to_market == pytest.approx(150.0)
        assert sd.daily_mark_to_market_chg == pytest.approx(-10.0)

    def test_optional_fields_default_none(self):
        sd = ShortDetail.model_validate({})
        assert sd.held_in_short is None
        assert sd.credit_debit is None
        assert sd.daily_mark_to_market is None

    def test_all_zeros(self):
        sd = ShortDetail.model_validate({
            "heldInShort": 0.0,
            "heldInShortChg": 0.0,
            "creditDebit": 0.0,
            "creditDebitChg": 0.0,
            "dailyMarkToMarket": 0.0,
            "dailyMarkToMarketChg": 0.0,
        })
        assert sd.held_in_short == pytest.approx(0.0)
        assert sd.daily_mark_to_market == pytest.approx(0.0)

    def test_coerces_string_floats(self):
        sd = ShortDetail.model_validate({"heldInShort": "5000.0"})
        assert sd.held_in_short == pytest.approx(5000.0)


# ---------------------------------------------------------------------------
# OptionsDetail
# ---------------------------------------------------------------------------

class TestOptionsDetail:
    def test_parses_all_fields(self):
        od = OptionsDetail.model_validate({
            "heldInOption": 14575.00,
            "heldInOptionChg": -37630.00,
            "optionInTheMoney": 0.0,
            "optionRequirement": 0.0,
            "cashCoveredPutReserve": 0.0,
            "cashSpreadReserve": 0.0,
        })
        assert od.held_in_option == pytest.approx(14575.00)
        assert od.held_in_option_chg == pytest.approx(-37630.00)
        assert od.option_in_the_money == pytest.approx(0.0)
        assert od.option_requirement == pytest.approx(0.0)
        assert od.cash_covered_put_reserve == pytest.approx(0.0)
        assert od.cash_spread_reserve == pytest.approx(0.0)

    def test_optional_fields_default_none(self):
        od = OptionsDetail.model_validate({})
        assert od.held_in_option is None
        assert od.option_in_the_money is None
        assert od.cash_covered_put_reserve is None

    def test_large_negative_change(self):
        od = OptionsDetail.model_validate({"heldInOptionChg": -37630.00})
        assert od.held_in_option_chg == pytest.approx(-37630.00)

    def test_coerces_string_floats(self):
        od = OptionsDetail.model_validate({"heldInOption": "14575.00"})
        assert od.held_in_option == pytest.approx(14575.00)


# ---------------------------------------------------------------------------
# SimplifiedMarginDetail
# ---------------------------------------------------------------------------

class TestSimplifiedMarginDetail:
    def test_parses_all_fields(self):
        smd = SimplifiedMarginDetail.model_validate({
            "netMarketValue": 163749.04,
            "cashAndCredits": 3064.58,
            "isMarginDebtInGoodOrder": False,
            "nigoReasonCodes": ["RESTRICTION_81"],
            "netMarketValueChg": -48278.35,
            "cashAndCreditsChg": -317.61,
        })
        assert smd.net_market_value == pytest.approx(163749.04)
        assert smd.cash_and_credits == pytest.approx(3064.58)
        assert smd.is_margin_debt_in_good_order is False
        assert smd.nigo_reason_codes == ["RESTRICTION_81"]
        assert smd.net_market_value_chg == pytest.approx(-48278.35)
        assert smd.cash_and_credits_chg == pytest.approx(-317.61)

    def test_optional_fields_default_none(self):
        smd = SimplifiedMarginDetail.model_validate({})
        assert smd.net_market_value is None
        assert smd.is_margin_debt_in_good_order is None
        assert smd.nigo_reason_codes is None

    def test_in_good_order_with_no_nigo_codes(self):
        smd = SimplifiedMarginDetail.model_validate({
            "netMarketValue": 100000.0,
            "isMarginDebtInGoodOrder": True,
            "nigoReasonCodes": [],
        })
        assert smd.is_margin_debt_in_good_order is True
        assert smd.nigo_reason_codes == []

    def test_multiple_nigo_reason_codes(self):
        smd = SimplifiedMarginDetail.model_validate({
            "isMarginDebtInGoodOrder": False,
            "nigoReasonCodes": ["RESTRICTION_81", "RESTRICTION_82"],
        })
        assert smd.nigo_reason_codes == ["RESTRICTION_81", "RESTRICTION_82"]

    def test_coerces_string_floats(self):
        smd = SimplifiedMarginDetail.model_validate({"netMarketValue": "163749.04"})
        assert smd.net_market_value == pytest.approx(163749.04)


# ---------------------------------------------------------------------------
# BalanceTimingDetail
# ---------------------------------------------------------------------------

class TestBalanceTimingDetail:
    def test_parses_all_nested_models(self):
        btd = BalanceTimingDetail.model_validate(_make_recent_balance_detail())
        assert btd.as_of_date_time == 1774912387
        assert btd.acct_val_detail is not None
        assert btd.cash_detail is not None
        assert btd.buying_power_detail is not None
        assert btd.available_to_withdraw_detail is not None

    def test_acct_val_detail_values(self):
        btd = BalanceTimingDetail.model_validate(_make_recent_balance_detail(net_worth=1000.00))
        assert btd.acct_val_detail.net_worth == pytest.approx(1000.00)

    def test_cash_detail_core_balance(self):
        btd = BalanceTimingDetail.model_validate(_make_recent_balance_detail(core_balance=500.00))
        assert btd.cash_detail.core_balance == pytest.approx(500.00)

    def test_buying_power_cash(self):
        btd = BalanceTimingDetail.model_validate(_make_recent_balance_detail(cash_bp=250.00))
        assert btd.buying_power_detail.cash == pytest.approx(250.00)

    def test_optional_nested_models_default_none(self):
        btd = BalanceTimingDetail.model_validate({})
        assert btd.acct_val_detail is None
        assert btd.cash_detail is None
        assert btd.margin_detail is None
        assert btd.bond_detail is None
        assert btd.short_detail is None
        assert btd.options_detail is None
        assert btd.simplified_margin_detail is None

    def test_parses_margin_balance_detail(self):
        btd = BalanceTimingDetail.model_validate(_make_margin_balance_detail())
        assert btd.margin_detail is not None
        assert btd.margin_detail.held_in_margin == pytest.approx(149174.04)
        assert btd.margin_detail.equity == pytest.approx(148856.43)
        assert btd.margin_detail.maintenance_detail is not None
        assert btd.margin_detail.maintenance_detail.house_call_surplus == pytest.approx(3521.14)

    def test_parses_bond_detail(self):
        btd = BalanceTimingDetail.model_validate(_make_margin_balance_detail())
        assert btd.bond_detail is not None
        assert btd.bond_detail.corporate == pytest.approx(14057.28)
        assert btd.bond_detail.municipal == pytest.approx(17571.60)
        assert btd.bond_detail.government == pytest.approx(35143.20)

    def test_parses_short_detail(self):
        btd = BalanceTimingDetail.model_validate(_make_margin_balance_detail())
        assert btd.short_detail is not None
        assert btd.short_detail.held_in_short == pytest.approx(0.0)

    def test_parses_options_detail(self):
        btd = BalanceTimingDetail.model_validate(_make_margin_balance_detail())
        assert btd.options_detail is not None
        assert btd.options_detail.held_in_option == pytest.approx(14575.00)
        assert btd.options_detail.held_in_option_chg == pytest.approx(-37630.00)

    def test_parses_simplified_margin_detail(self):
        btd = BalanceTimingDetail.model_validate(_make_margin_balance_detail())
        assert btd.simplified_margin_detail is not None
        assert btd.simplified_margin_detail.net_market_value == pytest.approx(163749.04)
        assert btd.simplified_margin_detail.is_margin_debt_in_good_order is False
        assert btd.simplified_margin_detail.nigo_reason_codes == ["RESTRICTION_81"]

    def test_margin_buying_power_fields(self):
        btd = BalanceTimingDetail.model_validate(_make_margin_balance_detail())
        bp = btd.buying_power_detail
        assert bp.margin == pytest.approx(11714.40)
        assert bp.day_trade == pytest.approx(116529.58)
        assert bp.regulatory_day_trade == pytest.approx(116852.25)

    def test_loaned_sec_mkt_val_in_acct_val(self):
        btd = BalanceTimingDetail.model_validate(_make_margin_balance_detail())
        assert btd.acct_val_detail.loaned_sec_mkt_val == pytest.approx(223.21)

    def test_non_margin_account_omits_detail_blocks(self):
        btd = BalanceTimingDetail.model_validate(_make_recent_balance_detail())
        assert btd.margin_detail is None
        assert btd.bond_detail is None
        assert btd.short_detail is None
        assert btd.options_detail is None
        assert btd.simplified_margin_detail is None


# ---------------------------------------------------------------------------
# AccountBalance
# ---------------------------------------------------------------------------

class TestAccountBalance:
    def test_parses_full_account_balance(self):
        raw = {
            "acctNum": "257619270",
            "brokerageAcctDetail": _make_brokerage_acct_detail(),
        }
        ab = AccountBalance.model_validate(raw)
        assert ab.acct_num == "257619270"
        assert ab.addl_info_detail is not None
        assert ab.recent_balance_detail is not None
        assert ab.intraday_balance_detail is None
        assert ab.close_balance_detail is None

    def test_addl_info_detail_flags(self):
        raw = {
            "acctNum": "257619270",
            "brokerageAcctDetail": _make_brokerage_acct_detail(),
        }
        ab = AccountBalance.model_validate(raw)
        assert ab.addl_info_detail.has_real_time_balances is True
        assert ab.addl_info_detail.is_margin_account is False

    def test_recent_balance_detail_net_worth(self):
        raw = {
            "acctNum": "257619270",
            "brokerageAcctDetail": _make_brokerage_acct_detail(net_worth=5000.00),
        }
        ab = AccountBalance.model_validate(raw)
        assert ab.recent_balance_detail.acct_val_detail.net_worth == pytest.approx(5000.00)

    def test_intraday_and_close_balance_optional(self):
        brokerage = dict(_make_brokerage_acct_detail())
        brokerage["intradayBalanceDetail"] = _make_recent_balance_detail(net_worth=4900.00)
        brokerage["closeBalanceDetail"] = _make_recent_balance_detail(net_worth=4800.00)
        raw = {"acctNum": "257619270", "brokerageAcctDetail": brokerage}
        ab = AccountBalance.model_validate(raw)
        assert ab.intraday_balance_detail is not None
        assert ab.intraday_balance_detail.acct_val_detail.net_worth == pytest.approx(4900.00)
        assert ab.close_balance_detail is not None
        assert ab.close_balance_detail.acct_val_detail.net_worth == pytest.approx(4800.00)

    def test_missing_brokerage_detail(self):
        """AccountBalance with no brokerageAcctDetail still parses acctNum."""
        raw = {"acctNum": "999999999"}
        ab = AccountBalance.model_validate(raw)
        assert ab.acct_num == "999999999"
        assert ab.addl_info_detail is None
        assert ab.recent_balance_detail is None

    def test_margin_account_full_parse(self):
        raw = {
            "acctNum": "MARGIN001",
            "brokerageAcctDetail": _make_margin_brokerage_acct_detail(),
        }
        ab = AccountBalance.model_validate(raw)
        assert ab.acct_num == "MARGIN001"
        assert ab.addl_info_detail.is_margin_account is True
        assert ab.addl_info_detail.has_intraday_activity is True
        rbd = ab.recent_balance_detail
        assert rbd.margin_detail is not None
        assert rbd.margin_detail.held_in_margin == pytest.approx(149174.04)
        assert rbd.bond_detail is not None
        assert rbd.short_detail is not None
        assert rbd.options_detail is not None
        assert rbd.simplified_margin_detail is not None
        assert rbd.acct_val_detail.loaned_sec_mkt_val == pytest.approx(223.21)
        assert rbd.buying_power_detail.margin == pytest.approx(11714.40)

    def test_margin_account_maintenance_detail_deep(self):
        raw = {
            "acctNum": "MARGIN001",
            "brokerageAcctDetail": _make_margin_brokerage_acct_detail(),
        }
        ab = AccountBalance.model_validate(raw)
        maint = ab.recent_balance_detail.margin_detail.maintenance_detail
        assert maint.house_call_surplus == pytest.approx(3521.14)
        assert maint.exchange_call_surplus == pytest.approx(114930.58)
        assert maint.federal_special_memorandum_amt == pytest.approx(133872.56)
        assert maint.house_security_requirement == pytest.approx(148774.90)


# ---------------------------------------------------------------------------
# BalancesResponse — full integration parsing
# ---------------------------------------------------------------------------

class TestBalancesResponse:
    def test_single_account(self):
        raw = _make_single_account_response("257619270", net_worth=7.47)
        resp = BalancesResponse.from_api_response(raw)
        assert len(resp.accounts) == 1
        assert resp.accounts[0].acct_num == "257619270"

    def test_net_worth_field(self):
        raw = _make_single_account_response("257619270", net_worth=7.47)
        resp = BalancesResponse.from_api_response(raw)
        avd = resp.accounts[0].recent_balance_detail.acct_val_detail
        assert avd.net_worth == pytest.approx(7.47)

    def test_cash_detail_fields(self):
        raw = _make_single_account_response("257619270", core_balance=7.47)
        resp = BalancesResponse.from_api_response(raw)
        cd = resp.accounts[0].recent_balance_detail.cash_detail
        assert cd.core_balance == pytest.approx(7.47)
        assert cd.settled_amt == pytest.approx(7.47)
        assert cd.csh_money_mkt == pytest.approx(7.47)

    def test_buying_power_fields(self):
        raw = _make_single_account_response("257619270", net_worth=7.47)
        resp = BalancesResponse.from_api_response(raw)
        bp = resp.accounts[0].recent_balance_detail.buying_power_detail
        assert bp.cash == pytest.approx(7.47)
        assert bp.cash_chg == pytest.approx(0.00)
        assert bp.cash_cmtd_to_open_order == pytest.approx(0.00)

    def test_available_to_withdraw_fields(self):
        raw = _make_single_account_response("257619270", net_worth=7.47)
        resp = BalancesResponse.from_api_response(raw)
        atw = resp.accounts[0].recent_balance_detail.available_to_withdraw_detail
        assert atw.cash_only == pytest.approx(7.47)
        assert atw.cash_with_margin == pytest.approx(7.47)
        assert atw.unsettled_deposit == pytest.approx(0.00)

    def test_multiple_accounts(self):
        raw = _make_api_response([
            ("ACC001", _make_brokerage_acct_detail(net_worth=1000.00)),
            ("ACC002", _make_brokerage_acct_detail(net_worth=2500.00)),
            ("ACC003", _make_brokerage_acct_detail(net_worth=50000.00)),
        ])
        resp = BalancesResponse.from_api_response(raw)
        assert len(resp.accounts) == 3
        assert resp.accounts[0].acct_num == "ACC001"
        assert resp.accounts[1].acct_num == "ACC002"
        assert resp.accounts[2].acct_num == "ACC003"
        assert resp.accounts[0].recent_balance_detail.acct_val_detail.net_worth == pytest.approx(1000.00)
        assert resp.accounts[2].recent_balance_detail.acct_val_detail.net_worth == pytest.approx(50000.00)

    def test_empty_response_body(self):
        resp = BalancesResponse.from_api_response({})
        assert resp.accounts == []

    def test_empty_balances_list(self):
        resp = BalancesResponse.from_api_response({"balances": []})
        assert resp.accounts == []

    def test_margin_account_response(self):
        raw = _make_api_response([
            ("MARGIN001", _make_margin_brokerage_acct_detail()),
        ])
        resp = BalancesResponse.from_api_response(raw)
        assert len(resp.accounts) == 1
        acct = resp.accounts[0]
        assert acct.addl_info_detail.is_margin_account is True
        rbd = acct.recent_balance_detail
        assert rbd.margin_detail.held_in_margin == pytest.approx(149174.04)
        assert rbd.bond_detail.corporate == pytest.approx(14057.28)
        assert rbd.options_detail.held_in_option == pytest.approx(14575.00)
        assert rbd.simplified_margin_detail.nigo_reason_codes == ["RESTRICTION_81"]

    def test_mixed_cash_and_margin_accounts(self):
        raw = _make_api_response([
            ("CASH001", _make_brokerage_acct_detail(net_worth=7.47)),
            ("MARGIN001", _make_margin_brokerage_acct_detail()),
        ])
        resp = BalancesResponse.from_api_response(raw)
        assert len(resp.accounts) == 2
        # Cash account should have no margin details
        cash_acct = resp.accounts[0]
        assert cash_acct.addl_info_detail.is_margin_account is False
        assert cash_acct.recent_balance_detail.margin_detail is None
        assert cash_acct.recent_balance_detail.bond_detail is None
        # Margin account should have all detail blocks
        margin_acct = resp.accounts[1]
        assert margin_acct.addl_info_detail.is_margin_account is True
        assert margin_acct.recent_balance_detail.margin_detail is not None
        assert margin_acct.recent_balance_detail.bond_detail is not None


# ---------------------------------------------------------------------------
# BalancesAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestBalancesAPI:
    @respx.mock
    def test_get_balances_makes_correct_request(self):
        raw_response = _make_single_account_response("257619270")
        route = respx.post(f"{DPSERVICE_URL}/ftgw/dp/balance/detail/v2").mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = BalancesAPI(client)
        result = api.get_balances(["257619270"])

        assert route.called
        assert isinstance(result, BalancesResponse)
        assert len(result.accounts) == 1
        assert result.accounts[0].acct_num == "257619270"

    @respx.mock
    def test_get_balances_request_body_shape(self):
        raw_response = _make_single_account_response("257619270")
        route = respx.post(f"{DPSERVICE_URL}/ftgw/dp/balance/detail/v2").mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = BalancesAPI(client)
        api.get_balances(["257619270"])

        sent_body = json.loads(route.calls[0].request.content)
        params = sent_body["request"]["parameter"]

        # filters / priceTiming
        price_timing = params["filters"]["priceTiming"]
        assert price_timing["includeRecent"] is True
        assert price_timing["includeIntraday"] is True
        assert price_timing["includeClose"] is True

        # filters / requestedData
        req_data = params["filters"]["requestedData"]
        assert req_data["includeAddlInfoDetail"] is True
        assert req_data["includeAcctValDetail"] is True
        assert req_data["includeCashDetail"] is True
        assert req_data["includeBuyingPowerDetail"] is True
        assert req_data["includeAvailableToWithdrawDetail"] is True

        # top-level filter flags from capture
        assert params["filters"]["includeGrossLiquidityVal"] is False
        assert params["filters"]["includeDeposits"] is False

        # account detail
        acct_detail = params["acctDetails"]["acctDetail"]
        assert len(acct_detail) == 1
        assert acct_detail[0]["acctNum"] == "257619270"
        assert acct_detail[0]["acctType"] == "Brokerage"
        assert acct_detail[0]["acctSubType"] == "Brokerage"
        assert acct_detail[0]["hardToBorrow"] is False

    @respx.mock
    def test_get_balances_default_account_type_is_brokerage(self):
        raw_response = _make_single_account_response("123456789")
        route = respx.post(f"{DPSERVICE_URL}/ftgw/dp/balance/detail/v2").mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = BalancesAPI(client)
        api.get_balances(["123456789"])

        sent_body = json.loads(route.calls[0].request.content)
        acct_detail = sent_body["request"]["parameter"]["acctDetails"]["acctDetail"]
        assert acct_detail[0]["acctType"] == "Brokerage"

    @respx.mock
    def test_get_balances_custom_account_types(self):
        raw_response = _make_single_account_response("IRA999")
        route = respx.post(f"{DPSERVICE_URL}/ftgw/dp/balance/detail/v2").mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        custom_types = [
            {
                "acctType": "IRA",
                "acctNum": "IRA999",
                "acctSubType": "Roth",
                "hardToBorrow": False,
                "multiMarginSummaryInd": False,
                "filiSystem": None,
                "depositsInd": False,
                "clientID": None,
            }
        ]
        client = httpx.Client()
        api = BalancesAPI(client)
        api.get_balances(["IRA999"], account_types=custom_types)

        sent_body = json.loads(route.calls[0].request.content)
        acct_detail = sent_body["request"]["parameter"]["acctDetails"]["acctDetail"]
        assert acct_detail[0]["acctType"] == "IRA"
        assert acct_detail[0]["acctSubType"] == "Roth"

    @respx.mock
    def test_get_balances_raises_on_http_error(self):
        respx.post(f"{DPSERVICE_URL}/ftgw/dp/balance/detail/v2").mock(
            return_value=httpx.Response(401)
        )
        client = httpx.Client()
        api = BalancesAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_balances(["257619270"])

    @respx.mock
    def test_get_balances_multiple_accounts_request_body(self):
        raw_response = _make_api_response([
            ("ACC001", _make_brokerage_acct_detail(net_worth=1000.00)),
            ("ACC002", _make_brokerage_acct_detail(net_worth=2500.00)),
        ])
        route = respx.post(f"{DPSERVICE_URL}/ftgw/dp/balance/detail/v2").mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = BalancesAPI(client)
        result = api.get_balances(["ACC001", "ACC002"])

        sent_body = json.loads(route.calls[0].request.content)
        acct_detail = sent_body["request"]["parameter"]["acctDetails"]["acctDetail"]
        assert len(acct_detail) == 2
        assert acct_detail[0]["acctNum"] == "ACC001"
        assert acct_detail[1]["acctNum"] == "ACC002"
        assert len(result.accounts) == 2

    @respx.mock
    def test_get_balances_returns_balances_response_type(self):
        raw_response = _make_single_account_response("257619270")
        respx.post(f"{DPSERVICE_URL}/ftgw/dp/balance/detail/v2").mock(
            return_value=httpx.Response(200, json=raw_response)
        )
        client = httpx.Client()
        api = BalancesAPI(client)
        result = api.get_balances(["257619270"])
        assert isinstance(result, BalancesResponse)
