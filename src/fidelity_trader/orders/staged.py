"""Staged/saved orders retrieval API, mirroring Fidelity Trader+ traffic."""
import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.staged_order import StagedOrdersResponse

_STAGED_ORDER_PATH = (
    "/ftgw/dp/ent-research-staging/v1/customers/staged-order/get"
)


class StagedOrderAPI:
    """Client for retrieving staged (saved) orders.

    POSTs to the staged-order endpoint with a JSON body specifying the
    ``stageType`` and optional ``stageIds`` filter.
    """

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    @staticmethod
    def build_request_body(
        stage_type: str = "saveD_ORDER",
        stage_ids: list[str] | None = None,
    ) -> dict:
        """Construct the JSON request body matching captured traffic."""
        return {
            "stagedOrders": [
                {
                    "stageType": stage_type,
                    "stageIds": stage_ids if stage_ids is not None else [],
                }
            ]
        }

    def get_staged_orders(
        self,
        stage_type: str = "saveD_ORDER",
        stage_ids: list[str] | None = None,
    ) -> StagedOrdersResponse:
        """Retrieve staged/saved orders.

        Parameters
        ----------
        stage_type:
            The type of staged order to query.  Defaults to ``"saveD_ORDER"``
            (the casing observed in captured traffic).
        stage_ids:
            Optional list of specific stage IDs to retrieve.  When *None* or
            empty, all staged orders of the given type are returned.

        Returns
        -------
        StagedOrdersResponse
            Parsed response.  Use :attr:`~StagedOrdersResponse.is_empty` to
            check whether any orders were returned.

        Raises
        ------
        httpx.HTTPStatusError
            If the server returns a non-2xx status.
        """
        body = self.build_request_body(stage_type=stage_type, stage_ids=stage_ids)
        resp = self._http.post(
            f"{DPSERVICE_URL}{_STAGED_ORDER_PATH}", json=body
        )
        resp.raise_for_status()
        return StagedOrdersResponse.from_api_response(resp.json())
