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

    @field_validator(
        "net_worth",
        "net_worth_chg",
        "net_worth_chg_pct",
        "market_val",
        "market_val_chg",
        "market_val_chg_pct",
        "acct_eqty_pct",
        "regulatory_net_worth",
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
    cash_cmtd_to_open_order: Optional[float] = Field(default=None, alias="cashCmtdToOpenOrder")

    @field_validator("cash", "cash_chg", "cash_cmtd_to_open_order", mode="before")
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
    has_unpriced_order: Optional[bool] = Field(default=None, alias="hasUnpricedOrder")
    has_margin_calls: Optional[bool] = Field(default=None, alias="hasMarginCalls")
    has_real_time_balances: Optional[bool] = Field(default=None, alias="hasRealTimeBalances")


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
