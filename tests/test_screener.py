"""Tests for the LiveVol screener API models and ScreenerAPI client."""

import pytest
import httpx
import respx
import xml.etree.ElementTree as ET

from fidelity_trader._http import BASE_URL
from fidelity_trader.models.screener import (
    ScanField,
    ScanRow,
    ScanResult,
    LiveVolSession,
)
from fidelity_trader.research.screener import (
    ScreenerAPI,
    LIVEVOL_URL,
    LIVEVOL_AUTH_URL,
)

_SAML_URL = f"{BASE_URL}/ftgw/digital/rschwidgets/api/saml"
_SAML_LOGIN_URL = f"{LIVEVOL_AUTH_URL}/auth/api/v1/sessions/samllogin"
_EXECUTE_SCAN_URL = f"{LIVEVOL_URL}/DataService/ScannerServiceReference.asmx/ExecuteScan"

# ---------------------------------------------------------------------------
# XML fixtures
# ---------------------------------------------------------------------------

_SAMPLE_SAML = "PHNhbWw6QXNzZXJ0aW9uPjwvc2FtbDpBc3NlcnRpb24+"

_SAMPLE_SESSION_RESPONSE = {
    "sid": "3a159b37-c4ba-4ab7-bd10-5cc4607a106f",
    "expiresAt": 1775156791,
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature",
}

_SCAN_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<Livevol>
  <ExecuteScanResult>
    <ScanResult>
      <Row>
        <Fields>
          <Field displayName="Symbol" value="PRMB" descriptionId="" />
          <Field displayName="Company Name" value="Primo Brands Corporation" descriptionId="" />
          <Field displayName="Last" value="18.65" descriptionId="" />
          <Field displayName="Last Change" value="-0.22" descriptionId="" />
          <Field displayName="Call Volume" value="16427" descriptionId="" />
          <Field displayName="Average Call Volume" value="442" descriptionId="16" />
          <Field displayName="Percent Average Call Volume" value="3717" descriptionId="17" />
        </Fields>
      </Row>
      <Row>
        <Fields>
          <Field displayName="Symbol" value="SCO" descriptionId="" />
          <Field displayName="Company Name" value="ProShares UltraShort DJUBS Crude Oil" descriptionId="" />
          <Field displayName="Last" value="8.31" descriptionId="" />
          <Field displayName="Last Change" value="-0.48" descriptionId="" />
          <Field displayName="Call Volume" value="21226" descriptionId="" />
          <Field displayName="Average Call Volume" value="1085" descriptionId="16" />
          <Field displayName="Percent Average Call Volume" value="1956" descriptionId="17" />
        </Fields>
      </Row>
    </ScanResult>
  </ExecuteScanResult>
</Livevol>
"""

_EMPTY_SCAN_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<Livevol>
  <ExecuteScanResult>
    <ScanResult>
    </ScanResult>
  </ExecuteScanResult>
</Livevol>
"""

_NO_SCAN_RESULT_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<Livevol>
  <ExecuteScanResult>
  </ExecuteScanResult>
</Livevol>
"""

_SINGLE_ROW_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<Livevol>
  <ExecuteScanResult>
    <ScanResult>
      <Row>
        <Fields>
          <Field displayName="Symbol" value="AAPL" descriptionId="" />
          <Field displayName="Last" value="175.50" descriptionId="" />
        </Fields>
      </Row>
    </ScanResult>
  </ExecuteScanResult>
</Livevol>
"""


# ---------------------------------------------------------------------------
# ScanField
# ---------------------------------------------------------------------------

class TestScanField:
    def test_from_element_parses_all_attributes(self):
        elem = ET.fromstring(
            '<Field displayName="Symbol" value="PRMB" descriptionId="" />'
        )
        f = ScanField.from_element(elem)
        assert f.display_name == "Symbol"
        assert f.value == "PRMB"
        assert f.description_id == ""

    def test_from_element_with_description_id(self):
        elem = ET.fromstring(
            '<Field displayName="Average Call Volume" value="442" descriptionId="16" />'
        )
        f = ScanField.from_element(elem)
        assert f.display_name == "Average Call Volume"
        assert f.value == "442"
        assert f.description_id == "16"

    def test_from_element_missing_attributes_default_empty(self):
        elem = ET.fromstring("<Field />")
        f = ScanField.from_element(elem)
        assert f.display_name == ""
        assert f.value == ""
        assert f.description_id == ""

    def test_manual_construction(self):
        f = ScanField(display_name="Last", value="100.5", description_id="")
        assert f.display_name == "Last"
        assert f.value == "100.5"


# ---------------------------------------------------------------------------
# ScanRow
# ---------------------------------------------------------------------------

class TestScanRow:
    def test_getitem_returns_value_by_display_name(self):
        row = ScanRow(
            fields=[
                ScanField("Symbol", "AAPL", ""),
                ScanField("Last", "175.50", ""),
            ]
        )
        assert row["Symbol"] == "AAPL"
        assert row["Last"] == "175.50"

    def test_getitem_raises_key_error_for_missing_name(self):
        row = ScanRow(
            fields=[ScanField("Symbol", "AAPL", "")]
        )
        with pytest.raises(KeyError, match="Volume"):
            row["Volume"]

    def test_get_returns_value_for_existing_name(self):
        row = ScanRow(
            fields=[ScanField("Symbol", "SPY", "")]
        )
        assert row.get("Symbol") == "SPY"

    def test_get_returns_default_for_missing_name(self):
        row = ScanRow(fields=[ScanField("Symbol", "SPY", "")])
        assert row.get("Volume") is None
        assert row.get("Volume", "N/A") == "N/A"

    def test_get_returns_none_by_default(self):
        row = ScanRow(fields=[])
        assert row.get("anything") is None

    def test_from_element_parses_fields(self):
        xml = """
        <Row>
          <Fields>
            <Field displayName="Symbol" value="TEST" descriptionId="" />
            <Field displayName="Last" value="50.0" descriptionId="" />
          </Fields>
        </Row>
        """
        elem = ET.fromstring(xml)
        row = ScanRow.from_element(elem)
        assert len(row.fields) == 2
        assert row["Symbol"] == "TEST"
        assert row["Last"] == "50.0"

    def test_from_element_no_fields_element(self):
        elem = ET.fromstring("<Row></Row>")
        row = ScanRow.from_element(elem)
        assert len(row.fields) == 0

    def test_from_element_empty_fields(self):
        elem = ET.fromstring("<Row><Fields></Fields></Row>")
        row = ScanRow.from_element(elem)
        assert len(row.fields) == 0

    def test_dict_access_first_match_wins(self):
        row = ScanRow(
            fields=[
                ScanField("Symbol", "FIRST", ""),
                ScanField("Symbol", "SECOND", ""),
            ]
        )
        assert row["Symbol"] == "FIRST"
        assert row.get("Symbol") == "FIRST"


# ---------------------------------------------------------------------------
# ScanResult
# ---------------------------------------------------------------------------

class TestScanResult:
    def test_from_xml_parses_multiple_rows(self):
        result = ScanResult.from_xml(_SCAN_XML)
        assert len(result.rows) == 2

    def test_from_xml_first_row_symbol(self):
        result = ScanResult.from_xml(_SCAN_XML)
        assert result.rows[0]["Symbol"] == "PRMB"

    def test_from_xml_second_row_symbol(self):
        result = ScanResult.from_xml(_SCAN_XML)
        assert result.rows[1]["Symbol"] == "SCO"

    def test_from_xml_field_values(self):
        result = ScanResult.from_xml(_SCAN_XML)
        row = result.rows[0]
        assert row["Company Name"] == "Primo Brands Corporation"
        assert row["Last"] == "18.65"
        assert row["Last Change"] == "-0.22"
        assert row["Call Volume"] == "16427"
        assert row["Average Call Volume"] == "442"
        assert row["Percent Average Call Volume"] == "3717"

    def test_from_xml_second_row_field_values(self):
        result = ScanResult.from_xml(_SCAN_XML)
        row = result.rows[1]
        assert row["Company Name"] == "ProShares UltraShort DJUBS Crude Oil"
        assert row["Last"] == "8.31"
        assert row["Call Volume"] == "21226"

    def test_symbols_property(self):
        result = ScanResult.from_xml(_SCAN_XML)
        assert result.symbols == ["PRMB", "SCO"]

    def test_symbols_empty_result(self):
        result = ScanResult.from_xml(_EMPTY_SCAN_XML)
        assert result.symbols == []

    def test_from_xml_empty_scan_result(self):
        result = ScanResult.from_xml(_EMPTY_SCAN_XML)
        assert len(result.rows) == 0

    def test_from_xml_no_scan_result_element(self):
        result = ScanResult.from_xml(_NO_SCAN_RESULT_XML)
        assert len(result.rows) == 0
        assert result.symbols == []

    def test_from_xml_single_row(self):
        result = ScanResult.from_xml(_SINGLE_ROW_XML)
        assert len(result.rows) == 1
        assert result.rows[0]["Symbol"] == "AAPL"
        assert result.symbols == ["AAPL"]

    def test_description_id_preserved(self):
        result = ScanResult.from_xml(_SCAN_XML)
        avg_vol_field = None
        for f in result.rows[0].fields:
            if f.display_name == "Average Call Volume":
                avg_vol_field = f
                break
        assert avg_vol_field is not None
        assert avg_vol_field.description_id == "16"

    def test_default_construction(self):
        result = ScanResult()
        assert result.rows == []
        assert result.symbols == []


# ---------------------------------------------------------------------------
# LiveVolSession
# ---------------------------------------------------------------------------

class TestLiveVolSession:
    def test_construction(self):
        session = LiveVolSession(
            sid="abc-123",
            token="jwt.token.here",
            expires_at=1775156791,
        )
        assert session.sid == "abc-123"
        assert session.token == "jwt.token.here"
        assert session.expires_at == 1775156791

    def test_all_fields_stored(self):
        session = LiveVolSession(
            sid="3a159b37-c4ba-4ab7-bd10-5cc4607a106f",
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.sig",
            expires_at=9999999999,
        )
        assert session.sid == "3a159b37-c4ba-4ab7-bd10-5cc4607a106f"
        assert session.token.startswith("eyJ")
        assert session.expires_at == 9999999999


# ---------------------------------------------------------------------------
# ScreenerAPI — SAML assertion fetch (Step 1)
# ---------------------------------------------------------------------------

class TestScreenerAPISAMLFetch:
    @respx.mock
    def test_get_saml_assertion_makes_correct_request(self):
        route = respx.get(_SAML_URL).mock(
            return_value=httpx.Response(200, text=_SAMPLE_SAML)
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        result = api._get_saml_assertion()

        assert route.called
        assert result == _SAMPLE_SAML

    @respx.mock
    def test_get_saml_assertion_strips_whitespace(self):
        respx.get(_SAML_URL).mock(
            return_value=httpx.Response(200, text=f"  {_SAMPLE_SAML}  \n")
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        result = api._get_saml_assertion()
        assert result == _SAMPLE_SAML

    @respx.mock
    def test_get_saml_assertion_raises_on_error(self):
        respx.get(_SAML_URL).mock(return_value=httpx.Response(401))
        client = httpx.Client()
        api = ScreenerAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api._get_saml_assertion()


# ---------------------------------------------------------------------------
# ScreenerAPI — SAML exchange (Step 2)
# ---------------------------------------------------------------------------

class TestScreenerAPISAMLExchange:
    @respx.mock
    def test_exchange_saml_posts_form_encoded(self):
        route = respx.post(_SAML_LOGIN_URL).mock(
            return_value=httpx.Response(201, json=_SAMPLE_SESSION_RESPONSE)
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        api._exchange_saml(_SAMPLE_SAML)

        request = route.calls[0].request
        body = request.content.decode()
        assert "SAMLResponse=" in body

    @respx.mock
    def test_exchange_saml_sends_fetch_token_param(self):
        route = respx.post(_SAML_LOGIN_URL).mock(
            return_value=httpx.Response(201, json=_SAMPLE_SESSION_RESPONSE)
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        api._exchange_saml(_SAMPLE_SAML)

        request = route.calls[0].request
        assert "fetchToken=true" in str(request.url)

    @respx.mock
    def test_exchange_saml_returns_livevol_session(self):
        respx.post(_SAML_LOGIN_URL).mock(
            return_value=httpx.Response(201, json=_SAMPLE_SESSION_RESPONSE)
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        session = api._exchange_saml(_SAMPLE_SAML)

        assert isinstance(session, LiveVolSession)
        assert session.sid == "3a159b37-c4ba-4ab7-bd10-5cc4607a106f"
        assert session.token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"
        assert session.expires_at == 1775156791

    @respx.mock
    def test_exchange_saml_raises_on_error(self):
        respx.post(_SAML_LOGIN_URL).mock(return_value=httpx.Response(403))
        client = httpx.Client()
        api = ScreenerAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api._exchange_saml(_SAMPLE_SAML)


# ---------------------------------------------------------------------------
# ScreenerAPI — authenticate (full flow)
# ---------------------------------------------------------------------------

class TestScreenerAPIAuthenticate:
    @respx.mock
    def test_authenticate_runs_full_flow(self):
        respx.get(_SAML_URL).mock(
            return_value=httpx.Response(200, text=_SAMPLE_SAML)
        )
        respx.post(_SAML_LOGIN_URL).mock(
            return_value=httpx.Response(201, json=_SAMPLE_SESSION_RESPONSE)
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        session = api.authenticate()

        assert isinstance(session, LiveVolSession)
        assert session.token == _SAMPLE_SESSION_RESPONSE["token"]

    @respx.mock
    def test_authenticate_caches_session(self):
        respx.get(_SAML_URL).mock(
            return_value=httpx.Response(200, text=_SAMPLE_SAML)
        )
        respx.post(_SAML_LOGIN_URL).mock(
            return_value=httpx.Response(201, json=_SAMPLE_SESSION_RESPONSE)
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        api.authenticate()

        assert api._session is not None
        assert api._session.token == _SAMPLE_SESSION_RESPONSE["token"]

    @respx.mock
    def test_authenticate_returns_session_with_all_fields(self):
        respx.get(_SAML_URL).mock(
            return_value=httpx.Response(200, text=_SAMPLE_SAML)
        )
        respx.post(_SAML_LOGIN_URL).mock(
            return_value=httpx.Response(201, json=_SAMPLE_SESSION_RESPONSE)
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        session = api.authenticate()

        assert session.sid == "3a159b37-c4ba-4ab7-bd10-5cc4607a106f"
        assert session.expires_at == 1775156791


# ---------------------------------------------------------------------------
# ScreenerAPI — execute_scan
# ---------------------------------------------------------------------------

class TestScreenerAPIExecuteScan:
    @respx.mock
    def test_execute_scan_with_explicit_token(self):
        route = respx.post(_EXECUTE_SCAN_URL).mock(
            return_value=httpx.Response(200, text=_SCAN_XML)
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        result = api.execute_scan(scan_id=2, token="my.jwt.token")

        assert route.called
        assert isinstance(result, ScanResult)
        assert len(result.rows) == 2

    @respx.mock
    def test_execute_scan_sends_form_encoded_body(self):
        route = respx.post(_EXECUTE_SCAN_URL).mock(
            return_value=httpx.Response(200, text=_SCAN_XML)
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        api.execute_scan(scan_id=2, token="my.jwt.token")

        request = route.calls[0].request
        body = request.content.decode()
        assert "TOKEN=my.jwt.token" in body
        assert "SCANID=2" in body

    @respx.mock
    def test_execute_scan_uses_cached_token(self):
        respx.get(_SAML_URL).mock(
            return_value=httpx.Response(200, text=_SAMPLE_SAML)
        )
        respx.post(_SAML_LOGIN_URL).mock(
            return_value=httpx.Response(201, json=_SAMPLE_SESSION_RESPONSE)
        )
        route = respx.post(_EXECUTE_SCAN_URL).mock(
            return_value=httpx.Response(200, text=_SCAN_XML)
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        api.authenticate()
        api.execute_scan(scan_id=2)

        request = route.calls[0].request
        body = request.content.decode()
        assert f"TOKEN={_SAMPLE_SESSION_RESPONSE['token']}" in body

    def test_execute_scan_raises_without_token_or_session(self):
        client = httpx.Client()
        api = ScreenerAPI(client)
        with pytest.raises(ValueError, match="No token provided"):
            api.execute_scan(scan_id=2)

    @respx.mock
    def test_execute_scan_raises_on_http_error(self):
        respx.post(_EXECUTE_SCAN_URL).mock(
            return_value=httpx.Response(500)
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.execute_scan(scan_id=2, token="tok")

    @respx.mock
    def test_execute_scan_returns_parsed_symbols(self):
        respx.post(_EXECUTE_SCAN_URL).mock(
            return_value=httpx.Response(200, text=_SCAN_XML)
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        result = api.execute_scan(scan_id=2, token="tok")
        assert result.symbols == ["PRMB", "SCO"]

    @respx.mock
    def test_execute_scan_empty_result(self):
        respx.post(_EXECUTE_SCAN_URL).mock(
            return_value=httpx.Response(200, text=_EMPTY_SCAN_XML)
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        result = api.execute_scan(scan_id=5, token="tok")
        assert len(result.rows) == 0
        assert result.symbols == []

    @respx.mock
    def test_execute_scan_different_scan_id(self):
        route = respx.post(_EXECUTE_SCAN_URL).mock(
            return_value=httpx.Response(200, text=_SINGLE_ROW_XML)
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        api.execute_scan(scan_id=99, token="tok")

        request = route.calls[0].request
        body = request.content.decode()
        assert "SCANID=99" in body

    @respx.mock
    def test_execute_scan_explicit_token_overrides_cached(self):
        respx.get(_SAML_URL).mock(
            return_value=httpx.Response(200, text=_SAMPLE_SAML)
        )
        respx.post(_SAML_LOGIN_URL).mock(
            return_value=httpx.Response(201, json=_SAMPLE_SESSION_RESPONSE)
        )
        route = respx.post(_EXECUTE_SCAN_URL).mock(
            return_value=httpx.Response(200, text=_SCAN_XML)
        )
        client = httpx.Client()
        api = ScreenerAPI(client)
        api.authenticate()
        api.execute_scan(scan_id=2, token="override.token.here")

        request = route.calls[0].request
        body = request.content.decode()
        assert "TOKEN=override.token.here" in body
