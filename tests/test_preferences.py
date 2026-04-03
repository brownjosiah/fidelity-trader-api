"""Tests for the ATN preferences API."""

import json

import httpx
import respx

from fidelity_trader.settings.preferences import PreferencesAPI
from fidelity_trader.models.preferences import (
    PreferencesResponse,
    PreferenceData,
    SystemMessage,
)
from fidelity_trader._http import DPSERVICE_URL


BASE = f"{DPSERVICE_URL}/ftgw/dp/retail-customers/v1/personalization/atn-prefs"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_success_response(preference_data=None):
    return {
        "sysMsgs": {
            "sysMsg": [
                {
                    "message": "Successful table query",
                    "detail": "",
                    "source": "AP159679",
                    "code": "00000",
                    "type": "",
                }
            ]
        },
        "preferenceData": preference_data or [],
    }


def _make_preference_data(path="user/atn/global/v1", data=None):
    return {
        "preferencePath": path,
        "data": data or [{"DefaultAccountNumber": "250357290", "lastUpdatedBy": "AP149323"}],
    }


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestSystemMessage:
    def test_parse(self):
        msg = SystemMessage.model_validate({
            "message": "Successful table query",
            "source": "AP159679",
            "code": "00000",
        })
        assert msg.message == "Successful table query"
        assert msg.source == "AP159679"

    def test_defaults(self):
        msg = SystemMessage.model_validate({})
        assert msg.message == ""


class TestPreferenceData:
    def test_parse(self):
        pd = PreferenceData.model_validate({
            "preferencePath": "user/atn/global/v1",
            "data": [{"key": "value"}],
        })
        assert pd.preference_path == "user/atn/global/v1"
        assert len(pd.data) == 1

    def test_empty(self):
        pd = PreferenceData.model_validate({})
        assert pd.preference_path == ""
        assert pd.data == []


class TestPreferencesResponse:
    def test_from_api_response(self):
        data = _make_success_response([_make_preference_data()])
        resp = PreferencesResponse.from_api_response(data)
        assert len(resp.sys_msgs) == 1
        assert resp.sys_msgs[0].message == "Successful table query"
        assert len(resp.preference_data) == 1
        assert resp.preference_data[0].preference_path == "user/atn/global/v1"

    def test_is_success_true(self):
        resp = PreferencesResponse.from_api_response(_make_success_response())
        assert resp.is_success is True

    def test_is_success_false_on_error(self):
        data = {
            "sysMsgs": {"sysMsg": [{"message": "Error occurred", "code": "99999"}]},
            "preferenceData": [],
        }
        resp = PreferencesResponse.from_api_response(data)
        assert resp.is_success is False

    def test_empty_response(self):
        resp = PreferencesResponse.from_api_response({})
        assert resp.sys_msgs == []
        assert resp.preference_data == []

    def test_update_success_message(self):
        data = {
            "sysMsgs": {"sysMsg": [{"message": "Successful table update"}]},
            "preferenceData": [],
        }
        resp = PreferencesResponse.from_api_response(data)
        assert resp.is_success is True

    def test_multiple_preference_paths(self):
        data = _make_success_response([
            _make_preference_data("user/atn/global/v1"),
            _make_preference_data("user/atn/layout/abc/v1"),
        ])
        resp = PreferencesResponse.from_api_response(data)
        assert len(resp.preference_data) == 2


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

class TestPreferencesAPI:
    @respx.mock
    def test_get_preferences(self):
        route = respx.post(f"{BASE}/getpreference").mock(
            return_value=httpx.Response(200, json=_make_success_response([
                _make_preference_data()
            ]))
        )

        api = PreferencesAPI(httpx.Client())
        try:
            result = api.get_preferences("user/")
        finally:
            api._http.close()

        assert isinstance(result, PreferencesResponse)
        assert result.is_success is True
        body = json.loads(route.calls[0].request.content)
        assert body["preferences"][0]["preferencePath"] == "user/"
        assert body["preferences"][0]["prefKeys"] is None

    @respx.mock
    def test_get_preferences_with_keys(self):
        route = respx.post(f"{BASE}/getpreference").mock(
            return_value=httpx.Response(200, json=_make_success_response())
        )

        api = PreferencesAPI(httpx.Client())
        try:
            api.get_preferences("user/atn/global/v1", pref_keys=["DefaultAccountNumber"])
        finally:
            api._http.close()

        body = json.loads(route.calls[0].request.content)
        assert body["preferences"][0]["prefKeys"] == ["DefaultAccountNumber"]

    @respx.mock
    def test_save_preferences(self):
        route = respx.post(f"{BASE}/savepreference").mock(
            return_value=httpx.Response(200, json={
                "sysMsgs": {"sysMsg": [{"message": "Successful table update"}]},
                "preferenceData": [],
            })
        )

        api = PreferencesAPI(httpx.Client())
        try:
            result = api.save_preferences(
                "user/atn/global/v1",
                {"DefaultAccountNumber": "Z12345678"},
            )
        finally:
            api._http.close()

        assert result.is_success is True
        body = json.loads(route.calls[0].request.content)
        assert body["preferences"][0]["prefValues"] == {"DefaultAccountNumber": "Z12345678"}
        assert body["preferences"][0]["preferencePath"] == "user/atn/global/v1"

    @respx.mock
    def test_delete_preferences(self):
        route = respx.post(f"{BASE}/deletepreference").mock(
            return_value=httpx.Response(200, json={
                "sysMsgs": {"sysMsg": [{"message": "Successful table update"}]},
                "preferenceData": [],
            })
        )

        api = PreferencesAPI(httpx.Client())
        try:
            result = api.delete_preferences("user/atn/layout/abc")
        finally:
            api._http.close()

        assert result.is_success is True
        body = json.loads(route.calls[0].request.content)
        assert body["preferences"][0]["preferencePath"] == "user/atn/layout/abc"
        assert body["preferences"][0]["prefKeys"] is None

    @respx.mock
    def test_delete_preferences_with_keys(self):
        route = respx.post(f"{BASE}/deletepreference").mock(
            return_value=httpx.Response(200, json=_make_success_response())
        )

        api = PreferencesAPI(httpx.Client())
        try:
            api.delete_preferences("user/atn/layout/abc/v1", pref_keys=["NavBarPosition"])
        finally:
            api._http.close()

        body = json.loads(route.calls[0].request.content)
        assert body["preferences"][0]["prefKeys"] == ["NavBarPosition"]
