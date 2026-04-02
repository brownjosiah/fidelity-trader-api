"""Dataclass models for the alerts subscription (SOAP) API."""
from __future__ import annotations

import html
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List

# XML namespace used in the CustomerSignOnResponse body
_NS = "http://xmlns.fmr.com/institutional/eca/fens/2014/06/AutoSubscription"

# XML namespace used in the GetAlertsResponse body
_NS_ALERTS = "http://xmlns.fmr.com/brokerage/fens/service/ALERTS/2009-09"
_NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"


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


@dataclass
class AlertMessage:
    """A single parsed alert message (order fill, cancellation, etc.)."""

    msg_id: str
    msg_type: str
    priority: str
    timestamp: str
    display_text: str
    display_symbol: str
    account_num: str
    order_action: str
    order_num: str
    order_status: str
    symbol: str
    quantity: str
    executed_qty: str
    price: str
    avg_price: str
    exec_date: str
    exchange: str
    gross_amount: str
    sec_type: str
    raw_xml: str

    @property
    def is_execution(self) -> bool:
        """True if this alert is an order execution/fill (MSG_TYPE == MFCEX)."""
        return self.msg_type == "MFCEX"

    @property
    def is_cancellation(self) -> bool:
        """True if this alert is an order cancellation (MSG_TYPE == CXL01)."""
        return self.msg_type == "CXL01"

    @classmethod
    def from_xml(cls, document_text: str) -> "AlertMessage":
        """Parse an AlertMessage from a decoded ALERT XML document.

        ``document_text`` should be the HTML-entity-decoded content of a
        ``<Document>`` element from the GetAlertsResponse.
        """
        root = ET.fromstring(document_text)

        def _hdr(tag: str) -> str:
            el = root.find(f"MSG_HDR/{tag}")
            return el.text if el is not None and el.text else ""

        def _disp(tag: str) -> str:
            el = root.find(f"DISPLAY_DETAIL/{tag}")
            return el.text if el is not None and el.text else ""

        def _detail(tag: str) -> str:
            el = root.find(f"MSG_DETAIL/{tag}")
            return el.text if el is not None and el.text else ""

        return cls(
            msg_id=_hdr("MSG_ID"),
            msg_type=_hdr("MSG_TYPE"),
            priority=_hdr("MSG_PRIORITY"),
            timestamp=_hdr("ALERT_PUBLISHER_TMST"),
            display_text=_disp("DISPLAY_DATA"),
            display_symbol=_disp("DISPLAY_SYMBOL"),
            account_num=_detail("ACCOUNT_NUM"),
            order_action=_detail("ORDER_ACTION"),
            order_num=_detail("ORDER_NUM"),
            order_status=_detail("ORDER_STATUS"),
            symbol=_detail("DISP_MSG_SYMBOL"),
            quantity=_detail("ORIGINAL_QTY"),
            executed_qty=_detail("EXECUTED_QTY"),
            price=_detail("PRICE"),
            avg_price=_detail("AVG_PRICE"),
            exec_date=_detail("EXEC_DATE"),
            exchange=_detail("EXCH_CODE"),
            gross_amount=_detail("GROSS_AMT"),
            sec_type=_detail("SEC_TYPE"),
            raw_xml=document_text,
        )


@dataclass
class AlertsResponse:
    """Parsed result of a GetAlerts SOAP response."""

    total_count: int
    messages: List[AlertMessage]

    @classmethod
    def from_soap_response(cls, response_bytes: bytes) -> "AlertsResponse":
        """Parse an AlertsResponse from raw SOAP response bytes.

        Handles the ``GetAlertsResponse`` body returned by
        ``POST /ftgw/alerts/services/ATBTAlerts``.  Each ``<Document>``
        element contains HTML-entity-encoded XML which is decoded and
        parsed into an :class:`AlertMessage`.
        """
        root = ET.fromstring(response_bytes)

        body = root.find(f"{{{_NS_SOAP}}}Body")
        if body is None:
            raise ValueError("SOAP Body element not found in response")

        response = body.find(f"{{{_NS_ALERTS}}}GetAlertsResponse")
        if response is None:
            raise ValueError("GetAlertsResponse element not found in SOAP Body")

        count_el = response.find(f"{{{_NS_ALERTS}}}TotalMsgCount")
        if count_el is None or count_el.text is None:
            raise ValueError("TotalMsgCount element not found in GetAlertsResponse")
        total_count = int(count_el.text)

        messages: List[AlertMessage] = []
        messages_el = response.find(f"{{{_NS_ALERTS}}}Messages")
        if messages_el is not None:
            for msg_el in messages_el.findall(f"{{{_NS_ALERTS}}}Message"):
                doc_el = msg_el.find(f"{{{_NS_ALERTS}}}Document")
                if doc_el is not None and doc_el.text:
                    decoded = html.unescape(doc_el.text)
                    messages.append(AlertMessage.from_xml(decoded))

        return cls(total_count=total_count, messages=messages)
