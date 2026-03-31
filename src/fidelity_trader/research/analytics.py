import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.analytics import AnalyticsResponse

_ANALYTICS_PATH = "/ftgw/dp/research/option/positions/analytics/v1"


class OptionAnalyticsAPI:
    """Client for the option position analytics endpoint.

    Matches the POST request observed in captured Fidelity Trader+ traffic:
    POST https://dpservice.fidelity.com/ftgw/dp/research/option/positions/analytics/v1
    """

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def analyze_position(
        self,
        underlying_symbol: str,
        legs: list[dict],
        volatility_period: str = "90",
        eval_at_expiry: bool = True,
    ) -> AnalyticsResponse:
        """Analyze an option position (one or more legs).

        Args:
            underlying_symbol: The ticker of the underlying equity (e.g. "QS").
            legs: List of leg dicts, each with keys:
                  symbol (str), qty (int), price (float), equity (bool).
            volatility_period: Historical volatility period in days (default "90").
            eval_at_expiry: Whether to evaluate at expiry (default True).

        Returns:
            An AnalyticsResponse containing per-evaluation-date analytics.
        """
        payload = {
            "underlyingSymbol": underlying_symbol,
            "posDetails": [legs],
            "hvDetail": {"volatilityPeriod": volatility_period},
            "evalDaysDetail": {"evalAtExpiry": eval_at_expiry},
        }
        resp = self._http.post(
            f"{DPSERVICE_URL}{_ANALYTICS_PATH}",
            json=payload,
        )
        resp.raise_for_status()
        return AnalyticsResponse.from_api_response(resp.json())
