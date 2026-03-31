import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.tax_lot import TaxLotResponse


class TaxLotAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_tax_lots(
        self,
        account_number: str,
        symbol: str,
        holding_type: str = "_1",
    ) -> TaxLotResponse:
        """Fetch tax lot details for a specific symbol in an account.

        account_number: the Fidelity account number (e.g. "Z25485019").
        symbol: the ticker symbol to look up (e.g. "LGVN").
        holding_type: holdingTypeCode sent in the request body (default "_1").
        """
        body = {
            "holdingTypeCode": holding_type,
            "acctNum": account_number,
            "securityDetail": {"symbol": symbol},
        }

        resp = self._http.post(
            f"{DPSERVICE_URL}/ftgw/dp/orderentry/taxlot/v1",
            json=body,
        )
        resp.raise_for_status()
        return TaxLotResponse.from_api_response(resp.json())
