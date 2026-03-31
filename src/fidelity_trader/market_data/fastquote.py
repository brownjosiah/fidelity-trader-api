"""FastQuote API client for option chain and depth-of-market data.

Endpoints are on fastquote.fidelity.com and return XML responses.
Traffic captured from Fidelity Trader+ desktop application.
"""

from __future__ import annotations

import httpx

from fidelity_trader._http import FASTQUOTE_URL
from fidelity_trader.models.fastquote import OptionChainResponse, MontageResponse

_CHAIN_LITE_PATH = "/service/quote/chainLite"
_DTMONTAGE_PATH = "/service/quote/dtmontage"


class FastQuoteAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_option_chain(self, symbol: str) -> OptionChainResponse:
        """Fetch the options chain for the given underlying symbol.

        Calls the chainLite endpoint observed in captured Trader+ traffic.
        The response is XML and is parsed into an OptionChainResponse.
        """
        params = {"productid": "atn", "symbols": symbol}
        resp = self._http.get(
            f"{FASTQUOTE_URL}{_CHAIN_LITE_PATH}",
            params=params,
        )
        resp.raise_for_status()
        return OptionChainResponse.parse(resp.text)

    def get_montage(self, option_symbol: str) -> MontageResponse:
        """Fetch depth-of-market (exchange-level) quotes for a single option symbol.

        Calls the dtmontage endpoint observed in captured Trader+ traffic.
        The response can be XML or JSON.
        """
        params = {"symbols": option_symbol, "productid": "atn"}
        resp = self._http.get(
            f"{FASTQUOTE_URL}{_DTMONTAGE_PATH}",
            params=params,
        )
        resp.raise_for_status()
        return MontageResponse.parse(resp.text)
