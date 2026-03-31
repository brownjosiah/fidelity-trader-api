"""Tests for the MDDS WebSocket field mapping and streaming client."""
import json
import pytest

from fidelity_trader.streaming.mdds_fields import (
    EQUITY_FIELDS,
    OPTION_FIELDS,
    TIME_SALES_FIELDS,
    ALL_FIELDS,
    parse_fields,
)
from fidelity_trader.streaming.mdds import (
    MDDSClient,
    MDDSQuote,
    MDDSSession,
    MDDS_URL,
)


# ---------------------------------------------------------------------------
# Captured WebSocket fixtures
# ---------------------------------------------------------------------------

CONNECT_MSG = '{"Message":"success","SessionId":"a21af247-1f51-4ad4-a8ed-a16df58a352e","Status":"Ok","host":"7f5d436d3043.us-east-2a","productid":"atn"}'

SUCCESS_MSG = '{"Command":"subscribe","ResponseType":"1","Data":[{"0":"success","1":"Rocket Lab","6":"RKLB","10":"RKLB","12":"-3.55","13":"-5.8264","14":"99.58","16":"14.71","18":"56.73","19":"200","20":"56.6","21":"100","23":"2969239","24":"2026-03-30","25":"USD","26":"61.64","27":"56.132","29":"57.38","31":"61.45","32":"60.93","33":"21933537","57":"34694009211.24","80":"ROCKET LAB CORP COM","100":"ARCX","124":"57.38","127":"Industrials","128":"EQ","129":"569407668","166":"23730952","169":"realtime"}],"Delay":"8.513486ms","Request":"0ba9bd91"}'

OPTION_MSG = '{"Command":"subscribe","ResponseType":"1","Data":[{"0":"success","1":"EVGO JAN 15 2027 $7 CALL","6":"-EVGO270115C7.GK","120":"EVGO INC JAN 15 2027 $7 CALL","128":"OP","169":"realtime","182":"100","184":"7","185":"EVGO","187":"0.0863","188":"0.12568","189":"0.00236","190":"-0.00033","191":"0.00083","193":"0.0361","195":"1.55945","196":"1.25337","197":"C","199":"2027-01-15","290":"0.8291","302":"EVGO"}],"Delay":"8.812943ms","Request":"0ba9bd91"}'

ERROR_MSG = '{"Command":"subscribe","ResponseType":"-1","ErrorCode":"18","Data":[{"0":"Source not found","6":"-SPXW260217P6750"}],"Delay":"917.238µs","Request":"0ba9bd91"}'

STREAMING_UPDATE_MSG = '{"ResponseType":"0","Data":[{"6":"AAPL","124":"195.50","20":"195.40","31":"195.60","128":"EQ","1159":"195.45","1160":"300","1161":"14:30:05","1162":"XNGS","1163":"@","1164":"U","1165":"12345678"}]}'


# ---------------------------------------------------------------------------
# parse_fields tests
# ---------------------------------------------------------------------------

class TestParseFields:
    def test_equity_key_field_names(self):
        raw = {"6": "AAPL", "124": "175.50", "20": "175.40", "31": "175.60", "128": "EQ"}
        result = parse_fields(raw, EQUITY_FIELDS)
        assert result["symbol"] == "AAPL"
        assert result["last_price"] == "175.50"
        assert result["bid"] == "175.40"
        assert result["ask"] == "175.60"
        assert result["security_type"] == "EQ"

    def test_option_greeks_mapping(self):
        raw = {
            "184": "7",
            "187": "0.0863",
            "188": "0.12568",
            "189": "0.00236",
            "190": "-0.00033",
            "191": "0.00083",
            "197": "C",
            "199": "2027-01-15",
        }
        result = parse_fields(raw, OPTION_FIELDS)
        assert result["strike_price"] == "7"
        assert result["delta"] == "0.0863"
        assert result["gamma"] == "0.12568"
        assert result["vega"] == "0.00236"
        assert result["theta"] == "-0.00033"
        assert result["rho"] == "0.00083"
        assert result["call_put"] == "C"
        assert result["expiration_date"] == "2027-01-15"

    def test_auto_detect_equity(self):
        # No field 184 → equity fields used
        raw = {"6": "RKLB", "124": "57.38", "128": "EQ"}
        result = parse_fields(raw)
        assert result["symbol"] == "RKLB"
        assert result["last_price"] == "57.38"
        assert result["security_type"] == "EQ"

    def test_auto_detect_option(self):
        # Field 184 present → option fields used
        raw = {"6": "-EVGO270115C7.GK", "184": "7", "187": "0.0863"}
        result = parse_fields(raw)
        assert result["strike_price"] == "7"
        assert result["delta"] == "0.0863"

    def test_unknown_fields_get_field_prefix(self):
        raw = {"6": "AAPL", "9999": "mystery_value"}
        result = parse_fields(raw, EQUITY_FIELDS)
        assert "field_9999" in result
        assert result["field_9999"] == "mystery_value"

    def test_unknown_fields_with_auto_detect(self):
        raw = {"6": "AAPL", "888": "unknown", "999": "also_unknown"}
        result = parse_fields(raw)
        assert result["field_888"] == "unknown"
        assert result["field_999"] == "also_unknown"

    def test_all_equity_fields_present(self):
        # Spot-check a broad set of equity field mappings
        raw = {
            "0": "success",
            "1": "Rocket Lab",
            "12": "-3.55",
            "13": "-5.8264",
            "18": "56.73",
            "23": "2969239",
            "25": "USD",
            "26": "61.64",
            "27": "56.132",
            "29": "57.38",
            "32": "60.93",
            "33": "21933537",
            "57": "34694009211.24",
            "169": "realtime",
        }
        result = parse_fields(raw, EQUITY_FIELDS)
        assert result["status"] == "success"
        assert result["security_name"] == "Rocket Lab"
        assert result["net_change"] == "-3.55"
        assert result["net_change_pct"] == "-5.8264"
        assert result["open"] == "56.73"
        assert result["volume"] == "2969239"
        assert result["currency"] == "USD"
        assert result["day_high"] == "61.64"
        assert result["day_low"] == "56.132"
        assert result["previous_close"] == "57.38"
        assert result["close_price"] == "60.93"
        assert result["total_volume"] == "21933537"
        assert result["market_cap"] == "34694009211.24"
        assert result["data_quality"] == "realtime"

    def test_option_additional_fields(self):
        raw = {
            "120": "EVGO INC JAN 15 2027 $7 CALL",
            "182": "100",
            "183": "500",
            "193": "0.0361",
            "195": "1.55945",
            "196": "1.25337",
            "290": "0.8291",
            "302": "EVGO",
        }
        result = parse_fields(raw, OPTION_FIELDS)
        assert result["option_description"] == "EVGO INC JAN 15 2027 $7 CALL"
        assert result["contract_size"] == "100"
        assert result["open_interest"] == "500"
        assert result["premium"] == "0.0361"
        assert result["implied_volatility"] == "1.55945"
        assert result["historical_volatility"] == "1.25337"
        assert result["intrinsic_value"] == "0.8291"
        assert result["contract_root_symbol"] == "EVGO"

    def test_empty_dict(self):
        result = parse_fields({})
        assert result == {}

    def test_explicit_none_field_map_uses_auto_detect(self):
        raw = {"6": "TSLA", "124": "200.00"}
        result = parse_fields(raw, field_map=None)
        assert result["symbol"] == "TSLA"
        assert result["last_price"] == "200.00"


# ---------------------------------------------------------------------------
# MDDSClient.handle_connect_message tests
# ---------------------------------------------------------------------------

class TestHandleConnectMessage:
    def test_parses_session_id(self):
        client = MDDSClient()
        session = client.handle_connect_message(CONNECT_MSG)
        assert session.session_id == "a21af247-1f51-4ad4-a8ed-a16df58a352e"

    def test_parses_host(self):
        client = MDDSClient()
        session = client.handle_connect_message(CONNECT_MSG)
        assert session.host == "7f5d436d3043.us-east-2a"

    def test_connected_true_on_ok_status(self):
        client = MDDSClient()
        session = client.handle_connect_message(CONNECT_MSG)
        assert session.connected is True

    def test_connected_false_on_non_ok_status(self):
        client = MDDSClient()
        msg = json.dumps({"Message": "error", "SessionId": "abc", "Status": "Error", "host": "host1"})
        session = client.handle_connect_message(msg)
        assert session.connected is False

    def test_session_id_accessible_via_property(self):
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)
        assert client.session_id == "a21af247-1f51-4ad4-a8ed-a16df58a352e"

    def test_is_connected_property_updated(self):
        client = MDDSClient()
        assert client.is_connected is False
        client.handle_connect_message(CONNECT_MSG)
        assert client.is_connected is True

    def test_returns_mdds_session_instance(self):
        client = MDDSClient()
        result = client.handle_connect_message(CONNECT_MSG)
        assert isinstance(result, MDDSSession)


# ---------------------------------------------------------------------------
# MDDSClient.build_subscribe_message tests
# ---------------------------------------------------------------------------

class TestBuildSubscribeMessage:
    def _client_with_session(self) -> MDDSClient:
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)
        return client

    def test_command_is_subscribe(self):
        client = self._client_with_session()
        msg = json.loads(client.build_subscribe_message([".SPX", "AAPL"]))
        assert msg["Command"] == "subscribe"

    def test_symbols_joined_with_comma(self):
        client = self._client_with_session()
        msg = json.loads(client.build_subscribe_message([".SPX", "AAPL", "RKLB"]))
        assert msg["Symbol"] == ".SPX,AAPL,RKLB"

    def test_session_id_included(self):
        client = self._client_with_session()
        msg = json.loads(client.build_subscribe_message(["AAPL"]))
        assert msg["SessionId"] == "a21af247-1f51-4ad4-a8ed-a16df58a352e"

    def test_default_conflation_rate(self):
        client = self._client_with_session()
        msg = json.loads(client.build_subscribe_message(["AAPL"]))
        assert msg["ConflationRate"] == 1000

    def test_custom_conflation_rate(self):
        client = self._client_with_session()
        msg = json.loads(client.build_subscribe_message(["AAPL"], conflation_rate=500))
        assert msg["ConflationRate"] == 500

    def test_include_greeks_true_by_default(self):
        client = self._client_with_session()
        msg = json.loads(client.build_subscribe_message(["AAPL"]))
        assert msg["IncludeGreeks"] is True

    def test_include_greeks_false(self):
        client = self._client_with_session()
        msg = json.loads(client.build_subscribe_message(["AAPL"], include_greeks=False))
        assert msg["IncludeGreeks"] is False

    def test_single_symbol(self):
        client = self._client_with_session()
        msg = json.loads(client.build_subscribe_message([".SPX"]))
        assert msg["Symbol"] == ".SPX"

    def test_returns_valid_json_string(self):
        client = self._client_with_session()
        raw = client.build_subscribe_message(["AAPL"])
        assert isinstance(raw, str)
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# MDDSClient.build_unsubscribe_message tests
# ---------------------------------------------------------------------------

class TestBuildUnsubscribeMessage:
    def _client_with_session(self) -> MDDSClient:
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)
        return client

    def test_command_is_unsubscribe(self):
        client = self._client_with_session()
        msg = json.loads(client.build_unsubscribe_message(["AAPL"]))
        assert msg["Command"] == "unsubscribe"

    def test_symbols_joined_with_comma(self):
        client = self._client_with_session()
        msg = json.loads(client.build_unsubscribe_message(["AAPL", "RKLB"]))
        assert msg["Symbol"] == "AAPL,RKLB"

    def test_session_id_included(self):
        client = self._client_with_session()
        msg = json.loads(client.build_unsubscribe_message(["AAPL"]))
        assert msg["SessionId"] == "a21af247-1f51-4ad4-a8ed-a16df58a352e"

    def test_single_symbol(self):
        client = self._client_with_session()
        msg = json.loads(client.build_unsubscribe_message([".SPX"]))
        assert msg["Symbol"] == ".SPX"

    def test_returns_valid_json_string(self):
        client = self._client_with_session()
        raw = client.build_unsubscribe_message(["AAPL"])
        assert isinstance(raw, str)
        json.loads(raw)  # should not raise


# ---------------------------------------------------------------------------
# MDDSClient.parse_message tests
# ---------------------------------------------------------------------------

class TestParseMessage:
    def test_success_message_returns_quotes(self):
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)
        quotes = client.parse_message(SUCCESS_MSG)
        assert len(quotes) == 1

    def test_success_message_quote_symbol(self):
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)
        quotes = client.parse_message(SUCCESS_MSG)
        assert quotes[0].symbol == "RKLB"

    def test_success_message_security_type(self):
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)
        quotes = client.parse_message(SUCCESS_MSG)
        assert quotes[0].security_type == "EQ"

    def test_option_message_returns_quote(self):
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)
        quotes = client.parse_message(OPTION_MSG)
        assert len(quotes) == 1

    def test_option_message_security_type(self):
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)
        quotes = client.parse_message(OPTION_MSG)
        assert quotes[0].security_type == "OP"

    def test_error_message_returns_empty(self):
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)
        quotes = client.parse_message(ERROR_MSG)
        assert quotes == []

    def test_connect_message_returns_empty(self):
        client = MDDSClient()
        quotes = client.parse_message(CONNECT_MSG)
        assert quotes == []

    def test_connect_message_sets_session(self):
        client = MDDSClient()
        client.parse_message(CONNECT_MSG)
        assert client.session_id == "a21af247-1f51-4ad4-a8ed-a16df58a352e"
        assert client.is_connected is True

    def test_parse_message_raw_data_preserved(self):
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)
        quotes = client.parse_message(SUCCESS_MSG)
        raw = quotes[0].raw
        assert raw["6"] == "RKLB"
        assert raw["128"] == "EQ"

    def test_parse_message_non_success_items_skipped(self):
        # A Data array where first item has status != "success"
        msg = json.dumps({
            "Command": "subscribe",
            "ResponseType": "1",
            "Data": [
                {"0": "error", "6": "BADTICKER"},
                {"0": "success", "6": "AAPL", "128": "EQ"},
            ],
        })
        client = MDDSClient()
        quotes = client.parse_message(msg)
        assert len(quotes) == 1
        assert quotes[0].symbol == "AAPL"

    def test_unknown_response_type_returns_empty(self):
        msg = json.dumps({"Command": "subscribe", "ResponseType": "2", "Data": []})
        client = MDDSClient()
        quotes = client.parse_message(msg)
        assert quotes == []


# ---------------------------------------------------------------------------
# MDDSQuote property tests
# ---------------------------------------------------------------------------

class TestMDDSQuoteProperties:
    def _equity_quote(self) -> MDDSQuote:
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)
        return client.parse_message(SUCCESS_MSG)[0]

    def _option_quote(self) -> MDDSQuote:
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)
        return client.parse_message(OPTION_MSG)[0]

    def test_last_price(self):
        q = self._equity_quote()
        assert q.last_price == pytest.approx(57.38)

    def test_bid(self):
        q = self._equity_quote()
        assert q.bid == pytest.approx(56.6)

    def test_ask(self):
        q = self._equity_quote()
        assert q.ask == pytest.approx(61.45)

    def test_volume_from_volume_field(self):
        q = self._equity_quote()
        # field 23 maps to "volume"
        assert q.volume == 2969239

    def test_net_change(self):
        q = self._equity_quote()
        assert q.net_change == pytest.approx(-3.55)

    def test_delta(self):
        q = self._option_quote()
        assert q.delta == pytest.approx(0.0863)

    def test_is_option_false_for_equity(self):
        q = self._equity_quote()
        assert q.is_option is False

    def test_is_option_true_for_option(self):
        q = self._option_quote()
        assert q.is_option is True

    def test_last_price_missing_returns_none(self):
        q = MDDSQuote(symbol="TEST", data={})
        assert q.last_price is None

    def test_bid_missing_returns_none(self):
        q = MDDSQuote(symbol="TEST", data={})
        assert q.bid is None

    def test_ask_missing_returns_none(self):
        q = MDDSQuote(symbol="TEST", data={})
        assert q.ask is None

    def test_volume_missing_returns_none(self):
        q = MDDSQuote(symbol="TEST", data={})
        assert q.volume is None

    def test_net_change_missing_returns_none(self):
        q = MDDSQuote(symbol="TEST", data={})
        assert q.net_change is None

    def test_delta_missing_returns_none(self):
        q = MDDSQuote(symbol="TEST", data={})
        assert q.delta is None

    def test_volume_falls_back_to_total_volume(self):
        q = MDDSQuote(symbol="TEST", data={"total_volume": "5000000"})
        assert q.volume == 5000000

    def test_is_option_false_when_no_security_type(self):
        q = MDDSQuote(symbol="TEST")
        assert q.is_option is False


# ---------------------------------------------------------------------------
# Full round-trip tests
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_connect_subscribe_parse_equity(self):
        client = MDDSClient()

        # Step 1: Handle connection
        session = client.handle_connect_message(CONNECT_MSG)
        assert session.connected is True
        assert session.session_id == "a21af247-1f51-4ad4-a8ed-a16df58a352e"

        # Step 2: Build subscribe message
        sub_msg = json.loads(client.build_subscribe_message(["RKLB"]))
        assert sub_msg["Command"] == "subscribe"
        assert sub_msg["SessionId"] == session.session_id
        assert "RKLB" in sub_msg["Symbol"]

        # Step 3: Parse incoming quote
        quotes = client.parse_message(SUCCESS_MSG)
        assert len(quotes) == 1
        q = quotes[0]
        assert q.symbol == "RKLB"
        assert q.security_type == "EQ"
        assert q.last_price == pytest.approx(57.38)
        assert q.bid == pytest.approx(56.6)
        assert q.ask == pytest.approx(61.45)
        assert q.net_change == pytest.approx(-3.55)
        assert q.is_option is False

    def test_connect_subscribe_parse_option(self):
        client = MDDSClient()

        # Step 1: Handle connection
        session = client.handle_connect_message(CONNECT_MSG)
        assert session.connected is True

        # Step 2: Build subscribe
        sub_msg = json.loads(
            client.build_subscribe_message(["-EVGO270115C7"], include_greeks=True)
        )
        assert sub_msg["IncludeGreeks"] is True

        # Step 3: Parse option quote
        quotes = client.parse_message(OPTION_MSG)
        assert len(quotes) == 1
        q = quotes[0]
        assert q.symbol == "-EVGO270115C7.GK"
        assert q.security_type == "OP"
        assert q.is_option is True
        assert q.delta == pytest.approx(0.0863)
        assert q.data["gamma"] == "0.12568"
        assert q.data["vega"] == "0.00236"
        assert q.data["theta"] == "-0.00033"
        assert q.data["strike_price"] == "7"
        assert q.data["call_put"] == "C"
        assert q.data["expiration_date"] == "2027-01-15"

    def test_connect_then_error_then_success(self):
        client = MDDSClient()

        # Connect
        client.handle_connect_message(CONNECT_MSG)
        assert client.is_connected is True

        # Error message gives empty quotes
        err_quotes = client.parse_message(ERROR_MSG)
        assert err_quotes == []

        # Success message still parses correctly after error
        ok_quotes = client.parse_message(SUCCESS_MSG)
        assert len(ok_quotes) == 1
        assert ok_quotes[0].symbol == "RKLB"

    def test_parse_message_triggers_connect_on_first_message(self):
        client = MDDSClient()
        assert client.is_connected is False

        # parse_message handles connect message too
        result = client.parse_message(CONNECT_MSG)
        assert result == []
        assert client.is_connected is True
        assert client.session_id == "a21af247-1f51-4ad4-a8ed-a16df58a352e"

    def test_unsubscribe_after_subscribe(self):
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)

        unsub = json.loads(client.build_unsubscribe_message(["RKLB", ".SPX"]))
        assert unsub["Command"] == "unsubscribe"
        assert unsub["Symbol"] == "RKLB,.SPX"
        assert unsub["SessionId"] == "a21af247-1f51-4ad4-a8ed-a16df58a352e"


# ---------------------------------------------------------------------------
# MDDSClient initial state tests
# ---------------------------------------------------------------------------

class TestMDDSClientInitialState:
    def test_session_id_empty_on_init(self):
        client = MDDSClient()
        assert client.session_id == ""

    def test_is_connected_false_on_init(self):
        client = MDDSClient()
        assert client.is_connected is False

    def test_mdds_url_constant(self):
        assert MDDS_URL == "wss://mdds-i-tc.fidelity.com/?productid=atn"


# ---------------------------------------------------------------------------
# ALL_FIELDS / field map coverage tests
# ---------------------------------------------------------------------------

class TestFieldMapCoverage:
    def test_all_fields_is_superset_of_equity(self):
        for k in EQUITY_FIELDS:
            assert k in ALL_FIELDS

    def test_all_fields_is_superset_of_option(self):
        for k in OPTION_FIELDS:
            assert k in ALL_FIELDS

    def test_option_fields_is_superset_of_equity(self):
        for k in EQUITY_FIELDS:
            assert k in OPTION_FIELDS

    def test_option_only_keys_not_in_equity(self):
        option_only = {"184", "187", "188", "189", "190", "191", "197", "199"}
        for k in option_only:
            assert k in OPTION_FIELDS
            assert k not in EQUITY_FIELDS

    def test_field_values_are_strings(self):
        for v in EQUITY_FIELDS.values():
            assert isinstance(v, str), f"Expected str, got {type(v)} for value {v!r}"
        for v in OPTION_FIELDS.values():
            assert isinstance(v, str), f"Expected str, got {type(v)} for value {v!r}"

    def test_all_fields_includes_time_sales(self):
        for k in TIME_SALES_FIELDS:
            assert k in ALL_FIELDS

    def test_time_sales_field_names(self):
        assert TIME_SALES_FIELDS["1159"] == "last_trade_price"
        assert TIME_SALES_FIELDS["1160"] == "last_trade_size"
        assert TIME_SALES_FIELDS["1161"] == "last_trade_time"
        assert TIME_SALES_FIELDS["1162"] == "last_trade_exchange"
        assert TIME_SALES_FIELDS["1163"] == "last_trade_condition"
        assert TIME_SALES_FIELDS["1164"] == "last_trade_tick"
        assert TIME_SALES_FIELDS["1165"] == "last_trade_sequence"


# ---------------------------------------------------------------------------
# Time & Sales field parsing tests
# ---------------------------------------------------------------------------

class TestTimeSalesFields:
    def test_parse_fields_includes_ts_with_auto_detect(self):
        raw = {"6": "AAPL", "124": "195.50", "128": "EQ", "1159": "195.45", "1160": "300"}
        result = parse_fields(raw)
        assert result["last_trade_price"] == "195.45"
        assert result["last_trade_size"] == "300"

    def test_parse_fields_ts_not_prefixed_as_unknown(self):
        raw = {"6": "AAPL", "1159": "195.45", "1161": "14:30:05"}
        result = parse_fields(raw)
        assert "field_1159" not in result
        assert "field_1161" not in result
        assert result["last_trade_price"] == "195.45"
        assert result["last_trade_time"] == "14:30:05"


# ---------------------------------------------------------------------------
# Streaming update (ResponseType "0") tests
# ---------------------------------------------------------------------------

class TestStreamingUpdates:
    def test_response_type_0_returns_quotes(self):
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)
        quotes = client.parse_message(STREAMING_UPDATE_MSG)
        assert len(quotes) == 1

    def test_response_type_0_parses_symbol(self):
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)
        quotes = client.parse_message(STREAMING_UPDATE_MSG)
        assert quotes[0].symbol == "AAPL"

    def test_response_type_0_has_trade_data(self):
        client = MDDSClient()
        client.handle_connect_message(CONNECT_MSG)
        quotes = client.parse_message(STREAMING_UPDATE_MSG)
        q = quotes[0]
        assert q.has_trade_data is True
        assert q.last_trade_price == pytest.approx(195.45)
        assert q.last_trade_size == 300
        assert q.last_trade_time == "14:30:05"
        assert q.last_trade_exchange == "XNGS"

    def test_response_type_0_no_success_check(self):
        """Streaming updates don't have status field '0' = 'success'."""
        msg = json.dumps({
            "ResponseType": "0",
            "Data": [{"6": "TSLA", "124": "250.00", "128": "EQ"}],
        })
        client = MDDSClient()
        quotes = client.parse_message(msg)
        assert len(quotes) == 1
        assert quotes[0].symbol == "TSLA"

    def test_has_trade_data_false_when_no_ts_fields(self):
        q = MDDSQuote(symbol="TEST", data={"last_price": "100"})
        assert q.has_trade_data is False

    def test_last_trade_time_none_when_missing(self):
        q = MDDSQuote(symbol="TEST", data={})
        assert q.last_trade_time is None

    def test_last_trade_exchange_none_when_missing(self):
        q = MDDSQuote(symbol="TEST", data={})
        assert q.last_trade_exchange is None
