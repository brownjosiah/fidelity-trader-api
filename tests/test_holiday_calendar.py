"""Tests for the holiday calendar API models and HolidayCalendarAPI client."""
import pytest
import httpx
import respx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.holiday_calendar import (
    HolidayDetail,
    HolidayCalendarResponse,
)
from fidelity_trader.reference.holiday_calendar import HolidayCalendarAPI

_HOLIDAY_URL = f"{DPSERVICE_URL}/ftgw/dpdirect/market/holidaycalendar/v1"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_full_holiday(
    country_code: str = "US",
    date: int = 1735707600,
    holiday_desc: str = "New Year's Day",
) -> dict:
    return {
        "countryCode": country_code,
        "date": date,
        "holidayDesc": holiday_desc,
        "holidayType": "H",
    }


def _make_abbreviated_holiday(
    country_code: str = "US",
    date: int = 1751515200,
    holiday_desc: str = "Abbreviated Trading",
    early_close_tm: str = "13:00:00.000",
) -> dict:
    return {
        "countryCode": country_code,
        "date": date,
        "holidayDesc": holiday_desc,
        "holidayType": "A",
        "earlyCloseTm": early_close_tm,
    }


def _make_holiday_response(details: list[dict] | None = None) -> dict:
    if details is None:
        details = [_make_full_holiday()]
    return {"holidayCalendarDetails": details}


# ---------------------------------------------------------------------------
# HolidayDetail — full holiday
# ---------------------------------------------------------------------------

class TestHolidayDetailFullHoliday:
    def test_parses_all_fields(self):
        h = HolidayDetail.model_validate(_make_full_holiday())
        assert h.country_code == "US"
        assert h.date == 1735707600
        assert h.holiday_desc == "New Year's Day"
        assert h.holiday_type == "H"
        assert h.early_close_tm is None

    def test_is_full_holiday(self):
        h = HolidayDetail.model_validate(_make_full_holiday())
        assert h.is_full_holiday is True

    def test_is_not_abbreviated(self):
        h = HolidayDetail.model_validate(_make_full_holiday())
        assert h.is_abbreviated is False

    def test_date_str(self):
        h = HolidayDetail.model_validate(_make_full_holiday())
        assert h.date_str == "2025-01-01"


# ---------------------------------------------------------------------------
# HolidayDetail — abbreviated trading
# ---------------------------------------------------------------------------

class TestHolidayDetailAbbreviated:
    def test_parses_all_fields(self):
        h = HolidayDetail.model_validate(_make_abbreviated_holiday())
        assert h.country_code == "US"
        assert h.date == 1751515200
        assert h.holiday_desc == "Abbreviated Trading"
        assert h.holiday_type == "A"
        assert h.early_close_tm == "13:00:00.000"

    def test_is_abbreviated(self):
        h = HolidayDetail.model_validate(_make_abbreviated_holiday())
        assert h.is_abbreviated is True

    def test_is_not_full_holiday(self):
        h = HolidayDetail.model_validate(_make_abbreviated_holiday())
        assert h.is_full_holiday is False

    def test_date_str(self):
        h = HolidayDetail.model_validate(_make_abbreviated_holiday())
        assert h.date_str == "2025-07-03"


# ---------------------------------------------------------------------------
# HolidayDetail — other scenarios
# ---------------------------------------------------------------------------

class TestHolidayDetailEdgeCases:
    def test_thanksgiving_with_trailing_spaces(self):
        """The captured response had trailing whitespace in holidayDesc."""
        raw = {
            "countryCode": "US",
            "date": 1764219600,
            "holidayDesc": "Thanksgiving Day    ",
            "holidayType": "H",
        }
        h = HolidayDetail.model_validate(raw)
        assert h.holiday_desc == "Thanksgiving Day    "
        assert h.is_full_holiday is True
        assert h.date_str == "2025-11-27"

    def test_non_us_country_code(self):
        h = HolidayDetail.model_validate(_make_full_holiday(country_code="GB"))
        assert h.country_code == "GB"

    def test_populate_by_name(self):
        """Model accepts both camelCase aliases and snake_case names."""
        h = HolidayDetail(
            country_code="US",
            date=1735707600,
            holiday_desc="New Year's Day",
            holiday_type="H",
        )
        assert h.country_code == "US"
        assert h.holiday_type == "H"


# ---------------------------------------------------------------------------
# HolidayCalendarResponse
# ---------------------------------------------------------------------------

class TestHolidayCalendarResponse:
    def test_from_api_response_single_holiday(self):
        raw = _make_holiday_response()
        resp = HolidayCalendarResponse.from_api_response(raw)
        assert len(resp.holidays) == 1
        assert resp.holidays[0].holiday_desc == "New Year's Day"

    def test_from_api_response_multiple_holidays(self):
        details = [
            _make_full_holiday(),
            _make_abbreviated_holiday(),
            _make_full_holiday(
                date=1764219600,
                holiday_desc="Thanksgiving Day    ",
            ),
        ]
        resp = HolidayCalendarResponse.from_api_response(
            _make_holiday_response(details)
        )
        assert len(resp.holidays) == 3
        assert resp.holidays[0].is_full_holiday is True
        assert resp.holidays[1].is_abbreviated is True
        assert resp.holidays[2].holiday_desc == "Thanksgiving Day    "

    def test_from_api_response_empty_list(self):
        raw = {"holidayCalendarDetails": []}
        resp = HolidayCalendarResponse.from_api_response(raw)
        assert resp.holidays == []

    def test_from_api_response_missing_key(self):
        resp = HolidayCalendarResponse.from_api_response({})
        assert resp.holidays == []

    def test_from_api_response_null_value(self):
        raw = {"holidayCalendarDetails": None}
        resp = HolidayCalendarResponse.from_api_response(raw)
        assert resp.holidays == []


# ---------------------------------------------------------------------------
# HolidayCalendarAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestHolidayCalendarAPI:
    @respx.mock
    def test_get_holidays_makes_correct_request(self):
        raw = _make_holiday_response()
        route = respx.get(_HOLIDAY_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = HolidayCalendarAPI(client)
        result = api.get_holidays()

        assert route.called
        assert isinstance(result, HolidayCalendarResponse)

    @respx.mock
    def test_get_holidays_sends_country_code_param(self):
        raw = _make_holiday_response()
        route = respx.get(_HOLIDAY_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = HolidayCalendarAPI(client)
        api.get_holidays("US")

        request = route.calls[0].request
        assert "countryCode=US" in str(request.url)

    @respx.mock
    def test_get_holidays_custom_country_code(self):
        raw = _make_holiday_response([_make_full_holiday(country_code="GB")])
        route = respx.get(_HOLIDAY_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = HolidayCalendarAPI(client)
        api.get_holidays("GB")

        request = route.calls[0].request
        assert "countryCode=GB" in str(request.url)

    @respx.mock
    def test_get_holidays_includes_fsreqid_header(self):
        raw = _make_holiday_response()
        route = respx.get(_HOLIDAY_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = HolidayCalendarAPI(client)
        api.get_holidays()

        request = route.calls[0].request
        assert "fsreqid" in request.headers
        assert request.headers["fsreqid"].startswith("REQ")

    @respx.mock
    def test_get_holidays_raises_on_http_error(self):
        respx.get(_HOLIDAY_URL).mock(return_value=httpx.Response(401))
        client = httpx.Client()
        api = HolidayCalendarAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_holidays()

    @respx.mock
    def test_get_holidays_parses_full_response(self):
        details = [
            _make_full_holiday(),
            _make_abbreviated_holiday(),
            _make_full_holiday(
                date=1764219600,
                holiday_desc="Thanksgiving Day    ",
            ),
        ]
        raw = _make_holiday_response(details)
        respx.get(_HOLIDAY_URL).mock(return_value=httpx.Response(200, json=raw))
        client = httpx.Client()
        api = HolidayCalendarAPI(client)
        result = api.get_holidays()

        assert len(result.holidays) == 3
        assert result.holidays[0].is_full_holiday is True
        assert result.holidays[0].date_str == "2025-01-01"
        assert result.holidays[1].is_abbreviated is True
        assert result.holidays[1].early_close_tm == "13:00:00.000"
        assert result.holidays[2].holiday_desc == "Thanksgiving Day    "

    @respx.mock
    def test_get_holidays_empty_response(self):
        raw = {"holidayCalendarDetails": []}
        respx.get(_HOLIDAY_URL).mock(return_value=httpx.Response(200, json=raw))
        client = httpx.Client()
        api = HolidayCalendarAPI(client)
        result = api.get_holidays()

        assert result.holidays == []

    @respx.mock
    def test_get_holidays_default_country_code_is_us(self):
        raw = _make_holiday_response()
        route = respx.get(_HOLIDAY_URL).mock(
            return_value=httpx.Response(200, json=raw)
        )
        client = httpx.Client()
        api = HolidayCalendarAPI(client)
        api.get_holidays()

        request = route.calls[0].request
        assert "countryCode=US" in str(request.url)
