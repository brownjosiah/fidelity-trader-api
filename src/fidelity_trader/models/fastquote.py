"""Models for fastquote option chain and depth-of-market (montage) responses.

Responses from fastquote.fidelity.com are XML; these dataclasses represent
the parsed data after xml.etree.ElementTree processing.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field


@dataclass
class ChainOption:
    """A single option contract entry within an expiration group."""

    symbol: str          # OCC symbol, e.g. "-QS260402C3"
    contract_symbol: str  # Underlying / contract symbol, e.g. "QS"
    strike: float
    expiry_type: str     # "W" = weekly, "M" = monthly

    @classmethod
    def from_element(cls, elem: ET.Element) -> "ChainOption":
        return cls(
            symbol=elem.get("s", ""),
            contract_symbol=elem.get("cs", ""),
            strike=float(elem.get("st", "0")),
            expiry_type=elem.get("et", ""),
        )


@dataclass
class ChainExpiration:
    """A group of option contracts sharing an expiration date."""

    date: str                        # e.g. "2026-04-02"
    options: list[ChainOption] = field(default_factory=list)

    @classmethod
    def from_element(cls, elem: ET.Element) -> "ChainExpiration":
        date = elem.get("dt", "")
        options = [ChainOption.from_element(o) for o in elem.findall("O")]
        return cls(date=date, options=options)


@dataclass
class OptionChainResponse:
    """Parsed response from the chainLite endpoint."""

    symbol: str
    calls: list[ChainExpiration] = field(default_factory=list)
    puts: list[ChainExpiration] = field(default_factory=list)

    @classmethod
    def from_xml(cls, xml_text: str) -> "OptionChainResponse":
        root = ET.fromstring(xml_text)
        base = root.find("BASE")
        symbol = base.get("ri", "") if base is not None else ""

        calls: list[ChainExpiration] = []
        puts: list[ChainExpiration] = []

        chain = root.find("CHAIN")
        if chain is not None:
            calls_elem = chain.find("CALLS")
            if calls_elem is not None:
                calls = [
                    ChainExpiration.from_element(e)
                    for e in calls_elem.findall("EXP_DATE")
                ]
            puts_elem = chain.find("PUTS")
            if puts_elem is not None:
                puts = [
                    ChainExpiration.from_element(e)
                    for e in puts_elem.findall("EXP_DATE")
                ]

        return cls(symbol=symbol, calls=calls, puts=puts)


@dataclass
class MontageQuote:
    """A single exchange-level quote from the dtmontage endpoint."""

    symbol: str           # Exchange-specific symbol, e.g. "-QS280121C7.A"
    exchange_name: str    # Full exchange name
    exchange_code: str    # Short exchange code, e.g. "AM"
    bid: float
    bid_size: int
    ask: float
    ask_size: int

    @classmethod
    def from_element(cls, elem: ET.Element) -> "MontageQuote":
        return cls(
            symbol=elem.get("se", ""),
            exchange_name=elem.get("en", ""),
            exchange_code=elem.get("ec", ""),
            bid=float(elem.get("b", "0")),
            bid_size=int(elem.get("bs", "0")),
            ask=float(elem.get("a", "0")),
            ask_size=int(elem.get("as", "0")),
        )


@dataclass
class MontageResponse:
    """Parsed response from the dtmontage (depth-of-market) endpoint."""

    symbol: str           # OCC symbol
    contract_symbol: str  # Underlying symbol
    expiration: str       # ISO date string, e.g. "2028-01-21"
    strike: float
    call_put: str         # "C" or "P"
    quotes: list[MontageQuote] = field(default_factory=list)

    @classmethod
    def from_xml(cls, xml_text: str) -> "MontageResponse":
        root = ET.fromstring(xml_text)
        base = root.find("BASE")
        if base is None:
            return cls(symbol="", contract_symbol="", expiration="", strike=0.0, call_put="")

        symbol = base.get("S", "")
        contract_symbol = base.get("cs", "")
        expiration = base.get("ex", "")
        strike = float(base.get("st", "0"))
        call_put = base.get("cp", "")

        quotes: list[MontageQuote] = []
        exch_quotes = root.find("EXCH_QUOTES")
        if exch_quotes is not None:
            quotes = [MontageQuote.from_element(o) for o in exch_quotes.findall("O")]

        return cls(
            symbol=symbol,
            contract_symbol=contract_symbol,
            expiration=expiration,
            strike=strike,
            call_put=call_put,
            quotes=quotes,
        )
