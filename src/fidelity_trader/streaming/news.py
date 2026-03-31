import httpx

from fidelity_trader._http import STREAMING_NEWS_URL
from fidelity_trader.models.streaming import StreamingAuthResponse

_AUTHORIZE_PATH = "/ftgw/snaz/Authorize"


class StreamingNewsAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def authorize(self) -> StreamingAuthResponse:
        """Authorize streaming news access.

        POSTs to the streaming news authorize endpoint with an empty body,
        matching the request format observed in captured Trader+ traffic.
        Returns connection details and an access token for the news stream.
        """
        resp = self._http.post(
            f"{STREAMING_NEWS_URL}{_AUTHORIZE_PATH}",
            content=b"",
        )
        resp.raise_for_status()
        return StreamingAuthResponse.model_validate(resp.json())
