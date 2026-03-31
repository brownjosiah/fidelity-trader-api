import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.closed_position import ClosedPositionsResponse

_ENDPOINT = (
    f"{DPSERVICE_URL}/ftgw/dp/customer-am-position/v1/accounts/closedposition"
)


class ClosedPositionsAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_closed_positions(
        self,
        account_numbers: list[str],
        start_date: str,
        end_date: str,
        date_type: str = "YTD",
        exclude_wash_sales: bool = False,
        retirement_flags: dict[str, bool] = None,
    ) -> ClosedPositionsResponse:
        """Fetch closed positions for the given accounts.

        Parameters
        ----------
        account_numbers:
            List of account number strings.
        start_date:
            ISO-format start date, e.g. ``"2026-01-01"``.
        end_date:
            ISO-format end date, e.g. ``"2026-03-30"``.
        date_type:
            Date range type label sent to the API (default ``"YTD"``).
        exclude_wash_sales:
            Whether to exclude wash-sale adjustments (default ``False``).
        retirement_flags:
            Optional mapping of ``{acctNum: isRetirementAcct}``.  When not
            provided every account defaults to ``False``.
        """
        if retirement_flags is None:
            retirement_flags = {}

        acct_details = [
            {
                "acctNum": num,
                "isRetirementAcct": retirement_flags.get(num, False),
            }
            for num in account_numbers
        ]

        body = {
            "request": {
                "parameters": {
                    "acctDetails": acct_details,
                    "startDate": start_date,
                    "endDate": end_date,
                    "taxYear": None,
                    "dateType": date_type,
                    "isExcludeWashSales": exclude_wash_sales,
                }
            }
        }

        resp = self._http.post(_ENDPOINT, json=body)
        resp.raise_for_status()
        return ClosedPositionsResponse.from_api_response(resp.json())
