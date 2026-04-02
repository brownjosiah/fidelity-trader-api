from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from fidelity_trader.models._parsers import _parse_float


# ---------------------------------------------------------------------------
# Sub-models — leaf detail blocks
# ---------------------------------------------------------------------------

class AcctValDetail(BaseModel):
    model_config = {"populate_by_name": True}

    net_worth: Optional[float] = Field(default=None, alias="netWorth")
    net_worth_chg: Optional[float] = Field(default=None, alias="netWorthChg")
    net_worth_chg_pct: Optional[float] = Field(default=None, alias="netWorthChgPct")
    market_val: Optional[float] = Field(default=None, alias="marketVal")
    market_val_chg: Optional[float] = Field(default=None, alias="marketValChg")
    market_val_chg_pct: Optional[float] = Field(default=None, alias="marketValChgPct")
    acct_eqty_pct: Optional[float] = Field(default=None, alias="acctEqtyPct")
    has_unpriced_position: Optional[bool] = Field(default=None, alias="hasUnpricedPosition")
    regulatory_net_worth: Optional[float] = Field(default=None, alias="regulatoryNetWorth")
    loaned_sec_mkt_val: Optional[float] = Field(default=None, alias="loanedSecMktVal")

    @field_validator(
        "net_worth",
        "net_worth_chg",
        "net_worth_chg_pct",
        "market_val",
        "market_val_chg",
        "market_val_chg_pct",
        "acct_eqty_pct",
        "regulatory_net_worth",
        "loaned_sec_mkt_val",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class CashDetail(BaseModel):
    model_config = {"populate_by_name": True}

    held_in_cash: Optional[float] = Field(default=None, alias="heldInCash")
    core_balance: Optional[float] = Field(default=None, alias="coreBalance")
    credit_debit: Optional[float] = Field(default=None, alias="creditDebit")
    settled_amt: Optional[float] = Field(default=None, alias="settledAmt")
    csh_money_mkt: Optional[float] = Field(default=None, alias="cshMoneyMkt")

    @field_validator(
        "held_in_cash",
        "core_balance",
        "credit_debit",
        "settled_amt",
        "csh_money_mkt",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class BuyingPowerDetail(BaseModel):
    model_config = {"populate_by_name": True}

    cash: Optional[float] = Field(default=None, alias="cash")
    cash_chg: Optional[float] = Field(default=None, alias="cashChg")
    margin: Optional[float] = Field(default=None, alias="margin")
    margin_chg: Optional[float] = Field(default=None, alias="marginChg")
    non_margin: Optional[float] = Field(default=None, alias="nonMargin")
    non_margin_chg: Optional[float] = Field(default=None, alias="nonMarginChg")
    day_trade: Optional[float] = Field(default=None, alias="dayTrade")
    regulatory_day_trade: Optional[float] = Field(default=None, alias="regulatoryDayTrade")
    without_margin_impact: Optional[float] = Field(default=None, alias="withoutMarginImpact")
    without_margin_impact_chg: Optional[float] = Field(default=None, alias="withoutMarginImpactChg")
    day_trade_call_amt: Optional[float] = Field(default=None, alias="dayTradeCallAmt")
    cash_cmtd_to_open_order: Optional[float] = Field(default=None, alias="cashCmtdToOpenOrder")
    cash_margin_cmtd_to_open_order: Optional[float] = Field(
        default=None, alias="cashMarginCmtdToOpenOrder"
    )

    @field_validator(
        "cash",
        "cash_chg",
        "margin",
        "margin_chg",
        "non_margin",
        "non_margin_chg",
        "day_trade",
        "regulatory_day_trade",
        "without_margin_impact",
        "without_margin_impact_chg",
        "day_trade_call_amt",
        "cash_cmtd_to_open_order",
        "cash_margin_cmtd_to_open_order",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class AvailableToWithdrawDetail(BaseModel):
    model_config = {"populate_by_name": True}

    cash_only: Optional[float] = Field(default=None, alias="cashOnly")
    cash_with_margin: Optional[float] = Field(default=None, alias="cashWithMargin")
    unsettled_deposit: Optional[float] = Field(default=None, alias="unsettledDeposit")

    @field_validator("cash_only", "cash_with_margin", "unsettled_deposit", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class AddlInfoDetail(BaseModel):
    model_config = {"populate_by_name": True}

    is_trust_account: Optional[bool] = Field(default=None, alias="isTrustAccount")
    is_margin_account: Optional[bool] = Field(default=None, alias="isMarginAccount")
    is_limited_margin_account: Optional[bool] = Field(default=None, alias="isLimitedMarginAccount")
    is_portfolio_margin_account: Optional[bool] = Field(default=None, alias="isPortfolioMarginAccount")
    is_multi_margin_account: Optional[bool] = Field(default=None, alias="isMultiMarginAccount")
    has_intraday_activity: Optional[bool] = Field(default=None, alias="hasIntradayActivity")
    has_unpriced_order: Optional[bool] = Field(default=None, alias="hasUnpricedOrder")
    has_margin_calls: Optional[bool] = Field(default=None, alias="hasMarginCalls")
    has_real_time_balances: Optional[bool] = Field(default=None, alias="hasRealTimeBalances")


# ---------------------------------------------------------------------------
# Margin / options / short / bond detail sub-models
# ---------------------------------------------------------------------------

class MarginMaintenanceDetail(BaseModel):
    model_config = {"populate_by_name": True}

    house_call_surplus: Optional[float] = Field(default=None, alias="houseCallSurplus")
    house_call_surplus_chg: Optional[float] = Field(default=None, alias="houseCallSurplusChg")
    exchange_call_surplus: Optional[float] = Field(default=None, alias="exchangeCallSurplus")
    exchange_call_surplus_chg: Optional[float] = Field(
        default=None, alias="exchangeCallSurplusChg"
    )
    federal_special_memorandum_amt: Optional[float] = Field(
        default=None, alias="federalSpecialMemorandumAmt"
    )
    federal_special_memorandum_amt_chg: Optional[float] = Field(
        default=None, alias="federalSpecialMemorandumAmtChg"
    )
    house_security_requirement: Optional[float] = Field(
        default=None, alias="houseSecurityRequirement"
    )

    @field_validator(
        "house_call_surplus",
        "house_call_surplus_chg",
        "exchange_call_surplus",
        "exchange_call_surplus_chg",
        "federal_special_memorandum_amt",
        "federal_special_memorandum_amt_chg",
        "house_security_requirement",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class MarginDetail(BaseModel):
    model_config = {"populate_by_name": True}

    held_in_margin: Optional[float] = Field(default=None, alias="heldInMargin")
    held_in_margin_chg: Optional[float] = Field(default=None, alias="heldInMarginChg")
    credit_debit: Optional[float] = Field(default=None, alias="creditDebit")
    credit_debit_chg: Optional[float] = Field(default=None, alias="creditDebitChg")
    equity: Optional[float] = Field(default=None, alias="equity")
    equity_pct: Optional[float] = Field(default=None, alias="equityPct")
    interest_rate: Optional[float] = Field(default=None, alias="interestRate")
    interest_accrued_mtd: Optional[float] = Field(default=None, alias="interestAccruedMTD")
    interest_accrued_daily: Optional[float] = Field(default=None, alias="interestAccruedDaily")
    is_phantom_margin_calls_addressed: Optional[bool] = Field(
        default=None, alias="isPhantomMarginCallsAddressed"
    )
    cash_to_cover_margin_calls: Optional[float] = Field(
        default=None, alias="cashToCoverMarginCalls"
    )
    maintenance_detail: Optional[MarginMaintenanceDetail] = Field(
        default=None, alias="maintenanceDetail"
    )

    @field_validator(
        "held_in_margin",
        "held_in_margin_chg",
        "credit_debit",
        "credit_debit_chg",
        "equity",
        "equity_pct",
        "interest_rate",
        "interest_accrued_mtd",
        "interest_accrued_daily",
        "cash_to_cover_margin_calls",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class BondDetail(BaseModel):
    model_config = {"populate_by_name": True}

    corporate: Optional[float] = Field(default=None, alias="corporate")
    corporate_chg: Optional[float] = Field(default=None, alias="corporateChg")
    municipal: Optional[float] = Field(default=None, alias="municipal")
    municipal_chg: Optional[float] = Field(default=None, alias="municipalChg")
    government: Optional[float] = Field(default=None, alias="government")
    government_chg: Optional[float] = Field(default=None, alias="governmentChg")

    @field_validator(
        "corporate",
        "corporate_chg",
        "municipal",
        "municipal_chg",
        "government",
        "government_chg",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class ShortDetail(BaseModel):
    model_config = {"populate_by_name": True}

    held_in_short: Optional[float] = Field(default=None, alias="heldInShort")
    held_in_short_chg: Optional[float] = Field(default=None, alias="heldInShortChg")
    credit_debit: Optional[float] = Field(default=None, alias="creditDebit")
    credit_debit_chg: Optional[float] = Field(default=None, alias="creditDebitChg")
    daily_mark_to_market: Optional[float] = Field(default=None, alias="dailyMarkToMarket")
    daily_mark_to_market_chg: Optional[float] = Field(
        default=None, alias="dailyMarkToMarketChg"
    )

    @field_validator(
        "held_in_short",
        "held_in_short_chg",
        "credit_debit",
        "credit_debit_chg",
        "daily_mark_to_market",
        "daily_mark_to_market_chg",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class OptionsDetail(BaseModel):
    model_config = {"populate_by_name": True}

    held_in_option: Optional[float] = Field(default=None, alias="heldInOption")
    held_in_option_chg: Optional[float] = Field(default=None, alias="heldInOptionChg")
    option_in_the_money: Optional[float] = Field(default=None, alias="optionInTheMoney")
    option_requirement: Optional[float] = Field(default=None, alias="optionRequirement")
    cash_covered_put_reserve: Optional[float] = Field(
        default=None, alias="cashCoveredPutReserve"
    )
    cash_spread_reserve: Optional[float] = Field(default=None, alias="cashSpreadReserve")

    @field_validator(
        "held_in_option",
        "held_in_option_chg",
        "option_in_the_money",
        "option_requirement",
        "cash_covered_put_reserve",
        "cash_spread_reserve",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class SimplifiedMarginDetail(BaseModel):
    model_config = {"populate_by_name": True}

    net_market_value: Optional[float] = Field(default=None, alias="netMarketValue")
    net_market_value_chg: Optional[float] = Field(default=None, alias="netMarketValueChg")
    cash_and_credits: Optional[float] = Field(default=None, alias="cashAndCredits")
    cash_and_credits_chg: Optional[float] = Field(default=None, alias="cashAndCreditsChg")
    is_margin_debt_in_good_order: Optional[bool] = Field(
        default=None, alias="isMarginDebtInGoodOrder"
    )
    nigo_reason_codes: Optional[List[str]] = Field(default=None, alias="nigoReasonCodes")

    @field_validator(
        "net_market_value",
        "net_market_value_chg",
        "cash_and_credits",
        "cash_and_credits_chg",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


# ---------------------------------------------------------------------------
# BalanceTimingDetail — used for recent / intraday / close balance snapshots
# ---------------------------------------------------------------------------

class BalanceTimingDetail(BaseModel):
    model_config = {"populate_by_name": True}

    as_of_date_time: Optional[int] = Field(default=None, alias="asOfDateTime")
    acct_val_detail: Optional[AcctValDetail] = Field(default=None, alias="acctValDetail")
    cash_detail: Optional[CashDetail] = Field(default=None, alias="cashDetail")
    buying_power_detail: Optional[BuyingPowerDetail] = Field(default=None, alias="buyingPowerDetail")
    available_to_withdraw_detail: Optional[AvailableToWithdrawDetail] = Field(
        default=None, alias="availableToWithdrawDetail"
    )
    margin_detail: Optional[MarginDetail] = Field(default=None, alias="marginDetail")
    bond_detail: Optional[BondDetail] = Field(default=None, alias="bondDetail")
    short_detail: Optional[ShortDetail] = Field(default=None, alias="shortDetail")
    options_detail: Optional[OptionsDetail] = Field(default=None, alias="optionsDetail")
    simplified_margin_detail: Optional[SimplifiedMarginDetail] = Field(
        default=None, alias="simplifiedMarginDetail"
    )


# ---------------------------------------------------------------------------
# Top-level per-account balance
# ---------------------------------------------------------------------------

class AccountBalance(BaseModel):
    model_config = {"populate_by_name": True}

    acct_num: str = Field(alias="acctNum")
    addl_info_detail: Optional[AddlInfoDetail] = Field(default=None, alias="addlInfoDetail")
    recent_balance_detail: Optional[BalanceTimingDetail] = Field(
        default=None, alias="recentBalanceDetail"
    )
    intraday_balance_detail: Optional[BalanceTimingDetail] = Field(
        default=None, alias="intradayBalanceDetail"
    )
    close_balance_detail: Optional[BalanceTimingDetail] = Field(
        default=None, alias="closeBalanceDetail"
    )

    @model_validator(mode="before")
    @classmethod
    def _unwrap_brokerage_detail(cls, data: Any) -> Any:
        """Hoist fields from brokerageAcctDetail up to the top level.

        The raw API response wraps per-account balance info inside
        ``brokerageAcctDetail``.  This validator flattens that nesting so the
        model fields can be populated directly.
        """
        if not isinstance(data, dict):
            return data
        brokerage = data.get("brokerageAcctDetail")
        if not brokerage:
            return data
        data = dict(data)
        # addlInfoDetail lives at the brokerage level
        if "addlInfoDetail" not in data and "addlInfoDetail" in brokerage:
            data["addlInfoDetail"] = brokerage["addlInfoDetail"]
        # timing snapshots live inside recentBalanceDetail / intradayBalanceDetail / closeBalanceDetail
        for key in ("recentBalanceDetail", "intradayBalanceDetail", "closeBalanceDetail"):
            if key not in data and key in brokerage:
                data[key] = brokerage[key]
        return data


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------

class BalancesResponse(BaseModel):
    model_config = {"populate_by_name": True}

    accounts: List[AccountBalance] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "BalancesResponse":
        """Parse the full API JSON response into a BalancesResponse.

        Expected shape::

            {
                "balances": [
                    {
                        "acctNum": "...",
                        "brokerageAcctDetail": { ... }
                    },
                    ...
                ]
            }
        """
        balances_list = data.get("balances") or []
        return cls(
            accounts=[AccountBalance.model_validate(item) for item in balances_list]
        )
