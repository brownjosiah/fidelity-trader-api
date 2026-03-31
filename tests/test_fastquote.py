"""Tests for the fastquote option chain and depth-of-market APIs."""

import pytest
import httpx
import respx

from fidelity_trader._http import FASTQUOTE_URL
from fidelity_trader.models.fastquote import (
    ChainOption,
    ChainExpiration,
    OptionChainResponse,
    MontageQuote,
    MontageResponse,
)
from fidelity_trader.market_data.fastquote import FastQuoteAPI

_CHAIN_URL = f"{FASTQUOTE_URL}/service/quote/chainLite"
_MONTAGE_URL = f"{FASTQUOTE_URL}/service/quote/dtmontage"

# ---------------------------------------------------------------------------
# XML fixtures
# ---------------------------------------------------------------------------

_CHAIN_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<OPTIONCHAIN>
  <BASE ri="QS" err="0" us="QS" fs="QS" st=""/>
  <CHAIN>
    <CALLS>
      <EXP_DATE dt="2026-04-02">
        <O s="-QS260402C3" cs="QS" st="3" et="W"/>
        <O s="-QS260402C4" cs="QS" st="4" et="W"/>
        <O s="-QS260402C5" cs="QS" st="5" et="W"/>
      </EXP_DATE>
      <EXP_DATE dt="2026-04-17">
        <O s="-QS260417C1" cs="QS" st="1" et="M"/>
      </EXP_DATE>
    </CALLS>
    <PUTS>
      <EXP_DATE dt="2026-04-02">
        <O s="-QS260402P3" cs="QS" st="3" et="W"/>
      </EXP_DATE>
    </PUTS>
  </CHAIN>
</OPTIONCHAIN>
"""

_MONTAGE_XML = """\
<OPTIONS_MONTAGE>
  <BASE S="-QS280121C7" err="0" cs="QS" fs="QS" ex="2028-01-21" st="7.00" cp="C" adj=""/>
  <EXCH_QUOTES>
    <O se="-QS280121C7.A" en="NYSE Amex Options Market" ec="AM" es="AMEX" b="2.50" bs="168" a="2.59" as="44"/>
    <O se="-QS280121C7.W" en="Chicago Board Options Exchange" ec="CB" es="CBOE" b="2.50" bs="3" a="2.59" as="22"/>
    <O se="-QS280121C7.X" en="NASDAQ OMX PHLX" ec="PH" es="PHLX" b="2.40" bs="96" a="2.59" as="65"/>
  </EXCH_QUOTES>
</OPTIONS_MONTAGE>
"""

_EMPTY_CHAIN_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<OPTIONCHAIN>
  <BASE ri="XYZ" err="0" us="XYZ" fs="XYZ" st=""/>
  <CHAIN>
    <CALLS/>
    <PUTS/>
  </CHAIN>
</OPTIONCHAIN>
"""


# ---------------------------------------------------------------------------
# ChainOption
# ---------------------------------------------------------------------------

class TestChainOption:
    def test_parses_all_attributes(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring('<O s="-QS260402C3" cs="QS" st="3" et="W"/>')
        opt = ChainOption.from_element(elem)
        assert opt.symbol == "-QS260402C3"
        assert opt.contract_symbol == "QS"
        assert opt.strike == pytest.approx(3.0)
        assert opt.expiry_type == "W"

    def test_monthly_expiry_type(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring('<O s="-QS260417C1" cs="QS" st="1" et="M"/>')
        opt = ChainOption.from_element(elem)
        assert opt.expiry_type == "M"
        assert opt.strike == pytest.approx(1.0)

    def test_missing_attributes_default(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring('<O/>')
        opt = ChainOption.from_element(elem)
        assert opt.symbol == ""
        assert opt.contract_symbol == ""
        assert opt.strike == pytest.approx(0.0)
        assert opt.expiry_type == ""


# ---------------------------------------------------------------------------
# ChainExpiration
# ---------------------------------------------------------------------------

class TestChainExpiration:
    def test_parses_date_and_options(self):
        import xml.etree.ElementTree as ET
        xml = '<EXP_DATE dt="2026-04-02"><O s="-QS260402C3" cs="QS" st="3" et="W"/><O s="-QS260402C4" cs="QS" st="4" et="W"/></EXP_DATE>'
        elem = ET.fromstring(xml)
        exp = ChainExpiration.from_element(elem)
        assert exp.date == "2026-04-02"
        assert len(exp.options) == 2
        assert exp.options[0].symbol == "-QS260402C3"
        assert exp.options[1].strike == pytest.approx(4.0)

    def test_empty_expiration(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring('<EXP_DATE dt="2026-04-17"/>')
        exp = ChainExpiration.from_element(elem)
        assert exp.date == "2026-04-17"
        assert exp.options == []


# ---------------------------------------------------------------------------
# OptionChainResponse
# ---------------------------------------------------------------------------

class TestOptionChainResponse:
    def test_parses_symbol(self):
        resp = OptionChainResponse.from_xml(_CHAIN_XML)
        assert resp.symbol == "QS"

    def test_parses_calls(self):
        resp = OptionChainResponse.from_xml(_CHAIN_XML)
        assert len(resp.calls) == 2

    def test_first_call_expiration_date(self):
        resp = OptionChainResponse.from_xml(_CHAIN_XML)
        assert resp.calls[0].date == "2026-04-02"

    def test_first_call_expiration_options_count(self):
        resp = OptionChainResponse.from_xml(_CHAIN_XML)
        assert len(resp.calls[0].options) == 3

    def test_call_option_fields(self):
        resp = OptionChainResponse.from_xml(_CHAIN_XML)
        opt = resp.calls[0].options[0]
        assert opt.symbol == "-QS260402C3"
        assert opt.contract_symbol == "QS"
        assert opt.strike == pytest.approx(3.0)
        assert opt.expiry_type == "W"

    def test_second_call_expiration_monthly(self):
        resp = OptionChainResponse.from_xml(_CHAIN_XML)
        exp = resp.calls[1]
        assert exp.date == "2026-04-17"
        assert len(exp.options) == 1
        assert exp.options[0].expiry_type == "M"

    def test_parses_puts(self):
        resp = OptionChainResponse.from_xml(_CHAIN_XML)
        assert len(resp.puts) == 1
        assert resp.puts[0].date == "2026-04-02"
        assert len(resp.puts[0].options) == 1
        assert resp.puts[0].options[0].symbol == "-QS260402P3"

    def test_empty_chain(self):
        resp = OptionChainResponse.from_xml(_EMPTY_CHAIN_XML)
        assert resp.symbol == "XYZ"
        assert resp.calls == []
        assert resp.puts == []


# ---------------------------------------------------------------------------
# MontageQuote
# ---------------------------------------------------------------------------

class TestMontageQuote:
    def test_parses_all_attributes(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring(
            '<O se="-QS280121C7.A" en="NYSE Amex Options Market" ec="AM" es="AMEX" b="2.50" bs="168" a="2.59" as="44"/>'
        )
        q = MontageQuote.from_element(elem)
        assert q.symbol == "-QS280121C7.A"
        assert q.exchange_name == "NYSE Amex Options Market"
        assert q.exchange_code == "AM"
        assert q.bid == pytest.approx(2.50)
        assert q.bid_size == 168
        assert q.ask == pytest.approx(2.59)
        assert q.ask_size == 44

    def test_missing_attributes_default(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring('<O/>')
        q = MontageQuote.from_element(elem)
        assert q.symbol == ""
        assert q.exchange_name == ""
        assert q.exchange_code == ""
        assert q.bid == pytest.approx(0.0)
        assert q.bid_size == 0
        assert q.ask == pytest.approx(0.0)
        assert q.ask_size == 0


# ---------------------------------------------------------------------------
# MontageResponse
# ---------------------------------------------------------------------------

class TestMontageResponse:
    def test_parses_base_fields(self):
        resp = MontageResponse.from_xml(_MONTAGE_XML)
        assert resp.symbol == "-QS280121C7"
        assert resp.contract_symbol == "QS"
        assert resp.expiration == "2028-01-21"
        assert resp.strike == pytest.approx(7.0)
        assert resp.call_put == "C"

    def test_parses_all_quotes(self):
        resp = MontageResponse.from_xml(_MONTAGE_XML)
        assert len(resp.quotes) == 3

    def test_first_quote_fields(self):
        resp = MontageResponse.from_xml(_MONTAGE_XML)
        q = resp.quotes[0]
        assert q.symbol == "-QS280121C7.A"
        assert q.exchange_name == "NYSE Amex Options Market"
        assert q.exchange_code == "AM"
        assert q.bid == pytest.approx(2.50)
        assert q.bid_size == 168
        assert q.ask == pytest.approx(2.59)
        assert q.ask_size == 44

    def test_second_quote_fields(self):
        resp = MontageResponse.from_xml(_MONTAGE_XML)
        q = resp.quotes[1]
        assert q.exchange_code == "CB"
        assert q.bid_size == 3

    def test_third_quote_fields(self):
        resp = MontageResponse.from_xml(_MONTAGE_XML)
        q = resp.quotes[2]
        assert q.exchange_code == "PH"
        assert q.bid == pytest.approx(2.40)
        assert q.ask_size == 65

    def test_empty_exch_quotes(self):
        xml = '<OPTIONS_MONTAGE><BASE S="-A" cs="A" ex="2028-01-21" st="5.00" cp="P"/></OPTIONS_MONTAGE>'
        resp = MontageResponse.from_xml(xml)
        assert resp.symbol == "-A"
        assert resp.quotes == []

    def test_no_base_element(self):
        xml = '<OPTIONS_MONTAGE></OPTIONS_MONTAGE>'
        resp = MontageResponse.from_xml(xml)
        assert resp.symbol == ""
        assert resp.quotes == []


# ---------------------------------------------------------------------------
# FastQuoteAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestFastQuoteAPIChain:
    @respx.mock
    def test_get_option_chain_makes_correct_request(self):
        route = respx.get(_CHAIN_URL).mock(
            return_value=httpx.Response(200, text=_CHAIN_XML, headers={"content-type": "application/xml"})
        )
        client = httpx.Client()
        api = FastQuoteAPI(client)
        result = api.get_option_chain("QS")

        assert route.called
        assert isinstance(result, OptionChainResponse)
        client.close()

    @respx.mock
    def test_get_option_chain_sends_correct_params(self):
        route = respx.get(_CHAIN_URL).mock(
            return_value=httpx.Response(200, text=_CHAIN_XML, headers={"content-type": "application/xml"})
        )
        client = httpx.Client()
        api = FastQuoteAPI(client)
        api.get_option_chain("QS")

        request = route.calls[0].request
        assert "symbols=QS" in str(request.url)
        assert "productid=atn" in str(request.url)
        client.close()

    @respx.mock
    def test_get_option_chain_parses_symbol(self):
        respx.get(_CHAIN_URL).mock(
            return_value=httpx.Response(200, text=_CHAIN_XML, headers={"content-type": "application/xml"})
        )
        client = httpx.Client()
        api = FastQuoteAPI(client)
        result = api.get_option_chain("QS")

        assert result.symbol == "QS"
        assert len(result.calls) == 2
        assert len(result.puts) == 1
        client.close()

    @respx.mock
    def test_get_option_chain_raises_on_http_error(self):
        respx.get(_CHAIN_URL).mock(return_value=httpx.Response(403))
        client = httpx.Client()
        api = FastQuoteAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_option_chain("QS")
        client.close()


class TestFastQuoteAPIMontage:
    @respx.mock
    def test_get_montage_makes_correct_request(self):
        route = respx.get(_MONTAGE_URL).mock(
            return_value=httpx.Response(200, text=_MONTAGE_XML, headers={"content-type": "application/xml"})
        )
        client = httpx.Client()
        api = FastQuoteAPI(client)
        result = api.get_montage("-QS280121C7")

        assert route.called
        assert isinstance(result, MontageResponse)
        client.close()

    @respx.mock
    def test_get_montage_sends_correct_params(self):
        route = respx.get(_MONTAGE_URL).mock(
            return_value=httpx.Response(200, text=_MONTAGE_XML, headers={"content-type": "application/xml"})
        )
        client = httpx.Client()
        api = FastQuoteAPI(client)
        api.get_montage("-QS280121C7")

        request = route.calls[0].request
        assert "symbols=-QS280121C7" in str(request.url)
        assert "productid=atn" in str(request.url)
        client.close()

    @respx.mock
    def test_get_montage_parses_response(self):
        respx.get(_MONTAGE_URL).mock(
            return_value=httpx.Response(200, text=_MONTAGE_XML, headers={"content-type": "application/xml"})
        )
        client = httpx.Client()
        api = FastQuoteAPI(client)
        result = api.get_montage("-QS280121C7")

        assert result.symbol == "-QS280121C7"
        assert result.contract_symbol == "QS"
        assert result.expiration == "2028-01-21"
        assert result.strike == pytest.approx(7.0)
        assert result.call_put == "C"
        assert len(result.quotes) == 3
        client.close()

    @respx.mock
    def test_get_montage_raises_on_http_error(self):
        respx.get(_MONTAGE_URL).mock(return_value=httpx.Response(500))
        client = httpx.Client()
        api = FastQuoteAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.get_montage("-QS280121C7")
        client.close()


# ---------------------------------------------------------------------------
# _http.py constant
# ---------------------------------------------------------------------------

def test_fastquote_url_defined():
    from fidelity_trader._http import FASTQUOTE_URL
    assert FASTQUOTE_URL == "https://fastquote.fidelity.com"
