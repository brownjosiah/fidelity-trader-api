"""Shared parsing helpers for Pydantic model field coercion."""
from __future__ import annotations

from typing import Any, Optional


def _parse_float(v: Any) -> Optional[float]:
    """Convert a raw API value to float, handling None / sentinel strings."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s in ("", "--", "N/A"):
        return None
    # Remove thousands separators before converting
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_int(v: Any) -> Optional[int]:
    """Convert a raw API value to int, handling None / sentinel strings."""
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    s = str(v).strip()
    if s in ("", "--", "N/A"):
        return None
    s = s.replace(",", "")
    try:
        return int(float(s))
    except ValueError:
        return None
