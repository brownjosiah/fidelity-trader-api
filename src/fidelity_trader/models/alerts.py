"""Dataclass models for the alerts subscription (SOAP) API."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

# XML namespace used in the CustomerSignOnResponse body
_NS = "http://xmlns.fmr.com/institutional/eca/fens/2014/06/AutoSubscription"


@dataclass
class AlertActivation:
    """Parsed result of a successful ATBTSubscription CustomerSignOn call."""

    result_code: str
    activation_status: str
    user_id: str
    password: str
    server_url: str
    destination: str

    @property
    def is_success(self) -> bool:
        return self.result_code == "SUCCESS"

    @classmethod
    def from_xml(cls, xml_bytes: bytes) -> "AlertActivation":
        """Parse an AlertActivation from the raw SOAP response bytes.

        Handles the ``p971:CustomerSignOnResponse`` body returned by
        ``POST /ftgw/alerts/services/ATBTSubscription``.
        """
        root = ET.fromstring(xml_bytes)

        # Walk down: Envelope -> Body -> CustomerSignOnResponse
        body = root.find("{http://schemas.xmlsoap.org/soap/envelope/}Body")
        if body is None:
            raise ValueError("SOAP Body element not found in response")

        response = body.find(f"{{{_NS}}}CustomerSignOnResponse")
        if response is None:
            raise ValueError("CustomerSignOnResponse element not found in SOAP Body")

        def _text(tag: str) -> str:
            el = response.find(f"{{{_NS}}}{tag}")
            if el is None or el.text is None:
                raise ValueError(f"Missing element <{tag}> in CustomerSignOnResponse")
            return el.text

        activation = response.find(f"{{{_NS}}}ActivationDetails")
        if activation is None:
            raise ValueError("ActivationDetails element not found")

        def _detail(tag: str) -> str:
            el = activation.find(f"{{{_NS}}}{tag}")
            if el is None:
                raise ValueError(f"Missing element <{tag}> in ActivationDetails")
            return el.text or ""

        return cls(
            result_code=_text("ResultCode"),
            activation_status=_detail("ActivationStatus"),
            user_id=_detail("UserId"),
            password=_detail("Password"),
            server_url=_detail("ServerUrl"),
            destination=_detail("Destination"),
        )
