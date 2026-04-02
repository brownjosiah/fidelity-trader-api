"""Tests for the price triggers API models and PriceTriggersAPI client."""
import json

import pytest
import httpx
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.price_trigger import (
    CreatedPriceTrigger,
    DEFAULT_DEVICES,
    PriceTrigger,
    PriceTriggerCreateRequest,
    PriceTriggerCreateResponse,
    PriceTriggerDeleteRequest,
    PriceTriggerDeleteResponse,
    PriceTriggerDevice,
    PriceTriggerSummary,
    PriceTriggersResponse,
)
from fidelity_trader.alerts.price_triggers import PriceTriggersAPI

_PRICE_TRIGGERS_BASE_URL = (
    f"{DPSERVICE_URL}/ftgw/dp/retail-price-triggers/v1"
    "/investments/research/alert/price-triggers"
)
_PRICE_TRIGGERS_URL = f"{_PRICE_TRIGGERS_BASE_URL}/list"
_PRICE_TRIGGERS_CREATE_URL = f"{_PRICE_TRIGGERS_BASE_URL}/create"
_PRICE_TRIGGERS_DELETE_URL = f"{_PRICE_TRIGGERS_BASE_URL}/delete"

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


# ---------------------------------------------------------------------------
# Create / Delete — fixtures
# ---------------------------------------------------------------------------

_CREATE_RESPONSE = {
    "triggers": [
        {
            "id": "1095172719",
            "symbol": "SPY",
            "operator": "lessThanPercent",
            "value": 4,
            "currency": "USD",
            "createTime": 1775152424015,
            "updateTime": 1775152424015,
            "devices": [
                {"name": "Active Trader Pro"},
                {"name": "Fidelity mobile applications"},
            ],
        }
    ]
}

_CREATE_MULTI_RESPONSE = {
    "triggers": [
        {
            "id": "2000000001",
            "symbol": "AAPL",
            "operator": "greaterThan",
            "value": 200.0,
            "currency": "USD",
            "createTime": 1775200000000,
            "updateTime": 1775200000000,
            "devices": [{"name": "Active Trader Pro"}],
        },
        {
            "id": "2000000002",
            "symbol": "AAPL",
            "operator": "lessThan",
            "value": 150.0,
            "currency": "USD",
            "createTime": 1775200000001,
            "updateTime": 1775200000001,
            "devices": [{"name": "Active Trader Pro"}],
        },
    ]
}

_DELETE_RESPONSE = {"status": "success"}


# ---------------------------------------------------------------------------
# PriceTriggerDevice model
# ---------------------------------------------------------------------------


class TestPriceTriggerDevice:
    def test_create_device(self):
        d = PriceTriggerDevice(name="Active Trader Pro")
        assert d.name == "Active Trader Pro"

    def test_default_devices_list(self):
        assert len(DEFAULT_DEVICES) == 2
        assert DEFAULT_DEVICES[0].name == "Active Trader Pro"
        assert DEFAULT_DEVICES[1].name == "Fidelity mobile applications"


# ---------------------------------------------------------------------------
# PriceTriggerCreateRequest model
# ---------------------------------------------------------------------------


class TestPriceTriggerCreateRequest:
    def test_basic_request(self):
        req = PriceTriggerCreateRequest(
            symbol="SPY", operator="lessThanPercent", value=4.0
        )
        assert req.symbol == "SPY"
        assert req.operator == "lessThanPercent"
        assert req.value == 4.0
        assert req.currency == "USD"
        assert req.notes == ""
        assert len(req.devices) == 2

    def test_to_api_payload_shape(self):
        req = PriceTriggerCreateRequest(
            symbol="SPY", operator="lessThanPercent", value=4.0
        )
        payload = req.to_api_payload()
        assert "triggers" in payload
        assert "devices" in payload
        assert len(payload["triggers"]) == 1
        trigger = payload["triggers"][0]
        assert trigger["symbol"] == "SPY"
        assert trigger["operator"] == "lessThanPercent"
        assert trigger["value"] == 4.0
        assert trigger["currency"] == "USD"
        assert trigger["notes"] == ""

    def test_to_api_payload_devices_default(self):
        req = PriceTriggerCreateRequest(
            symbol="SPY", operator="lessThanPercent", value=4.0
        )
        payload = req.to_api_payload()
        assert payload["devices"] == [
            {"name": "Active Trader Pro"},
            {"name": "Fidelity mobile applications"},
        ]

    def test_to_api_payload_custom_devices(self):
        devices = [PriceTriggerDevice(name="Custom App")]
        req = PriceTriggerCreateRequest(
            symbol="SPY", operator="greaterThan", value=500.0, devices=devices
        )
        payload = req.to_api_payload()
        assert payload["devices"] == [{"name": "Custom App"}]

    def test_to_api_payload_with_notes(self):
        req = PriceTriggerCreateRequest(
            symbol="AAPL", operator="greaterThan", value=200.0, notes="Watch this"
        )
        payload = req.to_api_payload()
        assert payload["triggers"][0]["notes"] == "Watch this"

    def test_operator_less_than_percent(self):
        req = PriceTriggerCreateRequest(
            symbol="SPY", operator="lessThanPercent", value=5.0
        )
        assert req.to_api_payload()["triggers"][0]["operator"] == "lessThanPercent"

    def test_operator_greater_than_percent(self):
        req = PriceTriggerCreateRequest(
            symbol="SPY", operator="greaterThanPercent", value=5.0
        )
        assert req.to_api_payload()["triggers"][0]["operator"] == "greaterThanPercent"

    def test_operator_less_than(self):
        req = PriceTriggerCreateRequest(
            symbol="QQQ", operator="lessThan", value=300.0
        )
        assert req.to_api_payload()["triggers"][0]["operator"] == "lessThan"

    def test_operator_greater_than(self):
        req = PriceTriggerCreateRequest(
            symbol="QQQ", operator="greaterThan", value=500.0
        )
        assert req.to_api_payload()["triggers"][0]["operator"] == "greaterThan"


# ---------------------------------------------------------------------------
# CreatedPriceTrigger model
# ---------------------------------------------------------------------------


class TestCreatedPriceTrigger:
    def test_parse_from_api(self):
        raw = _CREATE_RESPONSE["triggers"][0]
        t = CreatedPriceTrigger.model_validate(raw)
        assert t.id == "1095172719"
        assert t.symbol == "SPY"
        assert t.operator == "lessThanPercent"
        assert t.value == 4
        assert t.currency == "USD"
        assert t.create_time == 1775152424015
        assert t.update_time == 1775152424015
        assert len(t.devices) == 2

    def test_devices_parsed(self):
        raw = _CREATE_RESPONSE["triggers"][0]
        t = CreatedPriceTrigger.model_validate(raw)
        names = [d.name for d in t.devices]
        assert "Active Trader Pro" in names
        assert "Fidelity mobile applications" in names


# ---------------------------------------------------------------------------
# PriceTriggerCreateResponse model
# ---------------------------------------------------------------------------


class TestPriceTriggerCreateResponse:
    def test_from_api_response(self):
        resp = PriceTriggerCreateResponse.from_api_response(_CREATE_RESPONSE)
        assert len(resp.triggers) == 1
        assert resp.triggers[0].id == "1095172719"
        assert resp.triggers[0].symbol == "SPY"

    def test_from_api_response_multi(self):
        resp = PriceTriggerCreateResponse.from_api_response(_CREATE_MULTI_RESPONSE)
        assert len(resp.triggers) == 2
        assert resp.triggers[0].id == "2000000001"
        assert resp.triggers[1].id == "2000000002"

    def test_from_api_response_empty(self):
        resp = PriceTriggerCreateResponse.from_api_response({})
        assert resp.triggers == []

    def test_from_api_response_empty_triggers_list(self):
        resp = PriceTriggerCreateResponse.from_api_response({"triggers": []})
        assert resp.triggers == []


# ---------------------------------------------------------------------------
# PriceTriggerDeleteRequest model
# ---------------------------------------------------------------------------


class TestPriceTriggerDeleteRequest:
    def test_single_id_payload(self):
        req = PriceTriggerDeleteRequest(trigger_ids=["1095172719"])
        payload = req.to_api_payload()
        assert payload == {"triggers": [{"id": "1095172719"}]}

    def test_multiple_ids_payload(self):
        req = PriceTriggerDeleteRequest(trigger_ids=["AAA", "BBB", "CCC"])
        payload = req.to_api_payload()
        assert len(payload["triggers"]) == 3
        assert payload["triggers"][0] == {"id": "AAA"}
        assert payload["triggers"][1] == {"id": "BBB"}
        assert payload["triggers"][2] == {"id": "CCC"}


# ---------------------------------------------------------------------------
# PriceTriggerDeleteResponse model
# ---------------------------------------------------------------------------


class TestPriceTriggerDeleteResponse:
    def test_from_api_response(self):
        resp = PriceTriggerDeleteResponse.from_api_response({"status": "ok"})
        assert resp.raw == {"status": "ok"}

    def test_from_api_response_empty(self):
        resp = PriceTriggerDeleteResponse.from_api_response({})
        assert resp.raw == {}


# ---------------------------------------------------------------------------
# PriceTrigger model — new fields
# ---------------------------------------------------------------------------


class TestPriceTriggerNewFields:
    def test_new_fields_from_create_shape(self):
        t = PriceTrigger.model_validate({
            "id": "1095172719",
            "symbol": "SPY",
            "operator": "lessThanPercent",
            "value": 4,
            "currency": "USD",
            "createTime": 1775152424015,
            "updateTime": 1775152424015,
            "devices": [{"name": "Active Trader Pro"}],
        })
        assert t.id == "1095172719"
        assert t.operator == "lessThanPercent"
        assert t.value == 4
        assert t.currency == "USD"
        assert t.create_time == 1775152424015
        assert t.update_time == 1775152424015
        assert len(t.devices) == 1

    def test_new_fields_default_none(self):
        t = PriceTrigger.model_validate({})
        assert t.id is None
        assert t.operator is None
        assert t.value is None
        assert t.currency is None
        assert t.create_time is None
        assert t.update_time is None
        assert t.devices is None


# ---------------------------------------------------------------------------
# PriceTriggersAPI — create (mocked)
# ---------------------------------------------------------------------------


class TestPriceTriggersAPICreate:
    @respx.mock
    def test_create_posts_to_correct_url(self):
        route = respx.post(_PRICE_TRIGGERS_CREATE_URL).mock(
            return_value=httpx.Response(200, json=_CREATE_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        api.create_price_trigger("SPY", "lessThanPercent", 4.0)
        assert route.called

    @respx.mock
    def test_create_sends_correct_body(self):
        route = respx.post(_PRICE_TRIGGERS_CREATE_URL).mock(
            return_value=httpx.Response(200, json=_CREATE_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        api.create_price_trigger("SPY", "lessThanPercent", 4.0)

        request = route.calls[0].request
        body = json.loads(request.content)
        assert body["triggers"][0]["symbol"] == "SPY"
        assert body["triggers"][0]["operator"] == "lessThanPercent"
        assert body["triggers"][0]["value"] == 4.0
        assert body["triggers"][0]["currency"] == "USD"
        assert body["triggers"][0]["notes"] == ""

    @respx.mock
    def test_create_default_devices_in_body(self):
        route = respx.post(_PRICE_TRIGGERS_CREATE_URL).mock(
            return_value=httpx.Response(200, json=_CREATE_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        api.create_price_trigger("SPY", "lessThanPercent", 4.0)

        body = json.loads(route.calls[0].request.content)
        assert body["devices"] == [
            {"name": "Active Trader Pro"},
            {"name": "Fidelity mobile applications"},
        ]

    @respx.mock
    def test_create_custom_devices(self):
        route = respx.post(_PRICE_TRIGGERS_CREATE_URL).mock(
            return_value=httpx.Response(200, json=_CREATE_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        devices = [PriceTriggerDevice(name="Custom")]
        api.create_price_trigger("SPY", "lessThanPercent", 4.0, devices=devices)

        body = json.loads(route.calls[0].request.content)
        assert body["devices"] == [{"name": "Custom"}]

    @respx.mock
    def test_create_returns_parsed_response(self):
        respx.post(_PRICE_TRIGGERS_CREATE_URL).mock(
            return_value=httpx.Response(200, json=_CREATE_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        result = api.create_price_trigger("SPY", "lessThanPercent", 4.0)

        assert isinstance(result, PriceTriggerCreateResponse)
        assert len(result.triggers) == 1
        assert result.triggers[0].id == "1095172719"
        assert result.triggers[0].symbol == "SPY"
        assert result.triggers[0].operator == "lessThanPercent"
        assert result.triggers[0].value == 4

    @respx.mock
    def test_create_with_notes(self):
        route = respx.post(_PRICE_TRIGGERS_CREATE_URL).mock(
            return_value=httpx.Response(200, json=_CREATE_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        api.create_price_trigger("SPY", "greaterThan", 500.0, notes="earnings play")

        body = json.loads(route.calls[0].request.content)
        assert body["triggers"][0]["notes"] == "earnings play"

    @respx.mock
    def test_create_raises_on_http_error(self):
        respx.post(_PRICE_TRIGGERS_CREATE_URL).mock(
            return_value=httpx.Response(401)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.create_price_trigger("SPY", "lessThanPercent", 4.0)

    @respx.mock
    def test_create_raises_on_server_error(self):
        respx.post(_PRICE_TRIGGERS_CREATE_URL).mock(
            return_value=httpx.Response(500)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.create_price_trigger("AAPL", "greaterThan", 200.0)

    @respx.mock
    def test_create_greater_than_percent_operator(self):
        route = respx.post(_PRICE_TRIGGERS_CREATE_URL).mock(
            return_value=httpx.Response(200, json=_CREATE_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        api.create_price_trigger("SPY", "greaterThanPercent", 5.0)

        body = json.loads(route.calls[0].request.content)
        assert body["triggers"][0]["operator"] == "greaterThanPercent"

    @respx.mock
    def test_create_less_than_operator(self):
        route = respx.post(_PRICE_TRIGGERS_CREATE_URL).mock(
            return_value=httpx.Response(200, json=_CREATE_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        api.create_price_trigger("QQQ", "lessThan", 300.0)

        body = json.loads(route.calls[0].request.content)
        assert body["triggers"][0]["operator"] == "lessThan"
        assert body["triggers"][0]["symbol"] == "QQQ"

    @respx.mock
    def test_create_greater_than_operator(self):
        route = respx.post(_PRICE_TRIGGERS_CREATE_URL).mock(
            return_value=httpx.Response(200, json=_CREATE_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        api.create_price_trigger("TSLA", "greaterThan", 250.0)

        body = json.loads(route.calls[0].request.content)
        assert body["triggers"][0]["operator"] == "greaterThan"
        assert body["triggers"][0]["symbol"] == "TSLA"


# ---------------------------------------------------------------------------
# PriceTriggersAPI — delete (mocked)
# ---------------------------------------------------------------------------


class TestPriceTriggersAPIDelete:
    @respx.mock
    def test_delete_posts_to_correct_url(self):
        route = respx.post(_PRICE_TRIGGERS_DELETE_URL).mock(
            return_value=httpx.Response(200, json=_DELETE_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        api.delete_price_triggers(["1095172719"])
        assert route.called

    @respx.mock
    def test_delete_sends_trigger_ids(self):
        route = respx.post(_PRICE_TRIGGERS_DELETE_URL).mock(
            return_value=httpx.Response(200, json=_DELETE_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        api.delete_price_triggers(["AAA", "BBB"])

        body = json.loads(route.calls[0].request.content)
        assert body == {"triggers": [{"id": "AAA"}, {"id": "BBB"}]}

    @respx.mock
    def test_delete_returns_parsed_response(self):
        respx.post(_PRICE_TRIGGERS_DELETE_URL).mock(
            return_value=httpx.Response(200, json=_DELETE_RESPONSE)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        result = api.delete_price_triggers(["1095172719"])

        assert isinstance(result, PriceTriggerDeleteResponse)
        assert result.raw == _DELETE_RESPONSE

    @respx.mock
    def test_delete_raises_on_http_error(self):
        respx.post(_PRICE_TRIGGERS_DELETE_URL).mock(
            return_value=httpx.Response(401)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.delete_price_triggers(["1095172719"])

    @respx.mock
    def test_delete_raises_on_server_error(self):
        respx.post(_PRICE_TRIGGERS_DELETE_URL).mock(
            return_value=httpx.Response(500)
        )
        client = httpx.Client()
        api = PriceTriggersAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.delete_price_triggers(["1095172719"])
