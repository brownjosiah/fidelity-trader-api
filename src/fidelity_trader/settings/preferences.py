"""ATN Preferences API — get, save, and delete user preferences."""

import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.preferences import PreferencesResponse


class PreferencesAPI:
    """Manage Trader+ application preferences.

    Preferences are stored as key-value pairs organized by path
    (e.g., "user/atn/global/v1" for global settings,
    "user/atn/layout/{id}/v1" for layout configurations).
    """

    _BASE = f"{DPSERVICE_URL}/ftgw/dp/retail-customers/v1/personalization/atn-prefs"

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_preferences(
        self,
        preference_path: str = "user/",
        pref_keys: list[str] | None = None,
    ) -> PreferencesResponse:
        """Fetch preferences at the given path.

        Args:
            preference_path: The preference path to query (e.g., "user/").
            pref_keys: Optional list of specific keys to retrieve.
        """
        body = {
            "preferences": [
                {
                    "prefKeys": pref_keys,
                    "preferencePath": preference_path,
                }
            ]
        }
        resp = self._http.post(f"{self._BASE}/getpreference", json=body)
        resp.raise_for_status()
        return PreferencesResponse.from_api_response(resp.json())

    def save_preferences(
        self,
        preference_path: str,
        values: dict[str, str],
    ) -> PreferencesResponse:
        """Save preference key-value pairs at the given path.

        Args:
            preference_path: Where to store (e.g., "user/atn/global/v1").
            values: Dictionary of preference keys and values to save.
        """
        body = {
            "preferences": [
                {
                    "prefValues": values,
                    "preferencePath": preference_path,
                }
            ]
        }
        resp = self._http.post(f"{self._BASE}/savepreference", json=body)
        resp.raise_for_status()
        return PreferencesResponse.from_api_response(resp.json())

    def delete_preferences(
        self,
        preference_path: str,
        pref_keys: list[str] | None = None,
    ) -> PreferencesResponse:
        """Delete preferences at the given path.

        Args:
            preference_path: The path to delete from.
            pref_keys: Specific keys to delete. If None, deletes all at path.
        """
        body = {
            "preferences": [
                {
                    "prefKeys": pref_keys,
                    "preferencePath": preference_path,
                }
            ]
        }
        resp = self._http.post(f"{self._BASE}/deletepreference", json=body)
        resp.raise_for_status()
        return PreferencesResponse.from_api_response(resp.json())
