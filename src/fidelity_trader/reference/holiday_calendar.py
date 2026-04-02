import httpx

from fidelity_trader._http import DPSERVICE_URL, make_req_id
from fidelity_trader.models.holiday_calendar import HolidayCalendarResponse

_HOLIDAY_CALENDAR_PATH = "/ftgw/dpdirect/market/holidaycalendar/v1"


class HolidayCalendarAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_holidays(self, country_code: str = "US") -> HolidayCalendarResponse:
        """Fetch the market holiday calendar for the given country.

        Uses the holidaycalendar endpoint observed in captured Trader+ traffic.
        """
        params = {"countryCode": country_code}
        headers = {"fsreqid": make_req_id()}
        resp = self._http.get(
            f"{DPSERVICE_URL}{_HOLIDAY_CALENDAR_PATH}",
            params=params,
            headers=headers,
        )
        resp.raise_for_status()
        return HolidayCalendarResponse.from_api_response(resp.json())
