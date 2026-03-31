"""Tests for the tax lots API models and TaxLotAPI client."""
import pytest
import httpx
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.tax_lot import (
    SecurityDetail,
    TaxLotSummary,
    TaxLotAccountingDetail,
    TaxLotDetail,
    SpecificShrTaxLotDetail,
    TaxLotResponse,
)
from fidelity_trader.portfolio.tax_lots import TaxLotAPI


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_accounting_detail(
    qty: float = 0.0,
    term: str = "Short",
    acquisition_price: float = 0.89,
    cost_basis: float = 7.12,
    unrealized_gain_loss: float = 0.323,
    source: str = "Fidelity",
    wash_sale_ind: bool = False,
    event_id: str = "114703552256",
    acquisition_date: int = 1773720000,
    avg_cost_per_share: float = 0.89,
) -> dict:
    return {
        "qty": qty,
        "term": term,
        "acquisitionPrice": acquisition_price,
        "costBasis": cost_basis,
        "unrealizedGainLoss": unrealized_gain_loss,
        "source": source,
        "washSaleInd": wash_sale_ind,
        "disqualifiedDisplayTypeCode": "0",
        "eventIdOrig": "",
        "localTLABasisPerShare": "0.0000",
        "localTLATotalBasis": "0.0000",
        "localUnrealizedGainLoss": "0.0000",
        "eventId": event_id,
        "acquisitionDate": acquisition_date,
        "avgCostPerShare": avg_cost_per_share,
    }


def _make_lot_detail(
    lot_seq: int = 1,
    lot_qty: float = 8.0,
    accounting_detail: dict = None,
) -> dict:
    if accounting_detail is None:
        accounting_detail = _make_accounting_detail()
    return {
        "lotSeq": lot_seq,
        "lotQty": lot_qty,
        "specificShrTaxLotAccountingDetail": accounting_detail,
    }


def _make_api_response(
    symbol: str = "LGVN",
    acct_num: str = "Z25485019",
    lots: list[dict] = None,
    exec_qty: float = 0.0,
    num_of_lots: int = 0,
    num_of_lots_total: int = 1,
) -> dict:
    if lots is None:
        lots = [_make_lot_detail()]
    return {
        "securityDetail": {"symbol": symbol},
        "execQty": exec_qty,
        "specificShrTaxLotDetail": {
            "specificShrTaxLotDetails": lots,
            "numOfLots": num_of_lots,
            "summary": {
                "numOfLotsTotal": num_of_lots_total,
                "numOfLots": num_of_lots,
            },
        },
        "acctNum": acct_num,
        "acctTypeCode": 1,
        "lotCurrInd": "false",
    }


# ---------------------------------------------------------------------------
# SecurityDetail
# ---------------------------------------------------------------------------


class TestSecurityDetail:
    def test_parses_symbol(self):
        sd = SecurityDetail.model_validate({"symbol": "LGVN"})
        assert sd.symbol == "LGVN"

    def test_optional_symbol_defaults_none(self):
        sd = SecurityDetail.model_validate({})
        assert sd.symbol is None


# ---------------------------------------------------------------------------
# TaxLotSummary
# ---------------------------------------------------------------------------


class TestTaxLotSummary:
    def test_parses_all_fields(self):
        s = TaxLotSummary.model_validate({"numOfLotsTotal": 3, "numOfLots": 2})
        assert s.num_of_lots_total == 3
        assert s.num_of_lots == 2

    def test_optional_fields_default_none(self):
        s = TaxLotSummary.model_validate({})
        assert s.num_of_lots_total is None
        assert s.num_of_lots is None


# ---------------------------------------------------------------------------
# TaxLotAccountingDetail
# ---------------------------------------------------------------------------


class TestTaxLotAccountingDetail:
    def test_parses_all_fields(self):
        raw = _make_accounting_detail()
        detail = TaxLotAccountingDetail.model_validate(raw)
        assert detail.qty == pytest.approx(0.0)
        assert detail.term == "Short"
        assert detail.acquisition_price == pytest.approx(0.89)
        assert detail.cost_basis == pytest.approx(7.12)
        assert detail.unrealized_gain_loss == pytest.approx(0.323)
        assert detail.source == "Fidelity"
        assert detail.wash_sale_ind is False
        assert detail.event_id == "114703552256"
        assert detail.acquisition_date == 1773720000
        assert detail.avg_cost_per_share == pytest.approx(0.89)

    def test_optional_fields_default_none(self):
        detail = TaxLotAccountingDetail.model_validate({})
        assert detail.qty is None
        assert detail.term is None
        assert detail.acquisition_price is None

    def test_coerces_string_float(self):
        detail = TaxLotAccountingDetail.model_validate({"acquisitionPrice": "1.2345"})
        assert detail.acquisition_price == pytest.approx(1.2345)

    def test_sentinel_string_becomes_none(self):
        detail = TaxLotAccountingDetail.model_validate({"costBasis": "--"})
        assert detail.cost_basis is None

    def test_wash_sale_ind_false(self):
        detail = TaxLotAccountingDetail.model_validate({"washSaleInd": False})
        assert detail.wash_sale_ind is False

    def test_wash_sale_ind_true(self):
        detail = TaxLotAccountingDetail.model_validate({"washSaleInd": True})
        assert detail.wash_sale_ind is True

    def test_string_fields_preserved(self):
        detail = TaxLotAccountingDetail.model_validate({
            "localTLABasisPerShare": "0.0000",
            "localTLATotalBasis": "0.0000",
            "localUnrealizedGainLoss": "0.0000",
        })
        assert detail.local_tla_basis_per_share == "0.0000"
        assert detail.local_tla_total_basis == "0.0000"
        assert detail.local_unrealized_gain_loss == "0.0000"


# ---------------------------------------------------------------------------
# TaxLotDetail
# ---------------------------------------------------------------------------


class TestTaxLotDetail:
    def test_parses_all_fields(self):
        raw = _make_lot_detail(lot_seq=2, lot_qty=10.0)
        detail = TaxLotDetail.model_validate(raw)
        assert detail.lot_seq == 2
        assert detail.lot_qty == pytest.approx(10.0)
        assert detail.specific_shr_tax_lot_accounting_detail is not None

    def test_accounting_detail_nested(self):
        raw = _make_lot_detail()
        detail = TaxLotDetail.model_validate(raw)
        acct = detail.specific_shr_tax_lot_accounting_detail
        assert acct is not None
        assert acct.acquisition_price == pytest.approx(0.89)
        assert acct.cost_basis == pytest.approx(7.12)

    def test_optional_fields_default_none(self):
        detail = TaxLotDetail.model_validate({})
        assert detail.lot_seq is None
        assert detail.lot_qty is None
        assert detail.specific_shr_tax_lot_accounting_detail is None

    def test_lot_qty_coerces_string(self):
        detail = TaxLotDetail.model_validate({"lotQty": "5.5"})
        assert detail.lot_qty == pytest.approx(5.5)


# ---------------------------------------------------------------------------
# SpecificShrTaxLotDetail
# ---------------------------------------------------------------------------


class TestSpecificShrTaxLotDetail:
    def test_parses_lot_list(self):
        raw = {
            "specificShrTaxLotDetails": [_make_lot_detail(1), _make_lot_detail(2)],
            "numOfLots": 2,
            "summary": {"numOfLotsTotal": 2, "numOfLots": 2},
        }
        detail = SpecificShrTaxLotDetail.model_validate(raw)
        assert len(detail.specific_shr_tax_lot_details) == 2
        assert detail.num_of_lots == 2
        assert detail.summary is not None
        assert detail.summary.num_of_lots_total == 2

    def test_empty_lots_list(self):
        raw = {"specificShrTaxLotDetails": [], "numOfLots": 0}
        detail = SpecificShrTaxLotDetail.model_validate(raw)
        assert detail.specific_shr_tax_lot_details == []
        assert detail.num_of_lots == 0

    def test_missing_lots_defaults_empty(self):
        detail = SpecificShrTaxLotDetail.model_validate({})
        assert detail.specific_shr_tax_lot_details == []
        assert detail.summary is None


# ---------------------------------------------------------------------------
# TaxLotResponse — full integration parsing
# ---------------------------------------------------------------------------


class TestTaxLotResponse:
    def test_parses_full_response(self):
        raw = _make_api_response()
        resp = TaxLotResponse.from_api_response(raw)
        assert resp.acct_num == "Z25485019"
        assert resp.acct_type_code == 1
        assert resp.lot_curr_ind == "false"
        assert resp.exec_qty == pytest.approx(0.0)

    def test_security_detail_nested(self):
        raw = _make_api_response(symbol="LGVN")
        resp = TaxLotResponse.from_api_response(raw)
        assert resp.security_detail is not None
        assert resp.security_detail.symbol == "LGVN"

    def test_tax_lot_detail_nested(self):
        raw = _make_api_response()
        resp = TaxLotResponse.from_api_response(raw)
        assert resp.specific_shr_tax_lot_detail is not None
        lots = resp.specific_shr_tax_lot_detail.specific_shr_tax_lot_details
        assert len(lots) == 1
        assert lots[0].lot_seq == 1
        assert lots[0].lot_qty == pytest.approx(8.0)

    def test_accounting_detail_in_lot(self):
        raw = _make_api_response()
        resp = TaxLotResponse.from_api_response(raw)
        acct = resp.specific_shr_tax_lot_detail.specific_shr_tax_lot_details[0].specific_shr_tax_lot_accounting_detail
        assert acct is not None
        assert acct.term == "Short"
        assert acct.acquisition_price == pytest.approx(0.89)
        assert acct.cost_basis == pytest.approx(7.12)
        assert acct.unrealized_gain_loss == pytest.approx(0.323)
        assert acct.wash_sale_ind is False
        assert acct.acquisition_date == 1773720000

    def test_summary_nested(self):
        raw = _make_api_response(num_of_lots_total=3, num_of_lots=1)
        resp = TaxLotResponse.from_api_response(raw)
        summary = resp.specific_shr_tax_lot_detail.summary
        assert summary is not None
        assert summary.num_of_lots_total == 3
        assert summary.num_of_lots == 1

    def test_multiple_lots(self):
        lots = [
            _make_lot_detail(lot_seq=1, lot_qty=5.0,
                             accounting_detail=_make_accounting_detail(cost_basis=4.45)),
            _make_lot_detail(lot_seq=2, lot_qty=3.0,
                             accounting_detail=_make_accounting_detail(cost_basis=2.67)),
        ]
        raw = _make_api_response(lots=lots, num_of_lots_total=2)
        resp = TaxLotResponse.from_api_response(raw)
        detail = resp.specific_shr_tax_lot_detail
        assert len(detail.specific_shr_tax_lot_details) == 2
        assert detail.specific_shr_tax_lot_details[0].lot_qty == pytest.approx(5.0)
        assert detail.specific_shr_tax_lot_details[1].lot_qty == pytest.approx(3.0)
        assert detail.specific_shr_tax_lot_details[0].specific_shr_tax_lot_accounting_detail.cost_basis == pytest.approx(4.45)
        assert detail.specific_shr_tax_lot_details[1].specific_shr_tax_lot_accounting_detail.cost_basis == pytest.approx(2.67)

    def test_empty_response_body(self):
        resp = TaxLotResponse.from_api_response({})
        assert resp.acct_num is None
        assert resp.security_detail is None
        assert resp.specific_shr_tax_lot_detail is None

    def test_from_api_response_different_symbol(self):
        raw = _make_api_response(symbol="AAPL", acct_num="X12345678")
        resp = TaxLotResponse.from_api_response(raw)
        assert resp.security_detail.symbol == "AAPL"
        assert resp.acct_num == "X12345678"


# ---------------------------------------------------------------------------
# TaxLotAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------


class TestTaxLotAPI:
    @respx.mock
    def test_get_tax_lots_makes_correct_request(self):
        raw_response = _make_api_response()
        route = respx.post(
            f"{DPSERVICE_URL}/ftgw/dp/orderentry/taxlot/v1"
        ).mock(return_value=httpx.Response(200, json=raw_response))
        client = httpx.Client()
        api = TaxLotAPI(client)
        result = api.get_tax_lots("Z25485019", "LGVN")

        assert route.called
        assert isinstance(result, TaxLotResponse)
        assert result.acct_num == "Z25485019"
        assert result.security_detail.symbol == "LGVN"

    @respx.mock
    def test_get_tax_lots_request_body_shape(self):
        raw_response = _make_api_response()
        route = respx.post(
            f"{DPSERVICE_URL}/ftgw/dp/orderentry/taxlot/v1"
        ).mock(return_value=httpx.Response(200, json=raw_response))
        client = httpx.Client()
        api = TaxLotAPI(client)
        api.get_tax_lots("Z25485019", "LGVN")

        import json
        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["holdingTypeCode"] == "_1"
        assert sent_body["acctNum"] == "Z25485019"
        assert sent_body["securityDetail"]["symbol"] == "LGVN"

    @respx.mock
    def test_get_tax_lots_custom_holding_type(self):
        raw_response = _make_api_response()
        route = respx.post(
            f"{DPSERVICE_URL}/ftgw/dp/orderentry/taxlot/v1"
        ).mock(return_value=httpx.Response(200, json=raw_response))
        client = httpx.Client()
        api = TaxLotAPI(client)
        api.get_tax_lots("Z25485019", "LGVN", holding_type="_2")

        import json
        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["holdingTypeCode"] == "_2"

    @respx.mock
    def test_get_tax_lots_raises_on_http_error(self):
        respx.post(
            f"{DPSERVICE_URL}/ftgw/dp/orderentry/taxlot/v1"
        ).mock(return_value=httpx.Response(401))
        client = httpx.Client()
        api = TaxLotAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_tax_lots("Z25485019", "LGVN")

    @respx.mock
    def test_get_tax_lots_returns_parsed_lots(self):
        lots = [
            _make_lot_detail(lot_seq=1, lot_qty=8.0),
            _make_lot_detail(lot_seq=2, lot_qty=4.0),
        ]
        raw_response = _make_api_response(lots=lots, num_of_lots_total=2)
        respx.post(
            f"{DPSERVICE_URL}/ftgw/dp/orderentry/taxlot/v1"
        ).mock(return_value=httpx.Response(200, json=raw_response))
        client = httpx.Client()
        api = TaxLotAPI(client)
        result = api.get_tax_lots("Z25485019", "LGVN")

        assert result.specific_shr_tax_lot_detail is not None
        lot_details = result.specific_shr_tax_lot_detail.specific_shr_tax_lot_details
        assert len(lot_details) == 2
        assert lot_details[0].lot_seq == 1
        assert lot_details[1].lot_seq == 2
