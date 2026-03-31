"""Tests for the option position analytics API models and OptionAnalyticsAPI client."""
import math

import httpx
import pytest
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.analytics import (
    AnalyticsGreeks,
    PositionAnalytics,
    AnalyticsEvaluation,
    AnalyticsResponse,
)
from fidelity_trader.research.analytics import OptionAnalyticsAPI

_ANALYTICS_URL = f"{DPSERVICE_URL}/ftgw/dp/research/option/positions/analytics/v1"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_greeks(
    price: float = 6.18,
    profit: float = -8.0,
    delta: float = 0.0,
    theta: float = 0.0,
    gamma: float = 0.0,
    vega: float = 0.0,
    rho: float = 0.0,
    prem: float = 0.0,
    total_value: float = 0.0,
    prob_profit: float = 0.0,
    break_even: list = None,
    max_profit: object = 0.0,
    max_profit_1sd: list = None,
    max_loss_1sd: list = None,
    max_loss: object = -8.0,
    iv: float = None,
) -> dict:
    d = {
        "price": price,
        "profit": profit,
        "delta": delta,
        "theta": theta,
        "gamma": gamma,
        "vega": vega,
        "rho": rho,
        "prem": prem,
        "totalValue": total_value,
        "probProfit": prob_profit,
        "breakEven": break_even if break_even is not None else [],
        "maxProfit": max_profit,
        "maxProfit1sd": max_profit_1sd if max_profit_1sd is not None else [0.0],
        "maxLoss1sd": max_loss_1sd if max_loss_1sd is not None else [-8.0],
        "maxLoss": max_loss,
    }
    if iv is not None:
        d["iv"] = iv
    return d


def _make_position_analytics(
    position_detail: dict = None,
    leg_details: list = None,
) -> dict:
    if position_detail is None:
        position_detail = _make_greeks()
    if leg_details is None:
        leg_details = [
            _make_greeks(
                prob_profit=0.30437,
                break_even=[7.08],
                max_profit="Infinity",
                max_profit_1sd=[382.8682],
                max_loss_1sd=[-8.0],
                max_loss=-8.0,
                iv=0.82375,
            ),
            _make_greeks(
                profit=0.0,
                prob_profit=0.69112,
                break_even=[7.0],
                max_profit=0.0,
                max_profit_1sd=[0.0],
                max_loss_1sd=[-390.8682],
                max_loss="-Infinity",
                iv=0.82375,
            ),
        ]
    return {"positionDetail": position_detail, "legDetails": leg_details}


def _make_evaluation(
    eval_date: str = "1/21/2028",
    position_details: list = None,
) -> dict:
    if position_details is None:
        position_details = [_make_position_analytics()]
    return {"evalDate": eval_date, "positionDetails": position_details}


def _make_analytics_response(evaluations: list = None) -> dict:
    if evaluations is None:
        evaluations = [_make_evaluation()]
    return {"positionsAnalyticsDataDetails": evaluations}


_SAMPLE_LEGS = [
    {"symbol": "QS280121C7", "qty": 1, "price": 0.08, "equity": False},
    {"symbol": "QS280121C7", "qty": -1, "price": 0, "equity": False},
]


# ---------------------------------------------------------------------------
# AnalyticsGreeks
# ---------------------------------------------------------------------------

class TestAnalyticsGreeks:
    def test_parses_all_numeric_fields(self):
        raw = _make_greeks(
            price=6.18,
            profit=-8.0,
            delta=0.1,
            theta=-0.01,
            gamma=0.02,
            vega=0.05,
            rho=0.001,
            prem=0.5,
            total_value=100.0,
            prob_profit=0.30437,
        )
        g = AnalyticsGreeks.model_validate(raw)
        assert g.price == pytest.approx(6.18)
        assert g.profit == pytest.approx(-8.0)
        assert g.delta == pytest.approx(0.1)
        assert g.theta == pytest.approx(-0.01)
        assert g.gamma == pytest.approx(0.02)
        assert g.vega == pytest.approx(0.05)
        assert g.rho == pytest.approx(0.001)
        assert g.prem == pytest.approx(0.5)
        assert g.total_value == pytest.approx(100.0)
        assert g.prob_profit == pytest.approx(0.30437)

    def test_infinity_string_max_profit(self):
        raw = _make_greeks(max_profit="Infinity")
        g = AnalyticsGreeks.model_validate(raw)
        assert math.isinf(g.max_profit)
        assert g.max_profit > 0

    def test_neg_infinity_string_max_loss(self):
        raw = _make_greeks(max_loss="-Infinity")
        g = AnalyticsGreeks.model_validate(raw)
        assert math.isinf(g.max_loss)
        assert g.max_loss < 0

    def test_numeric_max_profit_and_loss(self):
        raw = _make_greeks(max_profit=500.0, max_loss=-100.0)
        g = AnalyticsGreeks.model_validate(raw)
        assert g.max_profit == pytest.approx(500.0)
        assert g.max_loss == pytest.approx(-100.0)

    def test_break_even_list(self):
        raw = _make_greeks(break_even=[7.08])
        g = AnalyticsGreeks.model_validate(raw)
        assert g.break_even == [pytest.approx(7.08)]

    def test_empty_break_even(self):
        raw = _make_greeks(break_even=[])
        g = AnalyticsGreeks.model_validate(raw)
        assert g.break_even == []

    def test_max_profit_1sd_list(self):
        raw = _make_greeks(max_profit_1sd=[382.8682])
        g = AnalyticsGreeks.model_validate(raw)
        assert g.max_profit_1sd == [pytest.approx(382.8682)]

    def test_max_loss_1sd_list(self):
        raw = _make_greeks(max_loss_1sd=[-390.8682])
        g = AnalyticsGreeks.model_validate(raw)
        assert g.max_loss_1sd == [pytest.approx(-390.8682)]

    def test_iv_optional_present(self):
        raw = _make_greeks(iv=0.82375)
        g = AnalyticsGreeks.model_validate(raw)
        assert g.iv == pytest.approx(0.82375)

    def test_iv_optional_absent(self):
        raw = _make_greeks()
        raw.pop("iv", None)
        g = AnalyticsGreeks.model_validate(raw)
        assert g.iv is None

    def test_alias_total_value(self):
        raw = {"totalValue": 42.5, "maxProfit": 0.0, "maxLoss": 0.0}
        g = AnalyticsGreeks.model_validate(raw)
        assert g.total_value == pytest.approx(42.5)

    def test_alias_prob_profit(self):
        raw = {"probProfit": 0.55, "maxProfit": 0.0, "maxLoss": 0.0}
        g = AnalyticsGreeks.model_validate(raw)
        assert g.prob_profit == pytest.approx(0.55)

    def test_defaults_when_missing(self):
        g = AnalyticsGreeks.model_validate({"maxProfit": 0.0, "maxLoss": 0.0})
        assert g.price == 0.0
        assert g.delta == 0.0
        assert g.break_even == []
        assert g.max_profit_1sd == []
        assert g.max_loss_1sd == []
        assert g.iv is None


# ---------------------------------------------------------------------------
# PositionAnalytics
# ---------------------------------------------------------------------------

class TestPositionAnalytics:
    def test_parses_position_detail(self):
        raw = _make_position_analytics()
        pa = PositionAnalytics.from_api_dict(raw)
        assert isinstance(pa.position_detail, AnalyticsGreeks)
        assert pa.position_detail.price == pytest.approx(6.18)

    def test_parses_leg_details(self):
        raw = _make_position_analytics()
        pa = PositionAnalytics.from_api_dict(raw)
        assert len(pa.leg_details) == 2

    def test_first_leg_infinity_max_profit(self):
        raw = _make_position_analytics()
        pa = PositionAnalytics.from_api_dict(raw)
        leg0 = pa.leg_details[0]
        assert math.isinf(leg0.max_profit)
        assert leg0.max_profit > 0

    def test_second_leg_neg_infinity_max_loss(self):
        raw = _make_position_analytics()
        pa = PositionAnalytics.from_api_dict(raw)
        leg1 = pa.leg_details[1]
        assert math.isinf(leg1.max_loss)
        assert leg1.max_loss < 0

    def test_first_leg_iv(self):
        raw = _make_position_analytics()
        pa = PositionAnalytics.from_api_dict(raw)
        assert pa.leg_details[0].iv == pytest.approx(0.82375)

    def test_position_detail_has_no_iv(self):
        raw = _make_position_analytics()
        pa = PositionAnalytics.from_api_dict(raw)
        assert pa.position_detail.iv is None

    def test_empty_leg_details(self):
        raw = _make_position_analytics(leg_details=[])
        pa = PositionAnalytics.from_api_dict(raw)
        assert pa.leg_details == []


# ---------------------------------------------------------------------------
# AnalyticsEvaluation
# ---------------------------------------------------------------------------

class TestAnalyticsEvaluation:
    def test_parses_eval_date(self):
        raw = _make_evaluation(eval_date="1/21/2028")
        ev = AnalyticsEvaluation.from_api_dict(raw)
        assert ev.eval_date == "1/21/2028"

    def test_parses_position_details(self):
        raw = _make_evaluation()
        ev = AnalyticsEvaluation.from_api_dict(raw)
        assert len(ev.position_details) == 1

    def test_empty_position_details(self):
        raw = {"evalDate": "1/21/2028", "positionDetails": []}
        ev = AnalyticsEvaluation.from_api_dict(raw)
        assert ev.position_details == []

    def test_missing_position_details(self):
        raw = {"evalDate": "1/21/2028"}
        ev = AnalyticsEvaluation.from_api_dict(raw)
        assert ev.position_details == []


# ---------------------------------------------------------------------------
# AnalyticsResponse
# ---------------------------------------------------------------------------

class TestAnalyticsResponse:
    def test_parses_full_captured_response(self):
        raw = _make_analytics_response()
        resp = AnalyticsResponse.from_api_response(raw)
        assert len(resp.evaluations) == 1

    def test_eval_date(self):
        raw = _make_analytics_response()
        resp = AnalyticsResponse.from_api_response(raw)
        assert resp.evaluations[0].eval_date == "1/21/2028"

    def test_position_detail_values(self):
        raw = _make_analytics_response()
        resp = AnalyticsResponse.from_api_response(raw)
        pos = resp.evaluations[0].position_details[0]
        assert pos.position_detail.price == pytest.approx(6.18)
        assert pos.position_detail.profit == pytest.approx(-8.0)
        assert pos.position_detail.max_loss == pytest.approx(-8.0)

    def test_leg0_infinity_max_profit(self):
        raw = _make_analytics_response()
        resp = AnalyticsResponse.from_api_response(raw)
        leg0 = resp.evaluations[0].position_details[0].leg_details[0]
        assert math.isinf(leg0.max_profit)

    def test_leg1_neg_infinity_max_loss(self):
        raw = _make_analytics_response()
        resp = AnalyticsResponse.from_api_response(raw)
        leg1 = resp.evaluations[0].position_details[0].leg_details[1]
        assert math.isinf(leg1.max_loss)
        assert leg1.max_loss < 0

    def test_empty_response(self):
        resp = AnalyticsResponse.from_api_response({})
        assert resp.evaluations == []

    def test_empty_evaluations_list(self):
        resp = AnalyticsResponse.from_api_response({"positionsAnalyticsDataDetails": []})
        assert resp.evaluations == []

    def test_multiple_evaluations(self):
        evals = [
            _make_evaluation("1/21/2028"),
            _make_evaluation("6/15/2027"),
        ]
        raw = _make_analytics_response(evals)
        resp = AnalyticsResponse.from_api_response(raw)
        assert len(resp.evaluations) == 2
        assert resp.evaluations[1].eval_date == "6/15/2027"


# ---------------------------------------------------------------------------
# OptionAnalyticsAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestOptionAnalyticsAPI:
    @respx.mock
    def test_analyze_position_makes_correct_request(self):
        raw = _make_analytics_response()
        route = respx.post(_ANALYTICS_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = OptionAnalyticsAPI(client)
        result = api.analyze_position("QS", _SAMPLE_LEGS)

        assert route.called
        assert isinstance(result, AnalyticsResponse)

    @respx.mock
    def test_analyze_position_request_body(self):
        import json as _json

        raw = _make_analytics_response()
        route = respx.post(_ANALYTICS_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = OptionAnalyticsAPI(client)
        api.analyze_position("QS", _SAMPLE_LEGS)

        request = route.calls[0].request
        body = _json.loads(request.content)
        assert body["underlyingSymbol"] == "QS"
        assert body["posDetails"] == [_SAMPLE_LEGS]
        assert body["hvDetail"]["volatilityPeriod"] == "90"
        assert body["evalDaysDetail"]["evalAtExpiry"] is True

    @respx.mock
    def test_analyze_position_custom_volatility_period(self):
        import json as _json

        raw = _make_analytics_response()
        route = respx.post(_ANALYTICS_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = OptionAnalyticsAPI(client)
        api.analyze_position("QS", _SAMPLE_LEGS, volatility_period="30")

        body = _json.loads(route.calls[0].request.content)
        assert body["hvDetail"]["volatilityPeriod"] == "30"

    @respx.mock
    def test_analyze_position_eval_at_expiry_false(self):
        import json as _json

        raw = _make_analytics_response()
        route = respx.post(_ANALYTICS_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = OptionAnalyticsAPI(client)
        api.analyze_position("QS", _SAMPLE_LEGS, eval_at_expiry=False)

        body = _json.loads(route.calls[0].request.content)
        assert body["evalDaysDetail"]["evalAtExpiry"] is False

    @respx.mock
    def test_analyze_position_parses_response(self):
        raw = _make_analytics_response()
        respx.post(_ANALYTICS_URL).mock(return_value=httpx.Response(200, json=raw))
        client = httpx.Client()
        api = OptionAnalyticsAPI(client)
        result = api.analyze_position("QS", _SAMPLE_LEGS)

        assert len(result.evaluations) == 1
        ev = result.evaluations[0]
        assert ev.eval_date == "1/21/2028"
        assert len(ev.position_details) == 1
        pos = ev.position_details[0]
        assert pos.position_detail.price == pytest.approx(6.18)
        assert len(pos.leg_details) == 2

    @respx.mock
    def test_analyze_position_raises_on_http_error(self):
        respx.post(_ANALYTICS_URL).mock(return_value=httpx.Response(401))
        client = httpx.Client()
        api = OptionAnalyticsAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.analyze_position("QS", _SAMPLE_LEGS)

    @respx.mock
    def test_analyze_position_raises_on_server_error(self):
        respx.post(_ANALYTICS_URL).mock(return_value=httpx.Response(500))
        client = httpx.Client()
        api = OptionAnalyticsAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.analyze_position("QS", _SAMPLE_LEGS)

    @respx.mock
    def test_analyze_position_leg_infinity_values(self):
        raw = _make_analytics_response()
        respx.post(_ANALYTICS_URL).mock(return_value=httpx.Response(200, json=raw))
        client = httpx.Client()
        api = OptionAnalyticsAPI(client)
        result = api.analyze_position("QS", _SAMPLE_LEGS)

        pos = result.evaluations[0].position_details[0]
        assert math.isinf(pos.leg_details[0].max_profit)
        assert pos.leg_details[0].max_profit > 0
        assert math.isinf(pos.leg_details[1].max_loss)
        assert pos.leg_details[1].max_loss < 0

    @respx.mock
    def test_analyze_position_iv_values(self):
        raw = _make_analytics_response()
        respx.post(_ANALYTICS_URL).mock(return_value=httpx.Response(200, json=raw))
        client = httpx.Client()
        api = OptionAnalyticsAPI(client)
        result = api.analyze_position("QS", _SAMPLE_LEGS)

        pos = result.evaluations[0].position_details[0]
        assert pos.leg_details[0].iv == pytest.approx(0.82375)
        assert pos.leg_details[1].iv == pytest.approx(0.82375)
