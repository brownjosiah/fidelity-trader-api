"""MDDS WebSocket field ID to name mapping.

Reverse-engineered from captured Fidelity Trader+ WebSocket traffic.
Field IDs are strings (the API uses string keys, not integers).
"""

# Core quote fields (equities + indices)
EQUITY_FIELDS = {
    "0": "status",
    "1": "security_name",
    "6": "symbol",
    "7": "cusip",
    "10": "symbol_root",
    "12": "net_change",
    "13": "net_change_pct",
    "14": "fifty_two_week_high",
    "15": "fifty_two_week_high_date",
    "16": "fifty_two_week_low",
    "17": "fifty_two_week_low_date",
    "18": "open",
    "19": "ask_size",
    "20": "bid",
    "21": "bid_size",
    "22": "num_trades",
    "23": "volume",
    "24": "trade_date",
    "25": "currency",
    "26": "day_high",
    "27": "day_low",
    "29": "previous_close",
    "31": "ask",
    "32": "close_price",
    "33": "total_volume",
    "57": "market_cap",
    "80": "full_description",
    "100": "exchange_code",
    "112": "last_trade_date",
    "113": "after_hours_price",
    "118": "industry",
    "119": "sector_group",
    "124": "last_price",
    "127": "sector",
    "128": "security_type",
    "129": "shares_outstanding",
    "166": "day_volume",
    "169": "data_quality",
    "194": "short_interest_pct",
    "277": "pre_market_price",
    "278": "pre_market_bid",
    "289": "display_symbol",
}

# Option-specific fields
OPTION_FIELDS = {
    **EQUITY_FIELDS,
    "60": "mid_price",
    "120": "option_description",
    "177": "option_high",
    "178": "option_high_volume",
    "179": "option_high_date",
    "180": "option_low_date",
    "181": "adjusted_ind",
    "182": "contract_size",
    "183": "open_interest",
    "184": "strike_price",
    "185": "underlying_symbol",
    "187": "delta",
    "188": "gamma",
    "189": "vega",
    "190": "theta",
    "191": "rho",
    "193": "premium",
    "195": "implied_volatility",
    "196": "historical_volatility",
    "197": "call_put",
    "198": "shares_per_contract",
    "199": "expiration_date",
    "252": "option_last_trade_date",
    "290": "intrinsic_value",
    "292": "expiration_date_alt",
    "302": "contract_root_symbol",
}

ALL_FIELDS = {**EQUITY_FIELDS, **OPTION_FIELDS}


def parse_fields(raw_data: dict, field_map: dict = None) -> dict:
    """Convert numbered field dict to named dict.

    Unknown fields are kept as-is with their numeric key prefixed with 'field_'.
    """
    if field_map is None:
        # Auto-detect: if field 184 (strike) exists, use option fields
        field_map = OPTION_FIELDS if "184" in raw_data else EQUITY_FIELDS

    result = {}
    for k, v in raw_data.items():
        name = field_map.get(k, f"field_{k}")
        result[name] = v
    return result
