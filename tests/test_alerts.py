"""Tests for the alerts subscription SOAP API."""
from __future__ import annotations

import html
import xml.etree.ElementTree as ET

import httpx
import pytest
import respx

from fidelity_trader._http import ALERTS_URL
from fidelity_trader.alerts.subscription import (
    AlertsAPI,
    _build_get_alerts_envelope,
    _build_soap_envelope,
)
from fidelity_trader.models.alerts import AlertActivation, AlertMessage, AlertsResponse

_SUBSCRIBE_URL = f"{ALERTS_URL}/ftgw/alerts/services/ATBTSubscription"

# ---------------------------------------------------------------------------
# Sample SOAP response (mirrors captured traffic)
# ---------------------------------------------------------------------------

_SAMPLE_RESPONSE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Body>
    <p971:CustomerSignOnResponse xmlns:p971="http://xmlns.fmr.com/institutional/eca/fens/2014/06/AutoSubscription">
      <p971:ResultCode>SUCCESS</p971:ResultCode>
      <p971:ActivationDetails>
        <p971:ActivationStatus>1</p971:ActivationStatus>
        <p971:UserId>oyIIObJORWQJdtfIm05OqQ==</p971:UserId>
        <p971:Password>4893ebc1559b4b0d8a1ec291fcb2f422</p971:Password>
        <p971:ServerUrl>ssl://atccf.fisc.fidelity.com:443</p971:ServerUrl>
        <p971:Destination>EMST.ATP.oyIIObJORWQJdtfIm05OqQ==,EMST.ATC.BROADCAST</p971:Destination>
      </p971:ActivationDetails>
    </p971:CustomerSignOnResponse>
  </soapenv:Body>
</soapenv:Envelope>"""

_FAILURE_RESPONSE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Body>
    <p971:CustomerSignOnResponse xmlns:p971="http://xmlns.fmr.com/institutional/eca/fens/2014/06/AutoSubscription">
      <p971:ResultCode>FAILURE</p971:ResultCode>
      <p971:ActivationDetails>
        <p971:ActivationStatus>0</p971:ActivationStatus>
        <p971:UserId>none</p971:UserId>
        <p971:Password>none</p971:Password>
        <p971:ServerUrl>ssl://atccf.fisc.fidelity.com:443</p971:ServerUrl>
        <p971:Destination></p971:Destination>
      </p971:ActivationDetails>
    </p971:CustomerSignOnResponse>
  </soapenv:Body>
</soapenv:Envelope>"""


# ---------------------------------------------------------------------------
# AlertActivation model tests
# ---------------------------------------------------------------------------

class TestAlertActivation:
    def test_parses_all_fields(self):
        act = AlertActivation.from_xml(_SAMPLE_RESPONSE_XML)
        assert act.result_code == "SUCCESS"
        assert act.activation_status == "1"
        assert act.user_id == "oyIIObJORWQJdtfIm05OqQ=="
        assert act.password == "4893ebc1559b4b0d8a1ec291fcb2f422"
        assert act.server_url == "ssl://atccf.fisc.fidelity.com:443"
        assert act.destination == "EMST.ATP.oyIIObJORWQJdtfIm05OqQ==,EMST.ATC.BROADCAST"

    def test_is_success_true_when_success(self):
        act = AlertActivation.from_xml(_SAMPLE_RESPONSE_XML)
        assert act.is_success is True

    def test_is_success_false_when_failure(self):
        act = AlertActivation.from_xml(_FAILURE_RESPONSE_XML)
        assert act.is_success is False

    def test_raises_on_missing_body(self):
        bad_xml = b"<root/>"
        with pytest.raises(ValueError, match="SOAP Body"):
            AlertActivation.from_xml(bad_xml)

    def test_raises_on_missing_response_element(self):
        no_response = b"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
          <soapenv:Body/>
        </soapenv:Envelope>"""
        with pytest.raises(ValueError, match="CustomerSignOnResponse"):
            AlertActivation.from_xml(no_response)

    def test_raises_on_missing_activation_details(self):
        no_details = b"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
          <soapenv:Body>
            <p971:CustomerSignOnResponse xmlns:p971="http://xmlns.fmr.com/institutional/eca/fens/2014/06/AutoSubscription">
              <p971:ResultCode>SUCCESS</p971:ResultCode>
            </p971:CustomerSignOnResponse>
          </soapenv:Body>
        </soapenv:Envelope>"""
        with pytest.raises(ValueError, match="ActivationDetails"):
            AlertActivation.from_xml(no_details)

    def test_is_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(AlertActivation)


# ---------------------------------------------------------------------------
# _build_soap_envelope tests
# ---------------------------------------------------------------------------

class TestBuildSoapEnvelope:
    def setup_method(self):
        self.xml_bytes = _build_soap_envelope()
        self.root = ET.fromstring(self.xml_bytes)
        self._soap = "http://schemas.xmlsoap.org/soap/envelope/"
        self._aut = "http://xmlns.fmr.com/institutional/eca/fens/2014/06/AutoSubscription"
        self._prin = "http://xmlns.fmr.com/institutional/common/headers/2012/09/PrincipalIdentity"
        self._prod = "http://xmlns.fmr.com/institutional/common/headers/2011/08/ProductIdentity"

    def test_returns_bytes(self):
        assert isinstance(self.xml_bytes, bytes)

    def test_root_is_envelope(self):
        assert self.root.tag == f"{{{self._soap}}}Envelope"

    def test_has_header_and_body(self):
        header = self.root.find(f"{{{self._soap}}}Header")
        body = self.root.find(f"{{{self._soap}}}Body")
        assert header is not None
        assert body is not None

    def test_principal_identity_fields(self):
        header = self.root.find(f"{{{self._soap}}}Header")
        prin = header.find(f"{{{self._prin}}}PrincipalIdentity")
        assert prin is not None
        assert prin.find(f"{{{self._prin}}}RequestorId").text == "fidelity"
        assert prin.find(f"{{{self._prin}}}AuthMethod").text == "Basic"
        assert prin.find(f"{{{self._prin}}}PrincipalDomain").text == "Retail"
        assert prin.find(f"{{{self._prin}}}PrincipalRole").text == "Owner"

    def test_product_identity_fields(self):
        header = self.root.find(f"{{{self._soap}}}Header")
        prod = header.find(f"{{{self._prod}}}ProductIdentity")
        assert prod is not None
        assert prod.find(f"{{{self._prod}}}AppId").text == "AP002304"
        assert prod.find(f"{{{self._prod}}}AppName").text == "ATP"
        assert prod.find(f"{{{self._prod}}}AppVersion").text == "0.0.1"
        assert prod.find(f"{{{self._prod}}}ProductId").text == "ATP"
        assert prod.find(f"{{{self._prod}}}SubSystem").text == "ActiveTrader"

    def test_body_contains_customer_signon_with_alert_code(self):
        body = self.root.find(f"{{{self._soap}}}Body")
        sign_on = body.find(f"{{{self._aut}}}CustomerSignOn")
        assert sign_on is not None
        alert_code = sign_on.find(f"{{{self._aut}}}AlertCode")
        assert alert_code is not None
        assert alert_code.text == "ATBT"

    def test_is_valid_xml(self):
        # Should not raise
        ET.fromstring(self.xml_bytes)


# ---------------------------------------------------------------------------
# AlertsAPI HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestAlertsAPISubscribe:
    @respx.mock
    def test_subscribe_posts_to_correct_url(self):
        route = respx.post(_SUBSCRIBE_URL).mock(
            return_value=httpx.Response(200, content=_SAMPLE_RESPONSE_XML)
        )
        api = AlertsAPI(httpx.Client())
        api.subscribe()
        assert route.called
        assert str(route.calls[0].request.url) == _SUBSCRIBE_URL

    @respx.mock
    def test_subscribe_returns_alert_activation(self):
        respx.post(_SUBSCRIBE_URL).mock(
            return_value=httpx.Response(200, content=_SAMPLE_RESPONSE_XML)
        )
        api = AlertsAPI(httpx.Client())
        result = api.subscribe()
        assert isinstance(result, AlertActivation)

    @respx.mock
    def test_subscribe_returns_correct_fields(self):
        respx.post(_SUBSCRIBE_URL).mock(
            return_value=httpx.Response(200, content=_SAMPLE_RESPONSE_XML)
        )
        api = AlertsAPI(httpx.Client())
        result = api.subscribe()
        assert result.result_code == "SUCCESS"
        assert result.user_id == "oyIIObJORWQJdtfIm05OqQ=="
        assert result.password == "4893ebc1559b4b0d8a1ec291fcb2f422"
        assert result.server_url == "ssl://atccf.fisc.fidelity.com:443"
        assert result.destination == "EMST.ATP.oyIIObJORWQJdtfIm05OqQ==,EMST.ATC.BROADCAST"

    @respx.mock
    def test_subscribe_sends_soap_action_header(self):
        route = respx.post(_SUBSCRIBE_URL).mock(
            return_value=httpx.Response(200, content=_SAMPLE_RESPONSE_XML)
        )
        api = AlertsAPI(httpx.Client())
        api.subscribe()
        request = route.calls[0].request
        assert request.headers["SOAPAction"] == "CustomerSignOn"

    @respx.mock
    def test_subscribe_sends_correct_content_type(self):
        route = respx.post(_SUBSCRIBE_URL).mock(
            return_value=httpx.Response(200, content=_SAMPLE_RESPONSE_XML)
        )
        api = AlertsAPI(httpx.Client())
        api.subscribe()
        request = route.calls[0].request
        assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"

    @respx.mock
    def test_subscribe_sends_xml_body(self):
        route = respx.post(_SUBSCRIBE_URL).mock(
            return_value=httpx.Response(200, content=_SAMPLE_RESPONSE_XML)
        )
        api = AlertsAPI(httpx.Client())
        api.subscribe()
        request = route.calls[0].request
        # Body should be parseable as XML and contain the CustomerSignOn element
        root = ET.fromstring(request.content)
        ns_aut = "http://xmlns.fmr.com/institutional/eca/fens/2014/06/AutoSubscription"
        ns_soap = "http://schemas.xmlsoap.org/soap/envelope/"
        body = root.find(f"{{{ns_soap}}}Body")
        sign_on = body.find(f"{{{ns_aut}}}CustomerSignOn")
        assert sign_on is not None

    @respx.mock
    def test_subscribe_raises_on_401(self):
        respx.post(_SUBSCRIBE_URL).mock(return_value=httpx.Response(401))
        api = AlertsAPI(httpx.Client())
        with pytest.raises(httpx.HTTPStatusError):
            api.subscribe()

    @respx.mock
    def test_subscribe_raises_on_500(self):
        respx.post(_SUBSCRIBE_URL).mock(return_value=httpx.Response(500))
        api = AlertsAPI(httpx.Client())
        with pytest.raises(httpx.HTTPStatusError):
            api.subscribe()

    @respx.mock
    def test_subscribe_is_success(self):
        respx.post(_SUBSCRIBE_URL).mock(
            return_value=httpx.Response(200, content=_SAMPLE_RESPONSE_XML)
        )
        api = AlertsAPI(httpx.Client())
        result = api.subscribe()
        assert result.is_success is True


# ---------------------------------------------------------------------------
# GetAlerts sample data
# ---------------------------------------------------------------------------

_ALERTS_URL_FULL = f"{ALERTS_URL}/ftgw/alerts/services/ATBTAlerts"

_EXECUTION_ALERT_XML = """\
<ALERT>
  <MSG_HDR>
    <MSG_ID>MF.EX   .2026-04-02-12.11.27.611483</MSG_ID>
    <MSG_TYPE>MFCEX</MSG_TYPE>
    <MSG_PRIORITY>6</MSG_PRIORITY>
    <SYSTEM_FLAG>3</SYSTEM_FLAG>
    <ALERT_PUBLISHER_TMST>2026-04-02-12.11.27.610000</ALERT_PUBLISHER_TMST>
  </MSG_HDR>
  <DISPLAY_DETAIL>
    <DISPLAY_DATA_ENCODING>TEXT</DISPLAY_DATA_ENCODING>
    <DISPLAY_DATA>Order to BUY 1 -QS270115C7:  1  filled @ $1.55.   Execution time: 12:11 PM. Order Number: D02PTTQR</DISPLAY_DATA>
    <DISPLAY_SYMBOL>-QS270115C7</DISPLAY_SYMBOL>
  </DISPLAY_DETAIL>
  <MSG_DETAIL>
    <ACCOUNT_NUM>Z21772945</ACCOUNT_NUM>
    <ORDER_ACTION>BC</ORDER_ACTION>
    <ORIGINAL_QTY>1</ORIGINAL_QTY>
    <EXECUTED_QTY>1</EXECUTED_QTY>
    <ORDER_NUM>D02PTTQR</ORDER_NUM>
    <ORDER_STATUS>1</ORDER_STATUS>
    <DISP_MSG_SYMBOL>QS270115C7</DISP_MSG_SYMBOL>
    <AVG_PRICE>1.55</AVG_PRICE>
    <PRICE>1.55</PRICE>
    <EXEC_SHRS>1</EXEC_SHRS>
    <EXEC_DATE>20260402</EXEC_DATE>
    <EXCH_CODE>PHLX</EXCH_CODE>
    <GROSS_AMT>155</GROSS_AMT>
    <SEC_TYPE>8</SEC_TYPE>
  </MSG_DETAIL>
</ALERT>"""

_CANCELLATION_ALERT_XML = """\
<ALERT>
  <MSG_HDR>
    <MSG_ID>CX.01   .2026-04-02-14.05.33.123456</MSG_ID>
    <MSG_TYPE>CXL01</MSG_TYPE>
    <MSG_PRIORITY>5</MSG_PRIORITY>
    <SYSTEM_FLAG>2</SYSTEM_FLAG>
    <ALERT_PUBLISHER_TMST>2026-04-02-14.05.33.120000</ALERT_PUBLISHER_TMST>
  </MSG_HDR>
  <DISPLAY_DETAIL>
    <DISPLAY_DATA_ENCODING>TEXT</DISPLAY_DATA_ENCODING>
    <DISPLAY_DATA>Order to SELL 50 AAPL cancelled. Order Number: D02XYZAB</DISPLAY_DATA>
    <DISPLAY_SYMBOL>AAPL</DISPLAY_SYMBOL>
  </DISPLAY_DETAIL>
  <MSG_DETAIL>
    <ACCOUNT_NUM>Z21772945</ACCOUNT_NUM>
    <ORDER_ACTION>S</ORDER_ACTION>
    <ORIGINAL_QTY>50</ORIGINAL_QTY>
    <EXECUTED_QTY>0</EXECUTED_QTY>
    <ORDER_NUM>D02XYZAB</ORDER_NUM>
    <ORDER_STATUS>5</ORDER_STATUS>
    <DISP_MSG_SYMBOL>AAPL</DISP_MSG_SYMBOL>
    <AVG_PRICE></AVG_PRICE>
    <PRICE>175.50</PRICE>
    <EXEC_SHRS>0</EXEC_SHRS>
    <EXEC_DATE></EXEC_DATE>
    <EXCH_CODE></EXCH_CODE>
    <GROSS_AMT></GROSS_AMT>
    <SEC_TYPE>1</SEC_TYPE>
  </MSG_DETAIL>
</ALERT>"""


def _encode_document(alert_xml: str) -> str:
    """HTML-entity-encode an alert XML string (as Fidelity sends it)."""
    return html.escape(alert_xml, quote=True)


def _build_get_alerts_soap_response(
    total_count: int, alert_xmls: list[str]
) -> bytes:
    """Build a mock GetAlerts SOAP response with the given alerts."""
    docs = ""
    for alert_xml in alert_xmls:
        encoded = _encode_document(alert_xml)
        docs += (
            f"<ns1:Message><ns1:Document>{encoded}</ns1:Document></ns1:Message>"
        )
    messages_block = f"<ns1:Messages>{docs}</ns1:Messages>" if docs else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
        "<soapenv:Header/>"
        "<soapenv:Body>"
        '<ns1:GetAlertsResponse xmlns:ns1="http://xmlns.fmr.com/brokerage/fens/service/ALERTS/2009-09">'
        f"<ns1:TotalMsgCount>{total_count}</ns1:TotalMsgCount>"
        f"{messages_block}"
        "</ns1:GetAlertsResponse>"
        "</soapenv:Body>"
        "</soapenv:Envelope>"
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# AlertMessage model tests
# ---------------------------------------------------------------------------

class TestAlertMessage:
    def test_parses_execution_alert_fields(self):
        msg = AlertMessage.from_xml(_EXECUTION_ALERT_XML)
        assert msg.msg_id == "MF.EX   .2026-04-02-12.11.27.611483"
        assert msg.msg_type == "MFCEX"
        assert msg.priority == "6"
        assert msg.timestamp == "2026-04-02-12.11.27.610000"
        assert msg.display_text.startswith("Order to BUY 1")
        assert msg.display_symbol == "-QS270115C7"
        assert msg.account_num == "Z21772945"
        assert msg.order_action == "BC"
        assert msg.order_num == "D02PTTQR"
        assert msg.order_status == "1"
        assert msg.symbol == "QS270115C7"
        assert msg.quantity == "1"
        assert msg.executed_qty == "1"
        assert msg.price == "1.55"
        assert msg.avg_price == "1.55"
        assert msg.exec_date == "20260402"
        assert msg.exchange == "PHLX"
        assert msg.gross_amount == "155"
        assert msg.sec_type == "8"

    def test_parses_cancellation_alert_fields(self):
        msg = AlertMessage.from_xml(_CANCELLATION_ALERT_XML)
        assert msg.msg_id == "CX.01   .2026-04-02-14.05.33.123456"
        assert msg.msg_type == "CXL01"
        assert msg.priority == "5"
        assert msg.account_num == "Z21772945"
        assert msg.order_action == "S"
        assert msg.order_num == "D02XYZAB"
        assert msg.order_status == "5"
        assert msg.symbol == "AAPL"
        assert msg.quantity == "50"
        assert msg.executed_qty == "0"
        assert msg.price == "175.50"
        assert msg.display_text == "Order to SELL 50 AAPL cancelled. Order Number: D02XYZAB"

    def test_is_execution_true_for_mfcex(self):
        msg = AlertMessage.from_xml(_EXECUTION_ALERT_XML)
        assert msg.is_execution is True

    def test_is_execution_false_for_cxl01(self):
        msg = AlertMessage.from_xml(_CANCELLATION_ALERT_XML)
        assert msg.is_execution is False

    def test_is_cancellation_true_for_cxl01(self):
        msg = AlertMessage.from_xml(_CANCELLATION_ALERT_XML)
        assert msg.is_cancellation is True

    def test_is_cancellation_false_for_mfcex(self):
        msg = AlertMessage.from_xml(_EXECUTION_ALERT_XML)
        assert msg.is_cancellation is False

    def test_raw_xml_preserved(self):
        msg = AlertMessage.from_xml(_EXECUTION_ALERT_XML)
        assert msg.raw_xml == _EXECUTION_ALERT_XML

    def test_empty_fields_handled_gracefully(self):
        msg = AlertMessage.from_xml(_CANCELLATION_ALERT_XML)
        # These fields are empty strings in the cancellation alert
        assert msg.avg_price == ""
        assert msg.exec_date == ""
        assert msg.exchange == ""
        assert msg.gross_amount == ""

    def test_is_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(AlertMessage)

    def test_missing_msg_detail_section(self):
        """Alert with no MSG_DETAIL section returns empty strings."""
        xml = "<ALERT><MSG_HDR><MSG_TYPE>MFCEX</MSG_TYPE></MSG_HDR></ALERT>"
        msg = AlertMessage.from_xml(xml)
        assert msg.msg_type == "MFCEX"
        assert msg.account_num == ""
        assert msg.order_num == ""
        assert msg.symbol == ""

    def test_missing_display_detail_section(self):
        """Alert with no DISPLAY_DETAIL section returns empty strings."""
        xml = "<ALERT><MSG_HDR><MSG_TYPE>CXL01</MSG_TYPE></MSG_HDR></ALERT>"
        msg = AlertMessage.from_xml(xml)
        assert msg.display_text == ""
        assert msg.display_symbol == ""


# ---------------------------------------------------------------------------
# AlertsResponse model tests
# ---------------------------------------------------------------------------

class TestAlertsResponse:
    def test_parses_total_count(self):
        resp_bytes = _build_get_alerts_soap_response(9, [_EXECUTION_ALERT_XML])
        result = AlertsResponse.from_soap_response(resp_bytes)
        assert result.total_count == 9

    def test_parses_single_message(self):
        resp_bytes = _build_get_alerts_soap_response(1, [_EXECUTION_ALERT_XML])
        result = AlertsResponse.from_soap_response(resp_bytes)
        assert len(result.messages) == 1
        assert result.messages[0].msg_type == "MFCEX"

    def test_parses_multiple_messages(self):
        resp_bytes = _build_get_alerts_soap_response(
            2, [_EXECUTION_ALERT_XML, _CANCELLATION_ALERT_XML]
        )
        result = AlertsResponse.from_soap_response(resp_bytes)
        assert len(result.messages) == 2
        assert result.messages[0].is_execution is True
        assert result.messages[1].is_cancellation is True

    def test_empty_alerts_response(self):
        resp_bytes = _build_get_alerts_soap_response(0, [])
        result = AlertsResponse.from_soap_response(resp_bytes)
        assert result.total_count == 0
        assert result.messages == []

    def test_html_entity_decoding(self):
        """Verify the HTML-entity-encoded Document content is decoded."""
        resp_bytes = _build_get_alerts_soap_response(1, [_EXECUTION_ALERT_XML])
        result = AlertsResponse.from_soap_response(resp_bytes)
        # If decoding failed, the XML parser would fail on &lt; etc.
        assert result.messages[0].msg_type == "MFCEX"
        assert result.messages[0].order_num == "D02PTTQR"

    def test_raises_on_missing_soap_body(self):
        bad_xml = b"<root/>"
        with pytest.raises(ValueError, match="SOAP Body"):
            AlertsResponse.from_soap_response(bad_xml)

    def test_raises_on_missing_get_alerts_response(self):
        no_response = (
            b'<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
            b"<soapenv:Body/>"
            b"</soapenv:Envelope>"
        )
        with pytest.raises(ValueError, match="GetAlertsResponse"):
            AlertsResponse.from_soap_response(no_response)

    def test_raises_on_missing_total_msg_count(self):
        no_count = (
            b'<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
            b"<soapenv:Body>"
            b'<ns1:GetAlertsResponse xmlns:ns1="http://xmlns.fmr.com/brokerage/fens/service/ALERTS/2009-09">'
            b"</ns1:GetAlertsResponse>"
            b"</soapenv:Body>"
            b"</soapenv:Envelope>"
        )
        with pytest.raises(ValueError, match="TotalMsgCount"):
            AlertsResponse.from_soap_response(no_count)

    def test_is_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(AlertsResponse)

    def test_total_count_independent_of_message_count(self):
        """TotalMsgCount can be larger than returned messages (paging)."""
        resp_bytes = _build_get_alerts_soap_response(50, [_EXECUTION_ALERT_XML])
        result = AlertsResponse.from_soap_response(resp_bytes)
        assert result.total_count == 50
        assert len(result.messages) == 1


# ---------------------------------------------------------------------------
# _build_get_alerts_envelope tests
# ---------------------------------------------------------------------------

class TestBuildGetAlertsEnvelope:
    def setup_method(self):
        self.xml_bytes = _build_get_alerts_envelope()
        self.root = ET.fromstring(self.xml_bytes)
        self._soap = "http://schemas.xmlsoap.org/soap/envelope/"
        self._prin = "http://xmlns.fmr.com/institutional/common/headers/2012/09/PrincipalIdentity"
        self._prod = "http://xmlns.fmr.com/institutional/common/headers/2011/08/ProductIdentity"
        self._alerts = "http://xmlns.fmr.com/brokerage/fens/service/ALERTS/2009-09"

    def test_returns_bytes(self):
        assert isinstance(self.xml_bytes, bytes)

    def test_is_valid_xml(self):
        # Should not raise
        ET.fromstring(self.xml_bytes)

    def test_root_is_envelope(self):
        assert self.root.tag == f"{{{self._soap}}}Envelope"

    def test_has_header_and_body(self):
        header = self.root.find(f"{{{self._soap}}}Header")
        body = self.root.find(f"{{{self._soap}}}Body")
        assert header is not None
        assert body is not None

    def test_principal_identity_fields(self):
        header = self.root.find(f"{{{self._soap}}}Header")
        prin = header.find(f"{{{self._prin}}}PrincipalIdentity")
        assert prin is not None
        assert prin.find(f"{{{self._prin}}}RequestorId").text == "Fidelity"
        assert prin.find(f"{{{self._prin}}}AuthMethod").text == "Basic"
        assert prin.find(f"{{{self._prin}}}PrincipalDomain").text == "Retail"
        assert prin.find(f"{{{self._prin}}}RequestorType").text == "Standard"
        assert prin.find(f"{{{self._prin}}}PrincipalRole").text == "Owner"

    def test_product_identity_fields(self):
        header = self.root.find(f"{{{self._soap}}}Header")
        prod = header.find(f"{{{self._prod}}}ProductIdentity")
        assert prod is not None
        assert prod.find(f"{{{self._prod}}}AppId").text == "AP002304"
        assert prod.find(f"{{{self._prod}}}AppName").text == "ATP"
        assert prod.find(f"{{{self._prod}}}AppVersion").text == "4.5.1"
        assert prod.find(f"{{{self._prod}}}ProductId").text == "ATP"
        assert prod.find(f"{{{self._prod}}}SubSystem").text == "ActiveTrader"

    def test_body_contains_get_alerts(self):
        body = self.root.find(f"{{{self._soap}}}Body")
        get_alerts = body.find(f"{{{self._alerts}}}GetAlerts")
        assert get_alerts is not None

    def test_default_msg_index_range(self):
        body = self.root.find(f"{{{self._soap}}}Body")
        get_alerts = body.find(f"{{{self._alerts}}}GetAlerts")
        msg_from = get_alerts.find(f"{{{self._alerts}}}MsgIndexFrom")
        msg_to = get_alerts.find(f"{{{self._alerts}}}MsgIndexTo")
        assert msg_from is not None
        assert msg_to is not None
        assert msg_from.text == "1"
        assert msg_to.text == "100"

    def test_custom_msg_index_range(self):
        xml_bytes = _build_get_alerts_envelope(msg_from=5, msg_to=25)
        root = ET.fromstring(xml_bytes)
        body = root.find(f"{{{self._soap}}}Body")
        get_alerts = body.find(f"{{{self._alerts}}}GetAlerts")
        msg_from = get_alerts.find(f"{{{self._alerts}}}MsgIndexFrom")
        msg_to = get_alerts.find(f"{{{self._alerts}}}MsgIndexTo")
        assert msg_from.text == "5"
        assert msg_to.text == "25"


# ---------------------------------------------------------------------------
# AlertsAPI.get_alerts HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestAlertsAPIGetAlerts:
    @respx.mock
    def test_get_alerts_posts_to_correct_url(self):
        resp_bytes = _build_get_alerts_soap_response(1, [_EXECUTION_ALERT_XML])
        route = respx.post(_ALERTS_URL_FULL).mock(
            return_value=httpx.Response(200, content=resp_bytes)
        )
        api = AlertsAPI(httpx.Client())
        api.get_alerts()
        assert route.called
        assert str(route.calls[0].request.url) == _ALERTS_URL_FULL

    @respx.mock
    def test_get_alerts_returns_alerts_response(self):
        resp_bytes = _build_get_alerts_soap_response(1, [_EXECUTION_ALERT_XML])
        respx.post(_ALERTS_URL_FULL).mock(
            return_value=httpx.Response(200, content=resp_bytes)
        )
        api = AlertsAPI(httpx.Client())
        result = api.get_alerts()
        assert isinstance(result, AlertsResponse)

    @respx.mock
    def test_get_alerts_returns_correct_messages(self):
        resp_bytes = _build_get_alerts_soap_response(
            2, [_EXECUTION_ALERT_XML, _CANCELLATION_ALERT_XML]
        )
        respx.post(_ALERTS_URL_FULL).mock(
            return_value=httpx.Response(200, content=resp_bytes)
        )
        api = AlertsAPI(httpx.Client())
        result = api.get_alerts()
        assert result.total_count == 2
        assert len(result.messages) == 2
        assert result.messages[0].is_execution is True
        assert result.messages[1].is_cancellation is True

    @respx.mock
    def test_get_alerts_sends_correct_content_type(self):
        resp_bytes = _build_get_alerts_soap_response(0, [])
        route = respx.post(_ALERTS_URL_FULL).mock(
            return_value=httpx.Response(200, content=resp_bytes)
        )
        api = AlertsAPI(httpx.Client())
        api.get_alerts()
        request = route.calls[0].request
        assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"

    @respx.mock
    def test_get_alerts_sends_xml_body_with_get_alerts(self):
        resp_bytes = _build_get_alerts_soap_response(0, [])
        route = respx.post(_ALERTS_URL_FULL).mock(
            return_value=httpx.Response(200, content=resp_bytes)
        )
        api = AlertsAPI(httpx.Client())
        api.get_alerts()
        request = route.calls[0].request
        root = ET.fromstring(request.content)
        ns_soap = "http://schemas.xmlsoap.org/soap/envelope/"
        ns_alerts = "http://xmlns.fmr.com/brokerage/fens/service/ALERTS/2009-09"
        body = root.find(f"{{{ns_soap}}}Body")
        get_alerts = body.find(f"{{{ns_alerts}}}GetAlerts")
        assert get_alerts is not None

    @respx.mock
    def test_get_alerts_passes_custom_range(self):
        resp_bytes = _build_get_alerts_soap_response(0, [])
        route = respx.post(_ALERTS_URL_FULL).mock(
            return_value=httpx.Response(200, content=resp_bytes)
        )
        api = AlertsAPI(httpx.Client())
        api.get_alerts(msg_from=10, msg_to=50)
        request = route.calls[0].request
        root = ET.fromstring(request.content)
        ns_soap = "http://schemas.xmlsoap.org/soap/envelope/"
        ns_alerts = "http://xmlns.fmr.com/brokerage/fens/service/ALERTS/2009-09"
        body = root.find(f"{{{ns_soap}}}Body")
        get_alerts = body.find(f"{{{ns_alerts}}}GetAlerts")
        msg_from = get_alerts.find(f"{{{ns_alerts}}}MsgIndexFrom")
        msg_to = get_alerts.find(f"{{{ns_alerts}}}MsgIndexTo")
        assert msg_from.text == "10"
        assert msg_to.text == "50"

    @respx.mock
    def test_get_alerts_raises_on_401(self):
        respx.post(_ALERTS_URL_FULL).mock(return_value=httpx.Response(401))
        api = AlertsAPI(httpx.Client())
        with pytest.raises(httpx.HTTPStatusError):
            api.get_alerts()

    @respx.mock
    def test_get_alerts_raises_on_500(self):
        respx.post(_ALERTS_URL_FULL).mock(return_value=httpx.Response(500))
        api = AlertsAPI(httpx.Client())
        with pytest.raises(httpx.HTTPStatusError):
            api.get_alerts()

    @respx.mock
    def test_get_alerts_empty_response(self):
        resp_bytes = _build_get_alerts_soap_response(0, [])
        respx.post(_ALERTS_URL_FULL).mock(
            return_value=httpx.Response(200, content=resp_bytes)
        )
        api = AlertsAPI(httpx.Client())
        result = api.get_alerts()
        assert result.total_count == 0
        assert result.messages == []

    @respx.mock
    def test_get_alerts_does_not_send_soap_action_header(self):
        """GetAlerts does not use a SOAPAction header (unlike subscribe)."""
        resp_bytes = _build_get_alerts_soap_response(0, [])
        route = respx.post(_ALERTS_URL_FULL).mock(
            return_value=httpx.Response(200, content=resp_bytes)
        )
        api = AlertsAPI(httpx.Client())
        api.get_alerts()
        request = route.calls[0].request
        assert "SOAPAction" not in request.headers
