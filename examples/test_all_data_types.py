"""Test all live market data categories available from Fidelity Trader+."""
import sys
import json
import asyncio
import ssl

sys.path.insert(0, "src")

import websockets
from fidelity_trader import FidelityClient
from fidelity_trader.credentials import SecretsManagerProvider
from fidelity_trader.streaming.mdds import MDDS_URL
from fidelity_trader.streaming.mdds_fields import parse_fields, OPTION_FIELDS

creds = SecretsManagerProvider(
    username_secret="fidelity/username",
    password_secret="fidelity/password",
    totp_secret_name="fidelity/totp_secret",
).get_credentials()


async def test_streaming(cookies):
    cookie_str = "; ".join(f"{c.name}={c.value}" for c in cookies)
    ssl_ctx = ssl.create_default_context()

    async with websockets.connect(
        MDDS_URL,
        additional_headers={"Cookie": cookie_str},
        ssl=ssl_ctx,
    ) as ws:
        connect_msg = await ws.recv()
        session_id = json.loads(connect_msg)["SessionId"]

        # =====================================================================
        # TEST 1: Equity quote — what fields do we get?
        # =====================================================================
        print("=" * 70)
        print("  1. EQUITY QUOTE FIELDS (AAPL)")
        print("=" * 70)

        await ws.send(json.dumps({
            "SessionId": session_id,
            "Command": "subscribe",
            "Symbol": "AAPL",
            "ConflationRate": 1000,
            "IncludeGreeks": False,
        }))

        msg = await ws.recv()
        data = json.loads(msg)
        if data.get("ResponseType") == "1":
            raw = data["Data"][0]
            parsed = parse_fields(raw)
            print(f"\n  Raw field count: {len(raw)}")
            print(f"\n  Key quote fields:")
            for key in ["symbol", "security_name", "last_price", "bid", "ask",
                         "bid_size", "ask_size", "open", "day_high", "day_low",
                         "close_price", "previous_close", "net_change", "net_change_pct",
                         "volume", "total_volume", "num_trades",
                         "fifty_two_week_high", "fifty_two_week_low",
                         "market_cap", "shares_outstanding",
                         "data_quality", "security_type",
                         "pre_market_price", "pre_market_bid",
                         "after_hours_price", "sector", "industry"]:
                val = parsed.get(key, "—")
                if val and val != "—":
                    print(f"    {key:30s} = {str(val)[:60]}")

        # =====================================================================
        # TEST 2: Option quote with Greeks
        # =====================================================================
        print("\n" + "=" * 70)
        print("  2. OPTION QUOTE WITH GREEKS (-AAPL260417C250)")
        print("=" * 70)

        await ws.send(json.dumps({
            "SessionId": session_id,
            "Command": "subscribe",
            "Symbol": "-AAPL260417C250",
            "ConflationRate": 1000,
            "IncludeGreeks": True,
        }))

        # May get multiple messages — look for the option data
        for _ in range(5):
            msg = await ws.recv()
            data = json.loads(msg)
            if data.get("ResponseType") == "1":
                for item in data["Data"]:
                    if item.get("128") == "OP" or "184" in item:
                        parsed = parse_fields(item, OPTION_FIELDS)
                        print(f"\n  Raw field count: {len(item)}")
                        print(f"\n  Option quote fields:")
                        for key in ["symbol", "display_symbol", "option_description",
                                     "underlying_symbol", "strike_price", "call_put",
                                     "expiration_date", "contract_size", "open_interest",
                                     "last_price", "bid", "ask", "mid_price",
                                     "volume", "net_change", "net_change_pct",
                                     "delta", "gamma", "theta", "vega", "rho",
                                     "implied_volatility", "historical_volatility",
                                     "intrinsic_value", "premium",
                                     "data_quality", "security_type"]:
                            val = parsed.get(key, "—")
                            if val and val != "—" and val != "":
                                print(f"    {key:30s} = {str(val)[:60]}")
                        break
                break

        # =====================================================================
        # TEST 3: Index quote (.SPX, .VIX, .DJI)
        # =====================================================================
        print("\n" + "=" * 70)
        print("  3. INDEX QUOTES (.SPX, .VIX, .DJI)")
        print("=" * 70)

        await ws.send(json.dumps({
            "SessionId": session_id,
            "Command": "subscribe",
            "Symbol": ".SPX,.VIX,.DJI",
            "ConflationRate": 1000,
            "IncludeGreeks": False,
        }))

        indices_seen = {}
        for _ in range(10):
            msg = await ws.recv()
            data = json.loads(msg)
            if data.get("ResponseType") == "1":
                for item in data["Data"]:
                    sym = item.get("289", item.get("6", ""))
                    if sym and sym not in indices_seen:
                        parsed = parse_fields(item)
                        last = parsed.get("last_price", "")
                        chg = parsed.get("net_change", "")
                        pct = parsed.get("net_change_pct", "")
                        high = parsed.get("day_high", "")
                        low = parsed.get("day_low", "")
                        print(f"    {sym:>6}  last={last:>10}  chg={chg:>10}  pct={pct:>8}%  high={high:>10}  low={low:>10}")
                        indices_seen[sym] = True
            if len(indices_seen) >= 3:
                break

        # =====================================================================
        # TEST 4: L2 / Depth of Market (montage — REST snapshot)
        # =====================================================================
        # (This was tested in the walkthrough via fastquote dtmontage)
        print("\n" + "=" * 70)
        print("  4. L2 / DEPTH OF MARKET")
        print("=" * 70)
        print("    Available via REST: fastquote.fidelity.com/service/quote/dtmontage")
        print("    Shows per-exchange bid/ask with sizes (AMEX, CBOE, PHLX, ISE, etc.)")
        print("    Status: SNAPSHOT only (not streaming L2)")
        print("    Note: Real streaming L2 likely uses the MDDS WebSocket with")
        print("    a different subscription command — needs further capture")

        # =====================================================================
        # TEST 5: Time & Sales
        # =====================================================================
        print("\n" + "=" * 70)
        print("  5. TIME & SALES")
        print("=" * 70)
        print("    Not yet captured from Trader+")
        print("    Checking if MDDS sends tick-by-tick trade data...")

        # Subscribe and wait for update messages (not just initial snapshot)
        await ws.send(json.dumps({
            "SessionId": session_id,
            "Command": "subscribe",
            "Symbol": "AAPL",
            "ConflationRate": 250,  # faster updates
            "IncludeGreeks": False,
        }))

        update_count = 0
        update_fields = set()
        try:
            async with asyncio.timeout(10):
                while update_count < 5:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    # Look for update messages (different from initial subscribe)
                    if data.get("Command") == "update" or (data.get("ResponseType") and data.get("ResponseType") != "-1"):
                        update_count += 1
                        if "Data" in data:
                            for item in data["Data"]:
                                update_fields.update(item.keys())
                                if update_count <= 3:
                                    parsed = parse_fields(item)
                                    # Show what fields change in updates
                                    changing = {k: v for k, v in parsed.items() if v and v != "" and not k.startswith("field_")}
                                    print(f"    Update {update_count}: {json.dumps(changing, default=str)[:120]}")
        except (asyncio.TimeoutError, TimeoutError):
            pass

        if update_count > 0:
            print(f"\n    Got {update_count} update(s) in 10s with {len(update_fields)} fields")
            print(f"    Update fields seen: {sorted(update_fields)[:20]}")
        else:
            print("    No streaming updates received (market may be between ticks)")

        # =====================================================================
        # SUMMARY
        # =====================================================================
        print("\n" + "=" * 70)
        print("  MARKET DATA COVERAGE SUMMARY")
        print("=" * 70)
        print("""
    Category            Source              Status
    ------------------  ------------------  --------------------------
    Live Quotes         MDDS WebSocket      WORKING (bid/ask/last/vol/chg)
    Option Quotes       MDDS WebSocket      WORKING (+ Greeks when IncludeGreeks=true)
    Index Quotes        MDDS WebSocket      WORKING (.SPX/.VIX/.DJI)
    Option Chain        FastQuote REST      WORKING (strikes/expirations)
    L2 / Montage        FastQuote REST      SNAPSHOT (per-exchange quotes)
    L2 Streaming        MDDS WebSocket      NEEDS INVESTIGATION
    Time & Sales        MDDS WebSocket      NEEDS INVESTIGATION
    Greeks Streaming    MDDS WebSocket      WORKING (delta/gamma/theta/vega/rho/IV)
        """)

        await ws.send(json.dumps({"SessionId": session_id, "Command": "unsubscribe", "Symbol": "AAPL,.SPX,.VIX,.DJI,-AAPL260417C250"}))


with FidelityClient() as client:
    client.login(creds.username, creds.password, totp_secret=creds.totp_secret)
    asyncio.run(test_streaming(client._http.cookies.jar))
