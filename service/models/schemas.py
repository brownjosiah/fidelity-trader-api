"""Pydantic schemas for OpenAPI response typing.

Contains two categories:
1. Mirror models for SDK dataclass types (used with asdict() in routes)
2. Inline response schemas for ad-hoc dict returns
"""

from __future__ import annotations

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Inline dict response schemas
# ---------------------------------------------------------------------------

class HealthCheckData(BaseModel):
    status: str


class ServiceInfoData(BaseModel):
    version: str
    sdk_version: str
    session_state: str


class AuthStatusData(BaseModel):
    state: str
    is_authenticated: bool


class CredentialStoredData(BaseModel):
    stored: bool


class CredentialDeletedData(BaseModel):
    deleted: bool


class StreamingSubscribedData(BaseModel):
    subscribed: list[str]


class StreamingUnsubscribedData(BaseModel):
    unsubscribed: list[str]


class StreamingSubscriptionsData(BaseModel):
    subscriptions: dict


class StreamingStatusData(BaseModel):
    connected: bool
    consumers: int
    subscriptions: int


# ---------------------------------------------------------------------------
# Dataclass mirror: OptionChain (from models/fastquote.py)
# ---------------------------------------------------------------------------

class ChainOptionSchema(BaseModel):
    symbol: str
    contract_symbol: str
    strike: float
    expiry_type: str


class ChainExpirationSchema(BaseModel):
    date: str
    options: list[ChainOptionSchema] = []


class OptionChainSchema(BaseModel):
    symbol: str
    calls: list[ChainExpirationSchema] = []
    puts: list[ChainExpirationSchema] = []


# ---------------------------------------------------------------------------
# Dataclass mirror: Montage (from models/fastquote.py)
# ---------------------------------------------------------------------------

class MontageQuoteSchema(BaseModel):
    symbol: str
    exchange_name: str
    exchange_code: str
    bid: float
    bid_size: int
    ask: float
    ask_size: int


class MontageSchema(BaseModel):
    symbol: str
    contract_symbol: str
    expiration: str
    strike: float
    call_put: str
    quotes: list[MontageQuoteSchema] = []


# ---------------------------------------------------------------------------
# Dataclass mirror: Chart (from models/chart.py)
# ---------------------------------------------------------------------------

class ChartBarSchema(BaseModel):
    timestamp: str
    open: float
    close: float
    high: float
    low: float
    volume: int


class ChartSymbolInfoSchema(BaseModel):
    identifier: str
    description: str
    last_trade: float
    trade_date: str
    day_open: float
    day_high: float
    day_low: float
    net_change: float
    net_change_pct: float
    previous_close: float


class ChartSchema(BaseModel):
    symbol_info: ChartSymbolInfoSchema
    bars: list[ChartBarSchema] = []


# ---------------------------------------------------------------------------
# Dataclass mirror: ScanResult (from models/screener.py)
# ---------------------------------------------------------------------------

class ScanFieldSchema(BaseModel):
    display_name: str
    value: str
    description_id: str


class ScanRowSchema(BaseModel):
    fields: list[ScanFieldSchema] = []


class ScanResultSchema(BaseModel):
    rows: list[ScanRowSchema] = []


# ---------------------------------------------------------------------------
# Dataclass mirror: AlertActivation (from models/alerts.py)
# ---------------------------------------------------------------------------

class AlertActivationSchema(BaseModel):
    result_code: str
    activation_status: str
    user_id: str
    password: str
    server_url: str
    destination: str
