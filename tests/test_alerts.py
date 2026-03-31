"""Tests for the alerts subscription SOAP API."""
from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx
import pytest
import respx

from fidelity_trader._http import ALERTS_URL
from fidelity_trader.alerts.subscription import AlertsAPI, _build_soap_envelope
from fidelity_trader.models.alerts import AlertActivation

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
