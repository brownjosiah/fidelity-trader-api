"""Alerts subscription API — wraps the ATBTSubscription SOAP endpoint."""
from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from fidelity_trader._http import ALERTS_URL
from fidelity_trader.models.alerts import AlertActivation

_SUBSCRIBE_PATH = "/ftgw/alerts/services/ATBTSubscription"

# XML namespaces (match the captured request exactly)
_NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
_NS_PROD = "http://xmlns.fmr.com/institutional/common/headers/2011/08/ProductIdentity"
_NS_PRIN = "http://xmlns.fmr.com/institutional/common/headers/2012/09/PrincipalIdentity"
_NS_AUT = "http://xmlns.fmr.com/institutional/eca/fens/2014/06/AutoSubscription"


def _build_soap_envelope() -> bytes:
    """Build the CustomerSignOn SOAP request body as UTF-8 bytes."""
    # Register namespace prefixes so ElementTree uses clean tags
    ET.register_namespace("soapenv", _NS_SOAP)
    ET.register_namespace("prod", _NS_PROD)
    ET.register_namespace("prin", _NS_PRIN)
    ET.register_namespace("aut", _NS_AUT)

    envelope = ET.Element(f"{{{_NS_SOAP}}}Envelope")

    # --- Header ---
    header = ET.SubElement(envelope, f"{{{_NS_SOAP}}}Header")

    principal = ET.SubElement(header, f"{{{_NS_PRIN}}}PrincipalIdentity")
    ET.SubElement(principal, f"{{{_NS_PRIN}}}RequestorId").text = "fidelity"
    ET.SubElement(principal, f"{{{_NS_PRIN}}}AuthMethod").text = "Basic"
    ET.SubElement(principal, f"{{{_NS_PRIN}}}PrincipalDomain").text = "Retail"
    ET.SubElement(principal, f"{{{_NS_PRIN}}}PrincipalRole").text = "Owner"

    product = ET.SubElement(header, f"{{{_NS_PROD}}}ProductIdentity")
    ET.SubElement(product, f"{{{_NS_PROD}}}AppId").text = "AP002304"
    ET.SubElement(product, f"{{{_NS_PROD}}}AppName").text = "ATP"
    ET.SubElement(product, f"{{{_NS_PROD}}}AppVersion").text = "0.0.1"
    ET.SubElement(product, f"{{{_NS_PROD}}}ProductId").text = "ATP"
    ET.SubElement(product, f"{{{_NS_PROD}}}SubSystem").text = "ActiveTrader"

    # --- Body ---
    body = ET.SubElement(envelope, f"{{{_NS_SOAP}}}Body")
    sign_on = ET.SubElement(body, f"{{{_NS_AUT}}}CustomerSignOn")
    ET.SubElement(sign_on, f"{{{_NS_AUT}}}AlertCode").text = "ATBT"

    return ET.tostring(envelope, encoding="unicode", xml_declaration=False).encode("utf-8")


class AlertsAPI:
    """Client for the Fidelity alerts subscription (ATBTSubscription) SOAP service."""

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def subscribe(self) -> AlertActivation:
        """Subscribe to ATP/ATBT alerts.

        POSTs the ``CustomerSignOn`` SOAP envelope to the ATBTSubscription
        endpoint.  Returns an :class:`~fidelity_trader.models.alerts.AlertActivation`
        containing the STOMP/JMS credentials and server URL needed to connect
        to the real-time alert stream.

        Raises:
            httpx.HTTPStatusError: on non-2xx responses.
            ValueError: if the SOAP response cannot be parsed.
        """
        soap_body = _build_soap_envelope()
        resp = self._http.post(
            f"{ALERTS_URL}{_SUBSCRIBE_PATH}",
            content=soap_body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "SOAPAction": "CustomerSignOn",
            },
        )
        resp.raise_for_status()
        return AlertActivation.from_xml(resp.content)
