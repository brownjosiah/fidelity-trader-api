"""Tests for the loaned securities API."""

import json

import httpx
import pytest
import respx

from fidelity_trader.portfolio.loaned_securities import LoanedSecuritiesAPI
from fidelity_trader.models.loaned_securities import (
    LoanedSecuritiesResponse,
    AccountLoanedSecurities,
    ContractDataDetail,
    CollateralDetail,
)
from fidelity_trader._http import DPSERVICE_URL


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_contract(symbol="LGVN", rate="3.735", qty=5, **overrides):
    base = {
        "symbol": symbol,
        "cusip": "54303L203",
        "securityDescription": f"{symbol} INC",
        "rate": rate,
        "contractVal": "21",
        "contractQty": qty,
        "priorDayAccrual": "0.01",
        "monthToDateAccrual": "0.03",
    }
    base.update(overrides)
    return base


def _make_collateral(cusip="L0C990063", amount="10142"):
    return {"cusip": cusip, "cusipDesc": "Collateral Deliv to US Bank", "amount": amount}


def _make_account(acct_num="Z21772945", contracts=None, collaterals=None):
    return {
        "acctNum": acct_num,
        "priorDayAccruals": "10.95",
        "monthToDateAccruals": "1127.28",
        "priorMonthAccruals": "2.59",
        "contractDataDetails": {
            "contractDataDetail": contracts or [_make_contract()],
        },
        "collateralDetails": {
            "collateralDetail": collaterals or [_make_collateral()],
        },
    }


def _make_api_response(accounts=None):
    return {
        "loanedSecurities": {
            "acctDetails": {
                "acctDetail": accounts or [_make_account()],
            }
        }
    }


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestCollateralDetail:
    def test_parse(self):
        c = CollateralDetail.model_validate(_make_collateral())
        assert c.cusip == "L0C990063"
        assert c.cusip_desc == "Collateral Deliv to US Bank"
        assert c.amount == pytest.approx(10142.0)

    def test_amount_coerces_string(self):
        c = CollateralDetail.model_validate({"amount": "5000.50"})
        assert c.amount == pytest.approx(5000.50)

    def test_defaults(self):
        c = CollateralDetail.model_validate({})
        assert c.cusip is None
        assert c.amount is None


class TestContractDataDetail:
    def test_parse_full(self):
        c = ContractDataDetail.model_validate(_make_contract())
        assert c.symbol == "LGVN"
        assert c.rate == pytest.approx(3.735)
        assert c.contract_qty == pytest.approx(5.0)
        assert c.prior_day_accrual == pytest.approx(0.01)
        assert c.month_to_date_accrual == pytest.approx(0.03)

    def test_missing_optional_fields(self):
        c = ContractDataDetail.model_validate({
            "symbol": "MAIA",
            "cusip": "552641102",
            "securityDescription": "MAIA BIOTECHNOLOGY INC COM",
            "monthToDateAccrual": "0.08",
        })
        assert c.symbol == "MAIA"
        assert c.rate is None
        assert c.contract_val is None
        assert c.contract_qty is None
        assert c.month_to_date_accrual == pytest.approx(0.08)

    def test_rate_coerces_string(self):
        c = ContractDataDetail.model_validate({"rate": "46.639"})
        assert c.rate == pytest.approx(46.639)


class TestAccountLoanedSecurities:
    def test_parse_full(self):
        a = AccountLoanedSecurities.model_validate(_make_account())
        assert a.acct_num == "Z21772945"
        assert a.prior_day_accruals == pytest.approx(10.95)
        assert a.month_to_date_accruals == pytest.approx(1127.28)
        assert a.prior_month_accruals == pytest.approx(2.59)
        assert len(a.contract_data_details) == 1
        assert len(a.collateral_details) == 1

    def test_flattens_nested_contract_data(self):
        a = AccountLoanedSecurities.model_validate(_make_account(
            contracts=[_make_contract("PLUG"), _make_contract("HRZN")]
        ))
        assert len(a.contract_data_details) == 2
        assert a.contract_data_details[0].symbol == "PLUG"
        assert a.contract_data_details[1].symbol == "HRZN"

    def test_empty_contracts(self):
        data = _make_account()
        data["contractDataDetails"]["contractDataDetail"] = []
        a = AccountLoanedSecurities.model_validate(data)
        assert a.contract_data_details == []

    def test_missing_contract_data_details(self):
        data = {"acctNum": "Z12345", "priorDayAccruals": "0"}
        a = AccountLoanedSecurities.model_validate(data)
        assert a.contract_data_details == []
        assert a.collateral_details == []


class TestLoanedSecuritiesResponse:
    def test_from_api_response(self):
        resp = LoanedSecuritiesResponse.from_api_response(_make_api_response())
        assert len(resp.accounts) == 1
        assert resp.accounts[0].acct_num == "Z21772945"

    def test_multiple_accounts(self):
        resp = LoanedSecuritiesResponse.from_api_response(_make_api_response([
            _make_account("Z111"),
            _make_account("Z222"),
        ]))
        assert len(resp.accounts) == 2
        assert resp.accounts[0].acct_num == "Z111"
        assert resp.accounts[1].acct_num == "Z222"

    def test_empty_response(self):
        resp = LoanedSecuritiesResponse.from_api_response({})
        assert resp.accounts == []

    def test_nested_contract_accessible(self):
        resp = LoanedSecuritiesResponse.from_api_response(_make_api_response())
        assert resp.accounts[0].contract_data_details[0].symbol == "LGVN"

    def test_nested_collateral_accessible(self):
        resp = LoanedSecuritiesResponse.from_api_response(_make_api_response())
        assert resp.accounts[0].collateral_details[0].amount == pytest.approx(10142.0)


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

class TestLoanedSecuritiesAPI:
    @respx.mock
    def test_get_loaned_securities(self):
        route = respx.post(
            f"{DPSERVICE_URL}/ftgw/dp/retail-am-loanedsecurities/v1/accounts/positions/rates"
        ).mock(return_value=httpx.Response(200, json=_make_api_response()))

        api = LoanedSecuritiesAPI(httpx.Client())
        try:
            result = api.get_loaned_securities(["Z21772945"])
        finally:
            api._http.close()

        assert isinstance(result, LoanedSecuritiesResponse)
        assert len(result.accounts) == 1
        assert route.called

    @respx.mock
    def test_request_body_shape(self):
        route = respx.post(
            f"{DPSERVICE_URL}/ftgw/dp/retail-am-loanedsecurities/v1/accounts/positions/rates"
        ).mock(return_value=httpx.Response(200, json=_make_api_response()))

        api = LoanedSecuritiesAPI(httpx.Client())
        try:
            api.get_loaned_securities(["Z111", "Z222"])
        finally:
            api._http.close()

        body = json.loads(route.calls[0].request.content)
        accts = body["request"]["parameters"]["acctDetails"]
        assert len(accts) == 2
        assert accts[0] == {"acctNum": "Z111"}
        assert accts[1] == {"acctNum": "Z222"}

    @respx.mock
    def test_raises_on_http_error(self):
        respx.post(
            f"{DPSERVICE_URL}/ftgw/dp/retail-am-loanedsecurities/v1/accounts/positions/rates"
        ).mock(return_value=httpx.Response(500))

        api = LoanedSecuritiesAPI(httpx.Client())
        try:
            with pytest.raises(httpx.HTTPStatusError):
                api.get_loaned_securities(["Z111"])
        finally:
            api._http.close()
