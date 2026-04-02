"""Tests for the price triggers list API models and PriceTriggersAPI client."""
import pytest
import httpx
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.price_trigger import (
    PriceTrigger,
    PriceTriggerSummary,
    PriceTriggersResponse,
)
from fidelity_trader.alerts.price_triggers import PriceTriggersAPI

_PRICE_TRIGGERS_URL = (
    f"{DPSERVICE_URL}/ftgw/dp/retail-price-triggers/v1"
    "/investments/research/alert/price-triggers/list"
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_EMPTY_RESPONSE = {
    "priceTrigger": {
        "totalAccount": 0,
        "availableAccount": 0,
        "offset": 0,
        "triggers": [],
    }
}

_POPULATED_RESPONSE = {
    "priceTrigger": {
        "totalAccount": 3,
        "availableAccount": 5,
        "offset": 0,
        "triggers": [
            {
                "triggerId": "TRG001",
                "symbol": "QS",
                "triggerType": "PRICE_ABOVE",
                "triggerPrice": 10.50,
                "status": "active",
                "createdDate": "2026-03-15",
            },
            {
                "triggerId": "TRG002",
                "symbol": "QS",
                "triggerType": "PRICE_BELOW",
                "triggerPrice": 5.25,
                "status": "active",
                "createdDate": "2026-03-20",
            },
        ],
    }
}

_SINGLE_TRIGGER_RESPONSE = {
    "priceTrigger": {
        "totalAccount": 1,
        "availableAccount": 1,
        "offset": 0,
        "triggers": [
            {
                "triggerId": "TRG100",
                "symbol": "AAPL",
                "triggerType": "PRICE_ABOVE",
                "triggerPrice": 200.00,
                "status": "active",
                "createdDate": "2026-04-01",
            },
        ],
    }
}


# ---------------------------------------------------------------------------
# PriceTrigger model
# ---------------------------------------------------------------------------

class TestPriceTrigger:
    def test_parses_full_trigger(self):
        raw = _POPULATED_RESPONSE["priceTrigger"]["triggers"][0]
        t = PriceTrigger.model_validate(raw)
        assert t.trigger_id == "TRG001"
        assert t.symbol == "QS"
        assert t.trigger_type == "PRICE_ABOVE"
        assert t.trigger_price == 10.50
        assert t.status == "active"
        assert t.created_date == "2026-03-15"

    def test_parses_below_trigger(self):
        raw = _POPULATED_RESPONSE["priceTrigger"]["triggers"][1]
        t = PriceTrigger.model_validate(raw)
        assert t.trigger_id == "TRG002"
        assert t.trigger_type == "PRICE_BELOW"
        assert t.trigger_price == 5.25

    def test_optional_fields_default_none(self):
        t = PriceTrigger.model_validate({})
        assert t.trigger_id is None
        assert t.symbol is None
        assert t.trigger_type is None
        assert t.trigger_price is None
        assert t.status is None
        assert t.created_date is None

    def test_alias_population(self):
        t = PriceTrigger.model_validate({
            "triggerId": "X1",
            "triggerType": "PRICE_ABOVE",
            "triggerPrice": 99.99,
            "createdDate": "2026-01-01",
        })
        assert t.trigger_id == "X1"
        assert t.trigger_type == "PRICE_ABOVE"
        assert t.trigger_price == 99.99
        assert t.created_date == "2026-01-01"

    def test_python_name_population(self):
        t = PriceTrigger(
            trigger_id="X2",
            trigger_type="PRICE_BELOW",
            trigger_price=50.0,
            created_date="2026-02-01",
        )
        assert t.trigger_id == "X2"
        assert t.trigger_type == "PRICE_BELOW"


# ---------------------------------------------------------------------------
# PriceTriggerSummary model
# ---------------------------------------------------------------------------

class TestPriceTriggerSummary:
    def test_is_empty_true_for_no_triggers(self):
        summary = PriceTriggerSummary(
            total_account=0, available_account=0, offset=0, triggers=[]
        )
        assert summary.is_empty is True

    def test_is_empty_false_with_triggers(self):
        trigger = PriceTrigger(symbol="QS", status="active")
        summary = PriceTriggerSummary(
            total_account=1,
            available_account=1,
            offset=0,
            triggers=[trigger],
        )
        assert summary.is_empty is False

    def test_defaults(self):
        summary = PriceTriggerSummary()
        assert summary.total_account == 0
        assert summary.available_account == 0
        assert summary.offset == 0
        assert summary.triggers == []

    def test_alias_population(self):
        summary = PriceTriggerSummary.model_validate({
            "totalAccount": 5,
            "availableAccount": 10,
            "offset": 2,
            "triggers": [],
        })
        assert summary.total_account == 5
        assert summary.available_account == 10
        assert summary.offset == 2


# ---------------------------------------------------------------------------
# PriceTriggersResponse model
# ---------------------------------------------------------------------------

class TestPriceTriggersResponse:
    def test_parses_empty_response(self):
        resp = PriceTriggersResponse.from_api_response(_EMPTY_RESPONSE)
        assert resp.price_trigger.total_account == 0
        assert resp.price_trigger.available_account == 0
        assert resp.price_trigger.offset == 0
        assert resp.price_trigger.triggers == []

    def test_is_empty_for_empty_response(self):
        resp = PriceTriggersResponse.from_api_response(_EMPTY_RESPONSE)
        assert resp.is_empty is True

    def test_parses_populated_response(self):
        resp = PriceTriggersResponse.from_api_response(_POPULATED_RESPONSE)
        assert resp.price_trigger.total_account == 3
        assert resp.price_trigger.available_account == 5
        assert len(resp.price_trigger.triggers) == 2

    def test_is_empty_false_for_populated_response(self):
        resp = PriceTriggersResponse.from_api_response(_POPULATED_RESPONSE)
        assert resp.is_empty is False

    def test_trigger_symbols_in_populated(self):
        resp = PriceTriggersResponse.from_api_response(_POPULATED_RESPONSE)
        symbols = [t.symbol for t in resp.price_trigger.triggers]
        assert symbols == ["QS", "QS"]

    def test_trigger_ids_in_populated(self):
        resp = PriceTriggersResponse.from_api_response(_POPULATED_RESPONSE)
        ids = [t.trigger_id for t in resp.price_trigger.triggers]
        assert ids == ["TRG001", "TRG002"]

    def test_missing_price_trigger_key(self):
        resp = PriceTriggersResponse.from_api_response({"other": "data"})
        assert resp.is_empty is True
        assert resp.price_trigger.total_account == 0

    def test_completely_empty_dict(self):
        resp = PriceTriggersResponse.from_api_response({})
        assert resp.is_empty is True
        assert resp.price_trigger.triggers == []

    def test_single_trigger_response(self):
        resp = PriceTriggersResponse.from_api_response(_SINGLE_TRIGGER_RESPONSE)
        assert resp.price_trigger.total_account == 1
        assert len(resp.price_trigger.triggers) == 1
        assert resp.price_trigger.triggers[0].symbol == "AAPL"
        assert resp.price_trigger.triggers[0].trigger_price == 200.00

    def test_offset_preserved(self):
        data = {
            "priceTrigger": {
                "totalAccount": 10,
                "availableAccount": 10,
                "offset": 5,
                "triggers": [],
            }
        }
        resp = PriceTriggersResponse.from_api_response(data)
        assert resp.price_trigger.offset == 5


# ---------------------------------------------------------------------------
# PriceTriggersAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestPriceTriggersAPI:
    @respx.mock
    def test_makes_correct_get_request(self):
        route = respx.get(_PRICE_TRIGGERS_URL).mock(
            return_value=httpx.Response(200, json=_EMPTY_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        result = api.get_price_triggers("QS")

        assert route.called
        assert isinstance(result, PriceTriggersResponse)

    @respx.mock
    def test_passes_symbol_param(self):
        route = respx.get(_PRICE_TRIGGERS_URL).mock(
            return_value=httpx.Response(200, json=_EMPTY_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        api.get_price_triggers("QS")

        request = route.calls[0].request
        assert "symbol=QS" in str(request.url)

    @respx.mock
    def test_passes_status_param(self):
        route = respx.get(_PRICE_TRIGGERS_URL).mock(
            return_value=httpx.Response(200, json=_EMPTY_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        api.get_price_triggers("QS", status="active")

        request = route.calls[0].request
        assert "status=active" in str(request.url)

    @respx.mock
    def test_passes_offset_param(self):
        route = respx.get(_PRICE_TRIGGERS_URL).mock(
            return_value=httpx.Response(200, json=_EMPTY_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        api.get_price_triggers("QS", offset=10)

        request = route.calls[0].request
        assert "offset=10" in str(request.url)

    @respx.mock
    def test_default_status_is_active(self):
        route = respx.get(_PRICE_TRIGGERS_URL).mock(
            return_value=httpx.Response(200, json=_EMPTY_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        api.get_price_triggers("AAPL")

        request = route.calls[0].request
        assert "status=active" in str(request.url)

    @respx.mock
    def test_default_offset_is_zero(self):
        route = respx.get(_PRICE_TRIGGERS_URL).mock(
            return_value=httpx.Response(200, json=_EMPTY_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        api.get_price_triggers("AAPL")

        request = route.calls[0].request
        assert "offset=0" in str(request.url)

    @respx.mock
    def test_returns_parsed_populated_response(self):
        respx.get(_PRICE_TRIGGERS_URL).mock(
            return_value=httpx.Response(200, json=_POPULATED_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        result = api.get_price_triggers("QS")

        assert result.price_trigger.total_account == 3
        assert len(result.price_trigger.triggers) == 2
        assert result.price_trigger.triggers[0].trigger_id == "TRG001"
        assert result.price_trigger.triggers[1].trigger_price == 5.25

    @respx.mock
    def test_raises_on_http_error(self):
        respx.get(_PRICE_TRIGGERS_URL).mock(return_value=httpx.Response(401))
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_price_triggers("QS")

    @respx.mock
    def test_raises_on_server_error(self):
        respx.get(_PRICE_TRIGGERS_URL).mock(return_value=httpx.Response(500))
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_price_triggers("AAPL")

    @respx.mock
    def test_custom_status_param(self):
        route = respx.get(_PRICE_TRIGGERS_URL).mock(
            return_value=httpx.Response(200, json=_EMPTY_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        api.get_price_triggers("QS", status="expired")

        request = route.calls[0].request
        assert "status=expired" in str(request.url)

    @respx.mock
    def test_pagination_offset(self):
        paginated = {
            "priceTrigger": {
                "totalAccount": 20,
                "availableAccount": 20,
                "offset": 10,
                "triggers": [
                    {
                        "triggerId": "TRG011",
                        "symbol": "TSLA",
                        "triggerType": "PRICE_ABOVE",
                        "triggerPrice": 300.00,
                        "status": "active",
                        "createdDate": "2026-03-25",
                    }
                ],
            }
        }
        route = respx.get(_PRICE_TRIGGERS_URL).mock(
            return_value=httpx.Response(200, json=paginated)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        result = api.get_price_triggers("TSLA", offset=10)

        request = route.calls[0].request
        assert "offset=10" in str(request.url)
        assert result.price_trigger.offset == 10
        assert result.price_trigger.total_account == 20
        assert len(result.price_trigger.triggers) == 1
        assert result.price_trigger.triggers[0].symbol == "TSLA"
