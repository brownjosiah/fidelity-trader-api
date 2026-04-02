from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator

from fidelity_trader.models._parsers import _parse_float


# ---------------------------------------------------------------------------
# Sub-models — leaf detail blocks
# ---------------------------------------------------------------------------

class TxnDateDetail(BaseModel):
    model_config = {"populate_by_name": True}

    traded_date: Optional[int] = Field(default=None, alias="tradedDate")
    posted_date: Optional[int] = Field(default=None, alias="postedDate")
    stlmnt_date: Optional[int] = Field(default=None, alias="stlmntDate")


class TxnOptionDetail(BaseModel):
    model_config = {"populate_by_name": True}

    contract_symbol: Optional[str] = Field(default=None, alias="contractSymbol")
    expire_date: Optional[str] = Field(default=None, alias="expireDate")
    strike_price: Optional[float] = Field(default=None, alias="strikePrice")
    type: Optional[str] = None

    @field_validator("strike_price", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class TxnSecurityDetail(BaseModel):
    model_config = {"populate_by_name": True}

    type_code: Optional[str] = Field(default=None, alias="typeCode")
    type_code_desc: Optional[str] = Field(default=None, alias="typeCodeDesc")
    symbol: Optional[str] = None
    desc: Optional[str] = None
    cusip: Optional[str] = None
    is_quotable: Optional[bool] = Field(default=None, alias="isQuotable")
    option_detail: Optional[TxnOptionDetail] = Field(default=None, alias="optionDetail")


class TxnAmountDetail(BaseModel):
    model_config = {"populate_by_name": True}

    price: Optional[float] = None
    commission: Optional[float] = None
    fees: Optional[float] = None
    interest: Optional[float] = None
    net: Optional[float] = None
    principal: Optional[float] = None

    @field_validator("price", "commission", "fees", "interest", "net", "principal", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class TxnBrokerageDetail(BaseModel):
    model_config = {"populate_by_name": True}

    trade_type_code: Optional[str] = Field(default=None, alias="tradeTypeCode")
    trade_type_code_desc: Optional[str] = Field(default=None, alias="tradeTypeCodeDesc")
    is_cancelled: Optional[bool] = Field(default=None, alias="isCancelled")


class TxnCategoryDetail(BaseModel):
    model_config = {"populate_by_name": True}

    txn_type_code: Optional[str] = Field(default=None, alias="txnTypeCode")
    txn_type_desc: Optional[str] = Field(default=None, alias="txnTypeDesc")
    txn_cat_code: Optional[str] = Field(default=None, alias="txnCatCode")
    txn_cat_desc: Optional[str] = Field(default=None, alias="txnCatDesc")
    txn_sub_cat_code: Optional[str] = Field(default=None, alias="txnSubCatCode")
    txn_sub_cat_desc: Optional[str] = Field(default=None, alias="txnSubCatDesc")


# ---------------------------------------------------------------------------
# Transaction — single transaction record
# ---------------------------------------------------------------------------

class Transaction(BaseModel):
    model_config = {"populate_by_name": True}

    desc: Optional[str] = None
    short_desc: Optional[str] = Field(default=None, alias="shortDesc")
    quantity: Optional[float] = None
    date_detail: Optional[TxnDateDetail] = Field(default=None, alias="dateDetail")
    security_detail: Optional[TxnSecurityDetail] = Field(default=None, alias="securityDetail")
    amt_detail: Optional[TxnAmountDetail] = Field(default=None, alias="amtDetail")
    brokerage_detail: Optional[TxnBrokerageDetail] = Field(default=None, alias="brokerageDetail")
    cat_detail: Optional[TxnCategoryDetail] = Field(default=None, alias="catDetail")

    @field_validator("quantity", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


# ---------------------------------------------------------------------------
# AccountTransactions — per-account wrapper
# ---------------------------------------------------------------------------

class AccountTransactions(BaseModel):
    model_config = {"populate_by_name": True}

    acct_num: str = Field(alias="acctNum")
    transactions: List[Transaction] = Field(default_factory=list)

    @classmethod
    def from_api_dict(cls, data: dict) -> "AccountTransactions":
        acct_num = data.get("acctNum", "")
        raw_txns = data.get("transactionDetails") or []
        transactions = [Transaction.model_validate(t) for t in raw_txns]
        return cls(acctNum=acct_num, transactions=transactions)


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------

class TransactionHistoryResponse(BaseModel):
    model_config = {"populate_by_name": True}

    as_of_date: Optional[int] = Field(default=None, alias="asOfDate")
    accounts: List[AccountTransactions] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "TransactionHistoryResponse":
        """Parse the full API JSON response into a TransactionHistoryResponse.

        Expected shape::

            {
                "asOfDate": 1774843200,
                "acctDetails": [
                    {
                        "acctNum": "...",
                        "transactionDetails": [ ... ]
                    },
                    ...
                ]
            }
        """
        as_of_date = data.get("asOfDate")
        acct_details = data.get("acctDetails") or []
        accounts = [AccountTransactions.from_api_dict(item) for item in acct_details]
        return cls(asOfDate=as_of_date, accounts=accounts)
