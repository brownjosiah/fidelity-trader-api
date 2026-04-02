"""Models for LiveVol screener/scanner responses.

The screener uses LiveVol's API (integrated into Fidelity Trader+).
Scan results come back as XML with a generic Field-based row structure.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LiveVolSession:
    """Session returned by the LiveVol SAML login exchange."""

    sid: str
    token: str
    expires_at: int


@dataclass
class ScanField:
    """A single field within a scan result row."""

    display_name: str
    value: str
    description_id: str

    @classmethod
    def from_element(cls, elem: ET.Element) -> "ScanField":
        return cls(
            display_name=elem.get("displayName", ""),
            value=elem.get("value", ""),
            description_id=elem.get("descriptionId", ""),
        )


@dataclass
class ScanRow:
    """A single row of scan results with dict-like access by display name."""

    fields: list[ScanField] = field(default_factory=list)

    def __getitem__(self, display_name: str) -> str:
        """Access field value by display name, e.g. row['Symbol']."""
        for f in self.fields:
            if f.display_name == display_name:
                return f.value
        raise KeyError(display_name)

    def get(self, display_name: str, default: Optional[str] = None) -> Optional[str]:
        """Access field value by display name with a default."""
        for f in self.fields:
            if f.display_name == display_name:
                return f.value
        return default

    @classmethod
    def from_element(cls, elem: ET.Element) -> "ScanRow":
        fields_elem = elem.find("Fields")
        if fields_elem is None:
            return cls()
        fields = [ScanField.from_element(f) for f in fields_elem.findall("Field")]
        return cls(fields=fields)


@dataclass
class ScanResult:
    """Parsed result from an ExecuteScan response."""

    rows: list[ScanRow] = field(default_factory=list)

    @property
    def symbols(self) -> list[str]:
        """List of symbol values from all rows."""
        result = []
        for row in self.rows:
            sym = row.get("Symbol")
            if sym is not None:
                result.append(sym)
        return result

    @classmethod
    def from_xml(cls, xml_text: str) -> "ScanResult":
        """Parse XML response from ExecuteScan endpoint."""
        root = ET.fromstring(xml_text)
        scan_result = root.find(".//ScanResult")
        if scan_result is None:
            return cls()
        rows = [ScanRow.from_element(r) for r in scan_result.findall("Row")]
        return cls(rows=rows)
