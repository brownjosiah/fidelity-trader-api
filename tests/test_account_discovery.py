"""Tests for account discovery v2 API models and AccountsAPI client."""
import json

import httpx
import pytest
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.account_detail import (
    PreferenceDetail,
    TradeAttrDetail,
    LegalAttrDetail,
    WorkplacePlanDetail,
    AccountDetail,
    AccountsResponse,
)
from fidelity_trader.portfolio.accounts import AccountsAPI


# ---------------------------------------------------------------------------
# Fixtures / sample data mirroring captured traffic
# ---------------------------------------------------------------------------

WORKPLACE_ACCT = {
    "acctNum": "90295",
    "acctType": "WPS",
    "acctSubType": "Defined Contributions",
    "workplacePlanDetail": {
        "marketValue": "133784.61",
        "planTypeName": "401K",
        "clientId": "000056732",
        "vestedAcctValEOD": "133784.61",
        "planType": "401(k)",
        "isVested100Pct": True,
    },
    "preferenceDetail": {
        "name": "UNITED AIRLINES 401(K) SAVINGS PLAN",
        "isHidden": False,
        "acctGroupId": "RA",
        "isDefaultAcct": False,
    },
}

CASH_MGMT_ACCT = {
    "acctNum": "Z33359950",
    "acctType": "Brokerage",
    "acctSubType": "Cash Management",
    "acctSubTypeDesc": "Brokerage Cash Management",
    "acctLegalAttrDetail": {
        "legalConstructCode": "INDIVIDUAL",
        "offeringCode": "CASHMGMTACCT",
        "lineOfBusinessCode": "PI",
    },
    "acctTradeAttrDetail": {
        "optionLevel": 0,
        "mrgnEstb": False,
        "optionEstb": False,
    },
    "preferenceDetail": {
        "name": "Cash Management",
        "isHidden": False,
        "isDefaultAcct": False,
    },
}

INDIVIDUAL_BROKERAGE_ACCT = {
    "acctNum": "Z25485019",
    "acctType": "Brokerage",
    "acctSubType": "Brokerage",
    "acctSubTypeDesc": "Individual Brokerage",
    "acctTradeAttrDetail": {
        "optionLevel": 4,
        "mrgnEstb": False,
        "optionEstb": True,
    },
    "preferenceDetail": {
        "name": "Individual",
        "isHidden": False,
    },
}

MARGIN_BROKERAGE_ACCT = {
    "acctNum": "Z21772945",
    "acctType": "Brokerage",
    "acctSubType": "Brokerage",
    "acctSubTypeDesc": "Margin Brokerage",
    "acctTradeAttrDetail": {
        "optionLevel": 5,
        "mrgnEstb": True,
        "optionEstb": True,
    },
    "preferenceDetail": {
        "name": "Margin Trading",
        "isHidden": False,
    },
}

FULL_CAPTURED_RESPONSE = {
    "acctDetails": [
        WORKPLACE_ACCT,
        CASH_MGMT_ACCT,
        INDIVIDUAL_BROKERAGE_ACCT,
        MARGIN_BROKERAGE_ACCT,
    ]
}


# ---------------------------------------------------------------------------
# PreferenceDetail
# ---------------------------------------------------------------------------

class TestPreferenceDetail:
    def test_parses_all_fields(self):
        pd = PreferenceDetail.model_validate({
            "name": "UNITED AIRLINES 401(K) SAVINGS PLAN",
            "isHidden": False,
            "acctGroupId": "RA",
            "isDefaultAcct": False,
        })
        assert pd.name == "UNITED AIRLINES 401(K) SAVINGS PLAN"
        assert pd.is_hidden is False
        assert pd.acct_group_id == "RA"
        assert pd.is_default_acct is False

    def test_optional_fields_default_none(self):
        pd = PreferenceDetail.model_validate({})
        assert pd.name is None
        assert pd.is_hidden is None
        assert pd.acct_group_id is None
        assert pd.is_default_acct is None

    def test_missing_optional_acct_group_id(self):
        pd = PreferenceDetail.model_validate({"name": "Individual", "isHidden": False})
        assert pd.name == "Individual"
        assert pd.acct_group_id is None

    def test_is_hidden_true(self):
        pd = PreferenceDetail.model_validate({"isHidden": True})
        assert pd.is_hidden is True

    def test_is_default_acct_true(self):
        pd = PreferenceDetail.model_validate({"isDefaultAcct": True})
        assert pd.is_default_acct is True


# ---------------------------------------------------------------------------
# TradeAttrDetail
# ---------------------------------------------------------------------------

class TestTradeAttrDetail:
    def test_parses_all_fields(self):
        tad = TradeAttrDetail.model_validate({
            "optionLevel": 4,
            "mrgnEstb": False,
            "optionEstb": True,
        })
        assert tad.option_level == 4
        assert tad.mrgn_estb is False
        assert tad.option_estb is True

    def test_optional_fields_default_none(self):
        tad = TradeAttrDetail.model_validate({})
        assert tad.option_level is None
        assert tad.mrgn_estb is None
        assert tad.option_estb is None

    def test_margin_enabled(self):
        tad = TradeAttrDetail.model_validate({"optionLevel": 5, "mrgnEstb": True, "optionEstb": True})
        assert tad.mrgn_estb is True
        assert tad.option_level == 5

    def test_zero_option_level(self):
        tad = TradeAttrDetail.model_validate({"optionLevel": 0, "mrgnEstb": False, "optionEstb": False})
        assert tad.option_level == 0
        assert tad.mrgn_estb is False
        assert tad.option_estb is False


# ---------------------------------------------------------------------------
# LegalAttrDetail
# ---------------------------------------------------------------------------

class TestLegalAttrDetail:
    def test_parses_all_fields(self):
        lad = LegalAttrDetail.model_validate({
            "legalConstructCode": "INDIVIDUAL",
            "offeringCode": "CASHMGMTACCT",
            "lineOfBusinessCode": "PI",
        })
        assert lad.legal_construct_code == "INDIVIDUAL"
        assert lad.offering_code == "CASHMGMTACCT"
        assert lad.line_of_business_code == "PI"

    def test_optional_fields_default_none(self):
        lad = LegalAttrDetail.model_validate({})
        assert lad.legal_construct_code is None
        assert lad.offering_code is None
        assert lad.line_of_business_code is None

    def test_partial_fields(self):
        lad = LegalAttrDetail.model_validate({"legalConstructCode": "JOINT"})
        assert lad.legal_construct_code == "JOINT"
        assert lad.offering_code is None


# ---------------------------------------------------------------------------
# WorkplacePlanDetail
# ---------------------------------------------------------------------------

class TestWorkplacePlanDetail:
    def test_parses_all_fields(self):
        wpd = WorkplacePlanDetail.model_validate({
            "marketValue": "133784.61",
            "planTypeName": "401K",
            "clientId": "000056732",
            "vestedAcctValEOD": "133784.61",
            "planType": "401(k)",
            "isVested100Pct": True,
        })
        assert wpd.market_value == pytest.approx(133784.61)
        assert wpd.plan_type_name == "401K"
        assert wpd.client_id == "000056732"
        assert wpd.vested_acct_val_eod == pytest.approx(133784.61)
        assert wpd.plan_type == "401(k)"
        assert wpd.is_vested_100_pct is True

    def test_optional_fields_default_none(self):
        wpd = WorkplacePlanDetail.model_validate({})
        assert wpd.market_value is None
        assert wpd.plan_type_name is None
        assert wpd.client_id is None
        assert wpd.vested_acct_val_eod is None
        assert wpd.plan_type is None
        assert wpd.is_vested_100_pct is None

    def test_coerces_string_market_value(self):
        wpd = WorkplacePlanDetail.model_validate({"marketValue": "50000.00"})
        assert wpd.market_value == pytest.approx(50000.0)

    def test_numeric_market_value(self):
        wpd = WorkplacePlanDetail.model_validate({"marketValue": 75000.0})
        assert wpd.market_value == pytest.approx(75000.0)

    def test_is_vested_false(self):
        wpd = WorkplacePlanDetail.model_validate({"isVested100Pct": False})
        assert wpd.is_vested_100_pct is False


# ---------------------------------------------------------------------------
# AccountDetail
# ---------------------------------------------------------------------------

class TestAccountDetail:
    def test_parses_workplace_account(self):
        acct = AccountDetail.model_validate(WORKPLACE_ACCT)
        assert acct.acct_num == "90295"
        assert acct.acct_type == "WPS"
        assert acct.acct_sub_type == "Defined Contributions"
        assert acct.acct_sub_type_desc is None
        assert acct.workplace_plan_detail is not None
        assert acct.workplace_plan_detail.plan_type == "401(k)"
        assert acct.workplace_plan_detail.market_value == pytest.approx(133784.61)
        assert acct.preference_detail is not None
        assert acct.preference_detail.name == "UNITED AIRLINES 401(K) SAVINGS PLAN"
        assert acct.acct_trade_attr_detail is None
        assert acct.acct_legal_attr_detail is None

    def test_parses_cash_management_account(self):
        acct = AccountDetail.model_validate(CASH_MGMT_ACCT)
        assert acct.acct_num == "Z33359950"
        assert acct.acct_type == "Brokerage"
        assert acct.acct_sub_type == "Cash Management"
        assert acct.acct_sub_type_desc == "Brokerage Cash Management"
        assert acct.acct_legal_attr_detail is not None
        assert acct.acct_legal_attr_detail.legal_construct_code == "INDIVIDUAL"
        assert acct.acct_legal_attr_detail.offering_code == "CASHMGMTACCT"
        assert acct.acct_trade_attr_detail is not None
        assert acct.acct_trade_attr_detail.option_level == 0
        assert acct.workplace_plan_detail is None

    def test_parses_individual_brokerage_account(self):
        acct = AccountDetail.model_validate(INDIVIDUAL_BROKERAGE_ACCT)
        assert acct.acct_num == "Z25485019"
        assert acct.acct_type == "Brokerage"
        assert acct.acct_sub_type_desc == "Individual Brokerage"
        assert acct.acct_trade_attr_detail is not None
        assert acct.acct_trade_attr_detail.option_level == 4
        assert acct.acct_trade_attr_detail.mrgn_estb is False
        assert acct.acct_trade_attr_detail.option_estb is True
        assert acct.acct_legal_attr_detail is None
        assert acct.workplace_plan_detail is None

    def test_parses_margin_brokerage_account(self):
        acct = AccountDetail.model_validate(MARGIN_BROKERAGE_ACCT)
        assert acct.acct_num == "Z21772945"
        assert acct.acct_sub_type_desc == "Margin Brokerage"
        assert acct.acct_trade_attr_detail.option_level == 5
        assert acct.acct_trade_attr_detail.mrgn_estb is True
        assert acct.acct_trade_attr_detail.option_estb is True

    def test_all_optional_fields_absent(self):
        acct = AccountDetail.model_validate({"acctNum": "X12345", "acctType": "Brokerage"})
        assert acct.acct_num == "X12345"
        assert acct.acct_type == "Brokerage"
        assert acct.acct_sub_type is None
        assert acct.acct_sub_type_desc is None
        assert acct.preference_detail is None
        assert acct.acct_trade_attr_detail is None
        assert acct.acct_legal_attr_detail is None
        assert acct.workplace_plan_detail is None

    def test_empty_dict(self):
        acct = AccountDetail.model_validate({})
        assert acct.acct_num is None
        assert acct.acct_type is None


# ---------------------------------------------------------------------------
# AccountsResponse
# ---------------------------------------------------------------------------

class TestAccountsResponse:
    def test_parses_full_captured_response(self):
        resp = AccountsResponse.from_api_response(FULL_CAPTURED_RESPONSE)
        assert len(resp.accounts) == 4

    def test_first_account_is_workplace(self):
        resp = AccountsResponse.from_api_response(FULL_CAPTURED_RESPONSE)
        acct = resp.accounts[0]
        assert acct.acct_num == "90295"
        assert acct.acct_type == "WPS"

    def test_second_account_is_cash_management(self):
        resp = AccountsResponse.from_api_response(FULL_CAPTURED_RESPONSE)
        acct = resp.accounts[1]
        assert acct.acct_num == "Z33359950"
        assert acct.acct_sub_type == "Cash Management"

    def test_third_account_is_individual_brokerage(self):
        resp = AccountsResponse.from_api_response(FULL_CAPTURED_RESPONSE)
        acct = resp.accounts[2]
        assert acct.acct_num == "Z25485019"
        assert acct.acct_sub_type_desc == "Individual Brokerage"

    def test_fourth_account_is_margin_brokerage(self):
        resp = AccountsResponse.from_api_response(FULL_CAPTURED_RESPONSE)
        acct = resp.accounts[3]
        assert acct.acct_num == "Z21772945"
        assert acct.acct_trade_attr_detail.mrgn_estb is True

    def test_empty_response_body(self):
        resp = AccountsResponse.from_api_response({})
        assert resp.accounts == []

    def test_empty_acct_details_list(self):
        resp = AccountsResponse.from_api_response({"acctDetails": []})
        assert resp.accounts == []

    def test_workplace_plan_detail_values(self):
        resp = AccountsResponse.from_api_response(FULL_CAPTURED_RESPONSE)
        wpd = resp.accounts[0].workplace_plan_detail
        assert wpd is not None
        assert wpd.market_value == pytest.approx(133784.61)
        assert wpd.plan_type_name == "401K"
        assert wpd.is_vested_100_pct is True

    def test_accounts_response_type(self):
        resp = AccountsResponse.from_api_response(FULL_CAPTURED_RESPONSE)
        assert isinstance(resp, AccountsResponse)
        for acct in resp.accounts:
            assert isinstance(acct, AccountDetail)


# ---------------------------------------------------------------------------
# AccountsAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

DISCOVER_URL = f"{DPSERVICE_URL}/ftgw/dp/customer-am-acctnxt/v2/accounts"
FEATURES_URL = f"{DPSERVICE_URL}/ftgw/dp/customer-am-feature/v2/accounts/features/get"


class TestAccountsAPI:
    @respx.mock
    def test_discover_accounts_makes_correct_request(self):
        route = respx.post(DISCOVER_URL).mock(
            return_value=httpx.Response(200, json=FULL_CAPTURED_RESPONSE)
        )
        client = httpx.Client()
        api = AccountsAPI(client)
        result = api.discover_accounts()

        assert route.called
        assert isinstance(result, AccountsResponse)
        assert len(result.accounts) == 4

    @respx.mock
    def test_discover_accounts_request_body_shape(self):
        route = respx.post(DISCOVER_URL).mock(
            return_value=httpx.Response(200, json=FULL_CAPTURED_RESPONSE)
        )
        client = httpx.Client()
        api = AccountsAPI(client)
        api.discover_accounts()

        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["acctCategory"] == "Brokerage,WorkplaceContributions"
        filters = sent_body["filters"]
        assert filters["returnPreferenceDetail"] is True
        assert filters["returnAcctTradeAttrDetail"] is True
        assert filters["returnAcctTypesIndDetail"] is True
        assert filters["returnAcctLegalAttrDetail"] is True
        assert filters["returnWorkplacePlanDetail"] is True
        assert filters["returnGroupDetail"] is True

    @respx.mock
    def test_discover_accounts_custom_categories(self):
        route = respx.post(DISCOVER_URL).mock(
            return_value=httpx.Response(200, json={"acctDetails": []})
        )
        client = httpx.Client()
        api = AccountsAPI(client)
        api.discover_accounts(categories="Brokerage")

        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["acctCategory"] == "Brokerage"

    @respx.mock
    def test_discover_accounts_returns_accounts_response_type(self):
        respx.post(DISCOVER_URL).mock(
            return_value=httpx.Response(200, json=FULL_CAPTURED_RESPONSE)
        )
        client = httpx.Client()
        api = AccountsAPI(client)
        result = api.discover_accounts()
        assert isinstance(result, AccountsResponse)

    @respx.mock
    def test_discover_accounts_raises_on_http_error(self):
        respx.post(DISCOVER_URL).mock(return_value=httpx.Response(401))
        client = httpx.Client()
        api = AccountsAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.discover_accounts()

    @respx.mock
    def test_discover_accounts_empty_response(self):
        respx.post(DISCOVER_URL).mock(
            return_value=httpx.Response(200, json={"acctDetails": []})
        )
        client = httpx.Client()
        api = AccountsAPI(client)
        result = api.discover_accounts()
        assert result.accounts == []

    @respx.mock
    def test_get_account_features_passthrough(self):
        features_payload = {
            "accountFeatures": [
                {"acctNum": "Z25485019", "features": {"fractionalShares": True}},
                {"acctNum": "Z21772945", "features": {"fractionalShares": True}},
            ]
        }
        route = respx.post(FEATURES_URL).mock(
            return_value=httpx.Response(200, json=features_payload)
        )
        client = httpx.Client()
        api = AccountsAPI(client)
        result = api.get_account_features(["Z25485019", "Z21772945"])

        assert route.called
        assert result == features_payload

    @respx.mock
    def test_get_account_features_request_body(self):
        route = respx.post(FEATURES_URL).mock(
            return_value=httpx.Response(200, json={})
        )
        client = httpx.Client()
        api = AccountsAPI(client)
        api.get_account_features(["Z25485019", "Z33359950"])

        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["acctNums"] == ["Z25485019", "Z33359950"]

    @respx.mock
    def test_get_account_features_raises_on_http_error(self):
        respx.post(FEATURES_URL).mock(return_value=httpx.Response(403))
        client = httpx.Client()
        api = AccountsAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_account_features(["Z25485019"])

    @respx.mock
    def test_get_account_features_returns_dict(self):
        respx.post(FEATURES_URL).mock(
            return_value=httpx.Response(200, json={"someKey": "someValue"})
        )
        client = httpx.Client()
        api = AccountsAPI(client)
        result = api.get_account_features(["Z25485019"])
        assert isinstance(result, dict)
