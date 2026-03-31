"""Tests for the transaction history API models and TransactionsAPI client."""
import json

import httpx
import pytest
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.transaction import (
    TxnDateDetail,
    TxnOptionDetail,
    TxnSecurityDetail,
    TxnAmountDetail,
    TxnBrokerageDetail,
    TxnCategoryDetail,
    Transaction,
    AccountTransactions,
    TransactionHistoryResponse,
)
from fidelity_trader.portfolio.transactions import TransactionsAPI


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_OPTION_TXN = {
    "desc": "YOU SOLD CLOSING TRANSACTION CALL (SPXW) NEW S & P 500 INDEX MAR 30 26 $6420 (100 SHS) (Margin)",
    "shortDesc": "YOU SOLD CLOSING TRANSACTION",
    "quantity": -1.0,
    "dateDetail": {
        "stlmntDate": 1774929600,
        "tradedDate": 1774843200,
        "postedDate": 1774843200,
    },
    "securityDetail": {
        "typeCode": "O",
        "typeCodeDesc": "Option",
        "symbol": "SPXW260330C6420",
        "desc": "CALL (SPXW) NEW S & P 500 INDEX MAR 30 26 $6420 (100 SHS)",
        "cusip": "8548449BT",
        "isQuotable": True,
        "optionDetail": {
            "contractSymbol": "SPXW",
            "expireDate": "2026-03-30",
            "strikePrice": 6420.0,
            "type": "C",
        },
    },
    "amtDetail": {
        "price": 0.12,
        "commission": 0.60,
        "fees": 0.02,
        "interest": 0.0,
        "net": 11.38,
        "principal": 12.0,
    },
    "brokerageDetail": {
        "tradeTypeCode": "2",
        "tradeTypeCodeDesc": "Margin",
        "isCancelled": False,
    },
    "catDetail": {
        "txnTypeCode": "ST",
        "txnTypeDesc": "Security Transaction or Trade",
        "txnCatCode": "IA",
        "txnCatDesc": "Investment Activity",
        "txnSubCatCode": "SL",
        "txnSubCatDesc": "Sell",
    },
}

_CASH_TXN = {
    "desc": "DIRECT DEPOSIT UNITED AIRLIDIR DEP (Cash)",
    "shortDesc": "DIRECT DEPOSIT UNITED AIRLIDIR DEP",
    "quantity": 0.0,
    "dateDetail": {"tradedDate": 1774843200, "postedDate": 1774843200},
    "securityDetail": {"desc": "", "isQuotable": False},
    "amtDetail": {
        "price": 0.0,
        "commission": 0.0,
        "fees": 0.0,
        "interest": 0.0,
        "net": 4600.25,
        "principal": 0.0,
    },
    "catDetail": {
        "txnTypeCode": "CT",
        "txnTypeDesc": "Cash Transaction",
        "txnCatCode": "DD",
        "txnCatDesc": "Direct Deposit",
    },
}


def _make_api_response(acct_num: str = "Z21772945", transactions: list = None) -> dict:
    if transactions is None:
        transactions = [_OPTION_TXN, _CASH_TXN]
    return {
        "asOfDate": 1774843200,
        "acctDetails": [
            {
                "acctNum": acct_num,
                "transactionDetails": transactions,
            }
        ],
    }


# ---------------------------------------------------------------------------
# TxnDateDetail
# ---------------------------------------------------------------------------

class TestTxnDateDetail:
    def test_parses_all_fields(self):
        d = TxnDateDetail.model_validate(
            {"stlmntDate": 1774929600, "tradedDate": 1774843200, "postedDate": 1774843200}
        )
        assert d.stlmnt_date == 1774929600
        assert d.traded_date == 1774843200
        assert d.posted_date == 1774843200

    def test_optional_fields_default_none(self):
        d = TxnDateDetail.model_validate({})
        assert d.traded_date is None
        assert d.posted_date is None
        assert d.stlmnt_date is None

    def test_missing_stlmnt_date(self):
        d = TxnDateDetail.model_validate({"tradedDate": 1774843200, "postedDate": 1774843200})
        assert d.stlmnt_date is None
        assert d.traded_date == 1774843200


# ---------------------------------------------------------------------------
# TxnOptionDetail
# ---------------------------------------------------------------------------

class TestTxnOptionDetail:
    def test_parses_all_fields(self):
        od = TxnOptionDetail.model_validate(
            {"contractSymbol": "SPXW", "expireDate": "2026-03-30", "strikePrice": 6420.0, "type": "C"}
        )
        assert od.contract_symbol == "SPXW"
        assert od.expire_date == "2026-03-30"
        assert od.strike_price == pytest.approx(6420.0)
        assert od.type == "C"

    def test_optional_fields_default_none(self):
        od = TxnOptionDetail.model_validate({})
        assert od.contract_symbol is None
        assert od.expire_date is None
        assert od.strike_price is None
        assert od.type is None

    def test_coerces_string_strike_price(self):
        od = TxnOptionDetail.model_validate({"strikePrice": "6420.0"})
        assert od.strike_price == pytest.approx(6420.0)

    def test_put_type(self):
        od = TxnOptionDetail.model_validate({"type": "P", "strikePrice": 5000.0})
        assert od.type == "P"
        assert od.strike_price == pytest.approx(5000.0)


# ---------------------------------------------------------------------------
# TxnSecurityDetail
# ---------------------------------------------------------------------------

class TestTxnSecurityDetail:
    def test_parses_option_security(self):
        sd = TxnSecurityDetail.model_validate(_OPTION_TXN["securityDetail"])
        assert sd.type_code == "O"
        assert sd.type_code_desc == "Option"
        assert sd.symbol == "SPXW260330C6420"
        assert sd.cusip == "8548449BT"
        assert sd.is_quotable is True
        assert sd.option_detail is not None
        assert sd.option_detail.contract_symbol == "SPXW"
        assert sd.option_detail.strike_price == pytest.approx(6420.0)

    def test_parses_cash_security(self):
        sd = TxnSecurityDetail.model_validate(_CASH_TXN["securityDetail"])
        assert sd.symbol is None
        assert sd.is_quotable is False
        assert sd.option_detail is None

    def test_optional_fields_default_none(self):
        sd = TxnSecurityDetail.model_validate({})
        assert sd.type_code is None
        assert sd.symbol is None
        assert sd.option_detail is None


# ---------------------------------------------------------------------------
# TxnAmountDetail
# ---------------------------------------------------------------------------

class TestTxnAmountDetail:
    def test_parses_option_amounts(self):
        ad = TxnAmountDetail.model_validate(_OPTION_TXN["amtDetail"])
        assert ad.price == pytest.approx(0.12)
        assert ad.commission == pytest.approx(0.60)
        assert ad.fees == pytest.approx(0.02)
        assert ad.interest == pytest.approx(0.0)
        assert ad.net == pytest.approx(11.38)
        assert ad.principal == pytest.approx(12.0)

    def test_parses_cash_amounts(self):
        ad = TxnAmountDetail.model_validate(_CASH_TXN["amtDetail"])
        assert ad.net == pytest.approx(4600.25)
        assert ad.price == pytest.approx(0.0)

    def test_optional_fields_default_none(self):
        ad = TxnAmountDetail.model_validate({})
        assert ad.price is None
        assert ad.net is None

    def test_coerces_string_floats(self):
        ad = TxnAmountDetail.model_validate({"net": "4600.25", "price": "0.12"})
        assert ad.net == pytest.approx(4600.25)
        assert ad.price == pytest.approx(0.12)

    def test_negative_net(self):
        ad = TxnAmountDetail.model_validate({"net": -500.0})
        assert ad.net == pytest.approx(-500.0)


# ---------------------------------------------------------------------------
# TxnBrokerageDetail
# ---------------------------------------------------------------------------

class TestTxnBrokerageDetail:
    def test_parses_all_fields(self):
        bd = TxnBrokerageDetail.model_validate(
            {"tradeTypeCode": "2", "tradeTypeCodeDesc": "Margin", "isCancelled": False}
        )
        assert bd.trade_type_code == "2"
        assert bd.trade_type_code_desc == "Margin"
        assert bd.is_cancelled is False

    def test_cancelled_transaction(self):
        bd = TxnBrokerageDetail.model_validate({"isCancelled": True})
        assert bd.is_cancelled is True

    def test_optional_fields_default_none(self):
        bd = TxnBrokerageDetail.model_validate({})
        assert bd.trade_type_code is None
        assert bd.is_cancelled is None


# ---------------------------------------------------------------------------
# TxnCategoryDetail
# ---------------------------------------------------------------------------

class TestTxnCategoryDetail:
    def test_parses_security_transaction(self):
        cd = TxnCategoryDetail.model_validate(_OPTION_TXN["catDetail"])
        assert cd.txn_type_code == "ST"
        assert cd.txn_type_desc == "Security Transaction or Trade"
        assert cd.txn_cat_code == "IA"
        assert cd.txn_cat_desc == "Investment Activity"
        assert cd.txn_sub_cat_code == "SL"
        assert cd.txn_sub_cat_desc == "Sell"

    def test_parses_cash_transaction(self):
        cd = TxnCategoryDetail.model_validate(_CASH_TXN["catDetail"])
        assert cd.txn_type_code == "CT"
        assert cd.txn_cat_code == "DD"
        assert cd.txn_cat_desc == "Direct Deposit"
        assert cd.txn_sub_cat_code is None

    def test_optional_fields_default_none(self):
        cd = TxnCategoryDetail.model_validate({})
        assert cd.txn_type_code is None
        assert cd.txn_cat_code is None


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

class TestTransaction:
    def test_parses_option_transaction(self):
        t = Transaction.model_validate(_OPTION_TXN)
        assert t.desc.startswith("YOU SOLD CLOSING TRANSACTION")
        assert t.short_desc == "YOU SOLD CLOSING TRANSACTION"
        assert t.quantity == pytest.approx(-1.0)
        assert t.date_detail is not None
        assert t.date_detail.traded_date == 1774843200
        assert t.date_detail.stlmnt_date == 1774929600
        assert t.security_detail is not None
        assert t.security_detail.symbol == "SPXW260330C6420"
        assert t.security_detail.option_detail.strike_price == pytest.approx(6420.0)
        assert t.amt_detail is not None
        assert t.amt_detail.net == pytest.approx(11.38)
        assert t.brokerage_detail is not None
        assert t.brokerage_detail.trade_type_code_desc == "Margin"
        assert t.cat_detail is not None
        assert t.cat_detail.txn_sub_cat_code == "SL"

    def test_parses_cash_transaction(self):
        t = Transaction.model_validate(_CASH_TXN)
        assert t.quantity == pytest.approx(0.0)
        assert t.security_detail is not None
        assert t.security_detail.option_detail is None
        assert t.brokerage_detail is None
        assert t.amt_detail.net == pytest.approx(4600.25)
        assert t.cat_detail.txn_type_code == "CT"

    def test_optional_fields_default_none(self):
        t = Transaction.model_validate({})
        assert t.desc is None
        assert t.quantity is None
        assert t.date_detail is None
        assert t.security_detail is None
        assert t.amt_detail is None
        assert t.brokerage_detail is None
        assert t.cat_detail is None

    def test_coerces_quantity_string(self):
        t = Transaction.model_validate({"quantity": "-1.0"})
        assert t.quantity == pytest.approx(-1.0)


# ---------------------------------------------------------------------------
# AccountTransactions
# ---------------------------------------------------------------------------

class TestAccountTransactions:
    def test_from_api_dict_with_transactions(self):
        raw = {
            "acctNum": "Z21772945",
            "transactionDetails": [_OPTION_TXN, _CASH_TXN],
        }
        at = AccountTransactions.from_api_dict(raw)
        assert at.acct_num == "Z21772945"
        assert len(at.transactions) == 2

    def test_from_api_dict_empty_transactions(self):
        raw = {"acctNum": "Z21772945", "transactionDetails": []}
        at = AccountTransactions.from_api_dict(raw)
        assert at.acct_num == "Z21772945"
        assert at.transactions == []

    def test_from_api_dict_missing_transactions_key(self):
        raw = {"acctNum": "Z21772945"}
        at = AccountTransactions.from_api_dict(raw)
        assert at.transactions == []

    def test_transaction_types_preserved(self):
        raw = {
            "acctNum": "Z21772945",
            "transactionDetails": [_OPTION_TXN, _CASH_TXN],
        }
        at = AccountTransactions.from_api_dict(raw)
        assert at.transactions[0].cat_detail.txn_type_code == "ST"
        assert at.transactions[1].cat_detail.txn_type_code == "CT"


# ---------------------------------------------------------------------------
# TransactionHistoryResponse
# ---------------------------------------------------------------------------

class TestTransactionHistoryResponse:
    def test_parses_full_response(self):
        raw = _make_api_response()
        resp = TransactionHistoryResponse.from_api_response(raw)
        assert resp.as_of_date == 1774843200
        assert len(resp.accounts) == 1
        assert resp.accounts[0].acct_num == "Z21772945"
        assert len(resp.accounts[0].transactions) == 2

    def test_option_transaction_details(self):
        raw = _make_api_response()
        resp = TransactionHistoryResponse.from_api_response(raw)
        opt_txn = resp.accounts[0].transactions[0]
        assert opt_txn.security_detail.symbol == "SPXW260330C6420"
        assert opt_txn.security_detail.option_detail.contract_symbol == "SPXW"
        assert opt_txn.security_detail.option_detail.expire_date == "2026-03-30"
        assert opt_txn.security_detail.option_detail.strike_price == pytest.approx(6420.0)
        assert opt_txn.amt_detail.net == pytest.approx(11.38)

    def test_cash_transaction_details(self):
        raw = _make_api_response()
        resp = TransactionHistoryResponse.from_api_response(raw)
        cash_txn = resp.accounts[0].transactions[1]
        assert cash_txn.cat_detail.txn_cat_code == "DD"
        assert cash_txn.amt_detail.net == pytest.approx(4600.25)
        assert cash_txn.security_detail.option_detail is None

    def test_empty_response(self):
        resp = TransactionHistoryResponse.from_api_response({})
        assert resp.as_of_date is None
        assert resp.accounts == []

    def test_empty_acct_details(self):
        resp = TransactionHistoryResponse.from_api_response({"asOfDate": 1774843200, "acctDetails": []})
        assert resp.as_of_date == 1774843200
        assert resp.accounts == []

    def test_multiple_accounts(self):
        raw = {
            "asOfDate": 1774843200,
            "acctDetails": [
                {"acctNum": "ACC001", "transactionDetails": [_OPTION_TXN]},
                {"acctNum": "ACC002", "transactionDetails": [_CASH_TXN]},
            ],
        }
        resp = TransactionHistoryResponse.from_api_response(raw)
        assert len(resp.accounts) == 2
        assert resp.accounts[0].acct_num == "ACC001"
        assert resp.accounts[1].acct_num == "ACC002"
        assert len(resp.accounts[0].transactions) == 1
        assert len(resp.accounts[1].transactions) == 1


# ---------------------------------------------------------------------------
# TransactionsAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

_TXN_URL = f"{DPSERVICE_URL}/ftgw/dp/accountmanagement/transaction/history/v2"


class TestTransactionsAPI:
    @respx.mock
    def test_get_transaction_history_makes_correct_request(self):
        raw = _make_api_response()
        route = respx.post(_TXN_URL).mock(return_value=httpx.Response(200, json=raw))
        client = httpx.Client()
        api = TransactionsAPI(client)
        result = api.get_transaction_history(["Z21772945"], 1769666400, 1774846800)

        assert route.called
        assert isinstance(result, TransactionHistoryResponse)
        assert len(result.accounts) == 1
        assert result.accounts[0].acct_num == "Z21772945"

    @respx.mock
    def test_get_transaction_history_request_body_shape(self):
        raw = _make_api_response()
        route = respx.post(_TXN_URL).mock(return_value=httpx.Response(200, json=raw))
        client = httpx.Client()
        api = TransactionsAPI(client)
        api.get_transaction_history(["Z21772945"], 1769666400, 1774846800)

        sent_body = json.loads(route.calls[0].request.content)

        # acctDetails
        acct_details = sent_body["acctDetails"]
        assert len(acct_details) == 1
        assert acct_details[0]["acctNum"] == "Z21772945"
        assert acct_details[0]["acctType"] == "brokerage"
        assert acct_details[0]["sysOfRcd"] is None

        # searchCriteriaDetail
        search = sent_body["searchCriteriaDetail"]
        assert search["txnFromDate"] == 1769666400
        assert search["txnToDate"] == 1774846800
        assert search["txnType"] is None
        assert search["txnCat"] is None

        # filterCriteriaDetail
        filters = search["filterCriteriaDetail"]
        assert filters["hasCoreStlmnt"] is False
        assert filters["hasFrgnTxn"] is False
        assert filters["hasPortfolioRetirementIncDetail"] is True
        assert filters["hasOnlyPortfolioRetirementIncDetail"] is True
        assert filters["hasAcctRetirementIncDetail"] is True
        assert filters["hasOnlyAcctRetirementIncDetail"] is True
        assert filters["hasIntradayTxn"] is False
        assert filters["hasJournaledTxn"] is False
        assert filters["hasOnlyContributionTxn"] is True
        assert filters["hasBasketName"] is True

    @respx.mock
    def test_get_transaction_history_default_account_type_is_brokerage(self):
        raw = _make_api_response()
        route = respx.post(_TXN_URL).mock(return_value=httpx.Response(200, json=raw))
        client = httpx.Client()
        api = TransactionsAPI(client)
        api.get_transaction_history(["Z21772945"], 1769666400, 1774846800)

        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["acctDetails"][0]["acctType"] == "brokerage"

    @respx.mock
    def test_get_transaction_history_custom_account_types(self):
        raw = _make_api_response("IRA999")
        route = respx.post(_TXN_URL).mock(return_value=httpx.Response(200, json=raw))
        custom_types = [{"acctType": "IRA", "acctNum": "IRA999", "sysOfRcd": None}]
        client = httpx.Client()
        api = TransactionsAPI(client)
        api.get_transaction_history(["IRA999"], 1769666400, 1774846800, account_types=custom_types)

        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["acctDetails"][0]["acctType"] == "IRA"
        assert sent_body["acctDetails"][0]["acctNum"] == "IRA999"

    @respx.mock
    def test_get_transaction_history_multiple_accounts(self):
        raw = {
            "asOfDate": 1774843200,
            "acctDetails": [
                {"acctNum": "ACC001", "transactionDetails": [_OPTION_TXN]},
                {"acctNum": "ACC002", "transactionDetails": [_CASH_TXN]},
            ],
        }
        route = respx.post(_TXN_URL).mock(return_value=httpx.Response(200, json=raw))
        client = httpx.Client()
        api = TransactionsAPI(client)
        result = api.get_transaction_history(["ACC001", "ACC002"], 1769666400, 1774846800)

        sent_body = json.loads(route.calls[0].request.content)
        assert len(sent_body["acctDetails"]) == 2
        assert sent_body["acctDetails"][0]["acctNum"] == "ACC001"
        assert sent_body["acctDetails"][1]["acctNum"] == "ACC002"
        assert len(result.accounts) == 2

    @respx.mock
    def test_get_transaction_history_raises_on_http_error(self):
        respx.post(_TXN_URL).mock(return_value=httpx.Response(401))
        client = httpx.Client()
        api = TransactionsAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_transaction_history(["Z21772945"], 1769666400, 1774846800)

    @respx.mock
    def test_get_transaction_history_returns_response_type(self):
        raw = _make_api_response()
        respx.post(_TXN_URL).mock(return_value=httpx.Response(200, json=raw))
        client = httpx.Client()
        api = TransactionsAPI(client)
        result = api.get_transaction_history(["Z21772945"], 1769666400, 1774846800)
        assert isinstance(result, TransactionHistoryResponse)

    @respx.mock
    def test_get_transaction_history_date_range_in_body(self):
        raw = _make_api_response()
        route = respx.post(_TXN_URL).mock(return_value=httpx.Response(200, json=raw))
        client = httpx.Client()
        api = TransactionsAPI(client)
        api.get_transaction_history(["Z21772945"], from_date=1769666400, to_date=1774846800)

        sent_body = json.loads(route.calls[0].request.content)
        search = sent_body["searchCriteriaDetail"]
        assert search["txnFromDate"] == 1769666400
        assert search["txnToDate"] == 1774846800
