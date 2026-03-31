"""Tests for the research (earnings + dividends) API models and ResearchAPI client."""
import pytest
import httpx
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.research import (
    SecDetail,
    EarningsQuarter,
    EarningsDetail,
    EarningsResponse,
    DividendHistory,
    DividendDetail,
    DividendsResponse,
)
from fidelity_trader.research.data import ResearchAPI

_EARNINGS_URL = f"{DPSERVICE_URL}/ftgw/dpdirect/research/earning/v1"
_DIVIDENDS_URL = f"{DPSERVICE_URL}/ftgw/dpdirect/research/dividend/v1"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_sec_detail(
    requested: str = "UAL",
    classification: str = "Common Stock",
    symbol: str = "UAL",
    cusip: str = "910047109",
) -> dict:
    return {
        "requested": requested,
        "classification": classification,
        "symbol": symbol,
        "CUSIP": cusip,
    }


def _make_earnings_quarter(
    fiscal_qtr: int = 1,
    fiscal_yr: int = 2024,
    report_date: str = "04/16/2024",
    adjusted_eps: float = -0.15,
    consensus_est: float = -0.575,
) -> dict:
    return {
        "fiscalQtr": fiscal_qtr,
        "fiscalYr": fiscal_yr,
        "reportDate": report_date,
        "adjustedEPS": adjusted_eps,
        "consensusEst": consensus_est,
    }


def _make_earning_detail(
    sec_detail: dict = None,
    quarters: list[dict] = None,
    eps_prev: float = 8.13559,
) -> dict:
    if sec_detail is None:
        sec_detail = _make_sec_detail()
    if quarters is None:
        quarters = [_make_earnings_quarter()]
    return {
        "secDetail": sec_detail,
        "qtrHistDetails": {"qtrHistDetail": quarters},
        "epsPrevQtrVsPrevYrQtr": eps_prev,
    }


def _make_earnings_response(details: list[dict] = None) -> dict:
    if details is None:
        details = [_make_earning_detail()]
    return {
        "earning": {
            "earningDetails": {
                "earningDetail": details,
            }
        }
    }


def _make_div_history(
    amt: float = 2.1,
    announce_date: str = "06/05/24",
    freq_name: str = "Quarterly",
    pay_date: str = "06/25/24",
    ex_date: str = "06/17/24",
    record_date: str = "06/17/24",
    currency: str = "USD",
    type_: str = "Regular",
    ex_date_cal_qtr: str = "Q2",
    ex_date_cal_yr: int = 2024,
) -> dict:
    return {
        "amt": amt,
        "announceDate": announce_date,
        "freqName": freq_name,
        "payDate": pay_date,
        "exDate": ex_date,
        "recordDate": record_date,
        "currency": currency,
        "type": type_,
        "exDateCalQtr": ex_date_cal_qtr,
        "exDateCalYr": ex_date_cal_yr,
    }


def _make_dividend_detail(
    sec_detail: dict = None,
    amt: float = 2.21,
    announce_date: str = "02/25/26",
    ex_div_date: str = "03/09/26",
    yld_ttm: float = 3.412864,
    indicated_ann_div: float = 8.84,
    history: list[dict] = None,
) -> dict:
    if sec_detail is None:
        sec_detail = _make_sec_detail("UNH", "Common Stock", "UNH", "91324P102")
    if history is None:
        history = [_make_div_history()]
    return {
        "secDetail": sec_detail,
        "equityDetail": {
            "amt": amt,
            "announceDate": announce_date,
            "exDivDate": ex_div_date,
            "yldTTM": yld_ttm,
            "indicatedAnnDiv": indicated_ann_div,
            "divHistDetails": {"divHistDetail": history},
        },
    }


def _make_dividends_response(details: list[dict] = None) -> dict:
    if details is None:
        details = [_make_dividend_detail()]
    return {
        "dividend": {
            "dividendDetails": {
                "dividendDetail": details,
            }
        }
    }


# ---------------------------------------------------------------------------
# SecDetail
# ---------------------------------------------------------------------------

class TestSecDetail:
    def test_parses_all_fields(self):
        sd = SecDetail.model_validate(_make_sec_detail())
        assert sd.requested == "UAL"
        assert sd.classification == "Common Stock"
        assert sd.symbol == "UAL"
        assert sd.cusip == "910047109"

    def test_cusip_alias(self):
        sd = SecDetail.model_validate({"CUSIP": "91324P102", "symbol": "UNH"})
        assert sd.cusip == "91324P102"

    def test_optional_fields_default_none(self):
        sd = SecDetail.model_validate({})
        assert sd.requested is None
        assert sd.cusip is None


# ---------------------------------------------------------------------------
# EarningsQuarter
# ---------------------------------------------------------------------------

class TestEarningsQuarter:
    def test_parses_all_fields(self):
        q = EarningsQuarter.model_validate(_make_earnings_quarter())
        assert q.fiscal_qtr == 1
        assert q.fiscal_yr == 2024
        assert q.report_date == "04/16/2024"
        assert q.adjusted_eps == pytest.approx(-0.15)
        assert q.consensus_est == pytest.approx(-0.575)

    def test_optional_eps_fields(self):
        q = EarningsQuarter.model_validate({"fiscalQtr": 3, "fiscalYr": 2025})
        assert q.adjusted_eps is None
        assert q.consensus_est is None

    def test_second_quarter(self):
        q = EarningsQuarter.model_validate(_make_earnings_quarter(
            fiscal_qtr=2, fiscal_yr=2024, report_date="07/17/2024",
            adjusted_eps=4.14, consensus_est=3.935,
        ))
        assert q.fiscal_qtr == 2
        assert q.adjusted_eps == pytest.approx(4.14)
        assert q.consensus_est == pytest.approx(3.935)


# ---------------------------------------------------------------------------
# EarningsDetail
# ---------------------------------------------------------------------------

class TestEarningsDetail:
    def test_parses_from_api_dict(self):
        raw = _make_earning_detail(
            quarters=[
                _make_earnings_quarter(1, 2024, "04/16/2024", -0.15, -0.575),
                _make_earnings_quarter(2, 2024, "07/17/2024", 4.14, 3.935),
            ]
        )
        detail = EarningsDetail.from_api_dict(raw)
        assert detail.sec_detail is not None
        assert detail.sec_detail.symbol == "UAL"
        assert len(detail.quarters) == 2
        assert detail.quarters[0].fiscal_qtr == 1
        assert detail.quarters[1].adjusted_eps == pytest.approx(4.14)
        assert detail.eps_prev_qtr_vs_prev_yr_qtr == pytest.approx(8.13559)

    def test_empty_quarters(self):
        raw = _make_earning_detail(quarters=[])
        detail = EarningsDetail.from_api_dict(raw)
        assert detail.quarters == []

    def test_missing_qtr_hist_details(self):
        raw = {"secDetail": _make_sec_detail(), "epsPrevQtrVsPrevYrQtr": 1.5}
        detail = EarningsDetail.from_api_dict(raw)
        assert detail.quarters == []
        assert detail.eps_prev_qtr_vs_prev_yr_qtr == pytest.approx(1.5)

    def test_optional_eps_prev(self):
        raw = {
            "secDetail": _make_sec_detail(),
            "qtrHistDetails": {"qtrHistDetail": [_make_earnings_quarter()]},
        }
        detail = EarningsDetail.from_api_dict(raw)
        assert detail.eps_prev_qtr_vs_prev_yr_qtr is None


# ---------------------------------------------------------------------------
# EarningsResponse
# ---------------------------------------------------------------------------

class TestEarningsResponse:
    def test_parses_full_response(self):
        raw = _make_earnings_response()
        resp = EarningsResponse.from_api_response(raw)
        assert len(resp.earnings) == 1
        assert resp.earnings[0].sec_detail.symbol == "UAL"

    def test_multiple_symbols(self):
        details = [
            _make_earning_detail(_make_sec_detail("UAL", symbol="UAL", cusip="910047109")),
            _make_earning_detail(_make_sec_detail("LGVN", symbol="LGVN", cusip="501889108")),
        ]
        resp = EarningsResponse.from_api_response(_make_earnings_response(details))
        assert len(resp.earnings) == 2
        assert resp.earnings[1].sec_detail.symbol == "LGVN"

    def test_empty_response(self):
        resp = EarningsResponse.from_api_response({})
        assert resp.earnings == []

    def test_empty_earning_details(self):
        raw = {"earning": {"earningDetails": {"earningDetail": []}}}
        resp = EarningsResponse.from_api_response(raw)
        assert resp.earnings == []


# ---------------------------------------------------------------------------
# DividendHistory
# ---------------------------------------------------------------------------

class TestDividendHistory:
    def test_parses_all_fields(self):
        h = DividendHistory.model_validate(_make_div_history())
        assert h.amt == pytest.approx(2.1)
        assert h.announce_date == "06/05/24"
        assert h.freq_name == "Quarterly"
        assert h.pay_date == "06/25/24"
        assert h.ex_date == "06/17/24"
        assert h.record_date == "06/17/24"
        assert h.currency == "USD"
        assert h.type == "Regular"
        assert h.ex_date_cal_qtr == "Q2"
        assert h.ex_date_cal_yr == 2024

    def test_optional_fields_default_none(self):
        h = DividendHistory.model_validate({})
        assert h.amt is None
        assert h.ex_date_cal_yr is None


# ---------------------------------------------------------------------------
# DividendDetail
# ---------------------------------------------------------------------------

class TestDividendDetail:
    def test_parses_from_api_dict(self):
        raw = _make_dividend_detail()
        detail = DividendDetail.from_api_dict(raw)
        assert detail.sec_detail is not None
        assert detail.sec_detail.symbol == "UNH"
        assert detail.sec_detail.cusip == "91324P102"
        assert detail.amt == pytest.approx(2.21)
        assert detail.announce_date == "02/25/26"
        assert detail.ex_div_date == "03/09/26"
        assert detail.yld_ttm == pytest.approx(3.412864)
        assert detail.indicated_ann_div == pytest.approx(8.84)
        assert len(detail.history) == 1

    def test_history_entry_fields(self):
        raw = _make_dividend_detail()
        detail = DividendDetail.from_api_dict(raw)
        h = detail.history[0]
        assert h.amt == pytest.approx(2.1)
        assert h.freq_name == "Quarterly"
        assert h.currency == "USD"
        assert h.ex_date_cal_yr == 2024

    def test_empty_history(self):
        raw = _make_dividend_detail(history=[])
        detail = DividendDetail.from_api_dict(raw)
        assert detail.history == []

    def test_missing_equity_detail(self):
        raw = {"secDetail": _make_sec_detail("UNH", symbol="UNH", cusip="91324P102")}
        detail = DividendDetail.from_api_dict(raw)
        assert detail.amt is None
        assert detail.yld_ttm is None
        assert detail.history == []


# ---------------------------------------------------------------------------
# DividendsResponse
# ---------------------------------------------------------------------------

class TestDividendsResponse:
    def test_parses_full_response(self):
        raw = _make_dividends_response()
        resp = DividendsResponse.from_api_response(raw)
        assert len(resp.dividends) == 1
        assert resp.dividends[0].sec_detail.symbol == "UNH"

    def test_multiple_symbols(self):
        details = [
            _make_dividend_detail(_make_sec_detail("UNH", symbol="UNH", cusip="91324P102")),
            _make_dividend_detail(_make_sec_detail("AAPL", symbol="AAPL", cusip="037833100")),
        ]
        resp = DividendsResponse.from_api_response(_make_dividends_response(details))
        assert len(resp.dividends) == 2
        assert resp.dividends[1].sec_detail.symbol == "AAPL"

    def test_empty_response(self):
        resp = DividendsResponse.from_api_response({})
        assert resp.dividends == []

    def test_empty_dividend_details(self):
        raw = {"dividend": {"dividendDetails": {"dividendDetail": []}}}
        resp = DividendsResponse.from_api_response(raw)
        assert resp.dividends == []


# ---------------------------------------------------------------------------
# ResearchAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestResearchAPIEarnings:
    @respx.mock
    def test_get_earnings_makes_correct_request(self):
        raw = _make_earnings_response()
        route = respx.get(_EARNINGS_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = ResearchAPI(client)
        result = api.get_earnings(["UAL"])

        assert route.called
        assert isinstance(result, EarningsResponse)

    @respx.mock
    def test_get_earnings_pipe_delimited_symbols(self):
        raw = _make_earnings_response()
        route = respx.get(_EARNINGS_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = ResearchAPI(client)
        api.get_earnings(["LGVN", "UAL", "AZTR"])

        request = route.calls[0].request
        assert "fvSymbol=LGVN%7CUAL%7CAZTR" in str(request.url)

    @respx.mock
    def test_get_earnings_includes_fsreqid_header(self):
        raw = _make_earnings_response()
        route = respx.get(_EARNINGS_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = ResearchAPI(client)
        api.get_earnings(["UAL"])

        request = route.calls[0].request
        assert "fsreqid" in request.headers
        assert request.headers["fsreqid"].startswith("REQ")

    @respx.mock
    def test_get_earnings_raises_on_http_error(self):
        respx.get(_EARNINGS_URL).mock(return_value=httpx.Response(401))
        client = httpx.Client()
        api = ResearchAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_earnings(["UAL"])

    @respx.mock
    def test_get_earnings_parses_response(self):
        details = [
            _make_earning_detail(
                _make_sec_detail("UAL", symbol="UAL", cusip="910047109"),
                quarters=[
                    _make_earnings_quarter(1, 2024, "04/16/2024", -0.15, -0.575),
                    _make_earnings_quarter(2, 2024, "07/17/2024", 4.14, 3.935),
                ],
                eps_prev=8.13559,
            )
        ]
        raw = _make_earnings_response(details)
        respx.get(_EARNINGS_URL).mock(return_value=httpx.Response(200, json=raw))
        client = httpx.Client()
        api = ResearchAPI(client)
        result = api.get_earnings(["UAL"])

        assert len(result.earnings) == 1
        detail = result.earnings[0]
        assert detail.sec_detail.symbol == "UAL"
        assert len(detail.quarters) == 2
        assert detail.quarters[1].adjusted_eps == pytest.approx(4.14)
        assert detail.eps_prev_qtr_vs_prev_yr_qtr == pytest.approx(8.13559)


class TestResearchAPIDividends:
    @respx.mock
    def test_get_dividends_makes_correct_request(self):
        raw = _make_dividends_response()
        route = respx.get(_DIVIDENDS_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = ResearchAPI(client)
        result = api.get_dividends(["UNH"])

        assert route.called
        assert isinstance(result, DividendsResponse)

    @respx.mock
    def test_get_dividends_pipe_delimited_symbols(self):
        raw = _make_dividends_response()
        route = respx.get(_DIVIDENDS_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = ResearchAPI(client)
        api.get_dividends(["LGVN", "UAL", "UNH"])

        request = route.calls[0].request
        assert "fvSymbol=LGVN%7CUAL%7CUNH" in str(request.url)

    @respx.mock
    def test_get_dividends_includes_fsreqid_header(self):
        raw = _make_dividends_response()
        route = respx.get(_DIVIDENDS_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = ResearchAPI(client)
        api.get_dividends(["UNH"])

        request = route.calls[0].request
        assert "fsreqid" in request.headers
        assert request.headers["fsreqid"].startswith("REQ")

    @respx.mock
    def test_get_dividends_raises_on_http_error(self):
        respx.get(_DIVIDENDS_URL).mock(return_value=httpx.Response(403))
        client = httpx.Client()
        api = ResearchAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_dividends(["UNH"])

    @respx.mock
    def test_get_dividends_parses_response(self):
        raw = _make_dividends_response()
        respx.get(_DIVIDENDS_URL).mock(return_value=httpx.Response(200, json=raw))
        client = httpx.Client()
        api = ResearchAPI(client)
        result = api.get_dividends(["UNH"])

        assert len(result.dividends) == 1
        detail = result.dividends[0]
        assert detail.sec_detail.symbol == "UNH"
        assert detail.sec_detail.cusip == "91324P102"
        assert detail.amt == pytest.approx(2.21)
        assert detail.yld_ttm == pytest.approx(3.412864)
        assert detail.indicated_ann_div == pytest.approx(8.84)
        assert len(detail.history) == 1
        assert detail.history[0].freq_name == "Quarterly"
