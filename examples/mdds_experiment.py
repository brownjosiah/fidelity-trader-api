"""Experiment with MDDS WebSocket commands to discover T&S and L2 data."""
import sys
import json
import asyncio
import ssl

sys.path.insert(0, "src")

import websockets
from fidelity_trader import FidelityClient
from fidelity_trader.credentials import SecretsManagerProvider
from fidelity_trader.streaming.mdds import MDDS_URL
from fidelity_trader.streaming.mdds_fields import parse_fields

SYMBOL = "SPY"


async def experiment(cookies):
    cookie_str = "; ".join(f"{c.name}={c.value}" for c in cookies)
    ssl_ctx = ssl.create_default_context()

    async with websockets.connect(
        MDDS_URL,
        additional_headers={"Cookie": cookie_str},
        ssl=ssl_ctx,
    ) as ws:
        connect_msg = await ws.recv()
        sid = json.loads(connect_msg)["SessionId"]
        print(f"Connected: {sid[:20]}...\n")

        async def send_and_recv(msg_dict, label, wait_count=3, timeout_s=5):
            """Send a command and collect responses."""
            print(f"{'='*70}")
            print(f"  EXPERIMENT: {label}")
            print(f"{'='*70}")
            print(f"  Sending: {json.dumps(msg_dict)[:120]}")
            await ws.send(json.dumps(msg_dict))
            results = []
            try:
                async with asyncio.timeout(timeout_s):
                    for _ in range(wait_count):
                        raw = await ws.recv()
                        data = json.loads(raw)
                        results.append(data)
                        cmd = data.get("Command", "")
                        rt = data.get("ResponseType", "")
                        err = data.get("ErrorCode", "")

                        if rt == "-1":
                            err_text = data.get("Data", [{}])[0].get("0", "")
                            print(f"  <- ERROR: code={err} {err_text}")
                        elif rt == "1" and "Data" in data:
                            for item in data["Data"]:
                                if item.get("0") == "success":
                                    parsed = parse_fields(item)
                                    sym = parsed.get("display_symbol", parsed.get("symbol", "?"))
                                    sec = parsed.get("security_type", "?")
                                    last = parsed.get("last_price", "")
                                    bid = parsed.get("bid", "")
                                    ask = parsed.get("ask", "")
                                    # Check for any T&S or L2 specific fields
                                    ts_fields = {k: v for k, v in parsed.items()
                                                if any(x in k.lower() for x in ["trade", "time", "sale", "tick", "level", "depth", "book"])}
                                    print(f"  <- SUCCESS: {sym} ({sec}) last={last} bid={bid} ask={ask}")
                                    if ts_fields:
                                        print(f"     T&S/L2 fields: {ts_fields}")
                                    # Show total field count and unknown fields
                                    unknown = {k: v for k, v in parsed.items() if k.startswith("field_") and v}
                                    if unknown:
                                        print(f"     Unknown fields ({len(unknown)}): {dict(list(unknown.items())[:5])}")
                        elif "Message" in data:
                            print(f"  <- {data.get('Message', '')} Status={data.get('Status', '')}")
                        else:
                            print(f"  <- {json.dumps(data)[:150]}")
            except (asyncio.TimeoutError, TimeoutError):
                if not results:
                    print(f"  <- TIMEOUT (no response in {timeout_s}s)")
            print()
            return results

        # =================================================================
        # 1. Standard subscribe (baseline)
        # =================================================================
        await send_and_recv({
            "SessionId": sid, "Command": "subscribe",
            "Symbol": SYMBOL, "ConflationRate": 250, "IncludeGreeks": False,
        }, "Standard subscribe (baseline)")

        # =================================================================
        # 2. Subscribe with different ConflationRate values
        # =================================================================
        for rate in [0, 100, 50]:
            await send_and_recv({
                "SessionId": sid, "Command": "subscribe",
                "Symbol": SYMBOL, "ConflationRate": rate, "IncludeGreeks": False,
            }, f"ConflationRate={rate} (faster updates?)")

        # =================================================================
        # 3. Try subscribe with extra params
        # =================================================================
        for extra_key, extra_val in [
            ("IncludeTimeSales", True),
            ("IncludeL2", True),
            ("IncludeDepth", True),
            ("IncludeBook", True),
            ("Level", 2),
            ("DataType", "TS"),
            ("DataType", "L2"),
            ("DataType", "DEPTH"),
            ("SubscriptionType", "timesales"),
            ("SubscriptionType", "level2"),
            ("IncludeTrades", True),
            ("Mode", "TS"),
            ("Mode", "L2"),
        ]:
            await send_and_recv({
                "SessionId": sid, "Command": "subscribe",
                "Symbol": SYMBOL, "ConflationRate": 250, "IncludeGreeks": False,
                extra_key: extra_val,
            }, f"subscribe + {extra_key}={extra_val}", wait_count=2, timeout_s=3)

        # =================================================================
        # 4. Try different commands entirely
        # =================================================================
        for cmd in ["timesales", "level2", "depth", "book", "trades",
                     "subscribe_timesales", "subscribe_l2", "subscribe_depth",
                     "ts_subscribe", "l2_subscribe", "marketdepth"]:
            await send_and_recv({
                "SessionId": sid, "Command": cmd,
                "Symbol": SYMBOL,
            }, f"Command='{cmd}'", wait_count=1, timeout_s=3)

        # =================================================================
        # 5. Try connecting to mdds-i (not mdds-i-tc)
        # =================================================================
        print("=" * 70)
        print("  EXPERIMENT: Connect to mdds-i.fidelity.com (non-tc)")
        print("=" * 70)
        try:
            async with websockets.connect(
                "wss://mdds-i.fidelity.com/?productid=atn",
                additional_headers={"Cookie": cookie_str},
                ssl=ssl_ctx,
            ) as ws2:
                msg = await ws2.recv()
                data = json.loads(msg)
                sid2 = data.get("SessionId", "")
                print(f"  Connected: {sid2[:20]}... Status={data.get('Status')}")

                # Try subscribe on this connection
                await ws2.send(json.dumps({
                    "SessionId": sid2, "Command": "subscribe",
                    "Symbol": SYMBOL, "ConflationRate": 0, "IncludeGreeks": False,
                }))
                try:
                    async with asyncio.timeout(5):
                        for _ in range(3):
                            raw = await ws2.recv()
                            d = json.loads(raw)
                            rt = d.get("ResponseType", "")
                            if rt == "1" and "Data" in d:
                                item = d["Data"][0]
                                parsed = parse_fields(item)
                                print(f"  <- Got {len(item)} fields, last={parsed.get('last_price')}")
                            else:
                                print(f"  <- {json.dumps(d)[:120]}")
                except (asyncio.TimeoutError, TimeoutError):
                    print(f"  <- timeout")
        except Exception as e:
            print(f"  <- Connection failed: {e}")

        # =================================================================
        # 6. Wait for streaming updates and inspect what changes
        # =================================================================
        print(f"\n{'='*70}")
        print(f"  EXPERIMENT: Capture streaming updates for 15s")
        print(f"{'='*70}")

        await ws.send(json.dumps({
            "SessionId": sid, "Command": "subscribe",
            "Symbol": SYMBOL, "ConflationRate": 0, "IncludeGreeks": False,
        }))

        update_count = 0
        all_fields_seen = set()
        try:
            async with asyncio.timeout(15):
                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    if data.get("ResponseType") == "1" and "Data" in data:
                        update_count += 1
                        for item in data["Data"]:
                            all_fields_seen.update(item.keys())
                            if update_count <= 5:
                                parsed = parse_fields(item)
                                last = parsed.get("last_price", "")
                                bid = parsed.get("bid", "")
                                ask = parsed.get("ask", "")
                                vol = parsed.get("volume", parsed.get("total_volume", ""))
                                num_fields = len(item)
                                print(f"  Update {update_count}: {num_fields} fields  last={last} bid={bid} ask={ask} vol={vol}")
        except (asyncio.TimeoutError, TimeoutError):
            pass

        print(f"\n  Total updates: {update_count} in 15s")
        print(f"  Unique fields across all updates: {len(all_fields_seen)}")
        print(f"  All field IDs: {sorted(all_fields_seen, key=lambda x: int(x) if x.isdigit() else 99999)}")

        # Unsubscribe
        await ws.send(json.dumps({"SessionId": sid, "Command": "unsubscribe", "Symbol": SYMBOL}))


creds = SecretsManagerProvider(
    username_secret="fidelity/username",
    password_secret="fidelity/password",
    totp_secret_name="fidelity/totp_secret",
).get_credentials()

with FidelityClient() as client:
    client.login(creds.username, creds.password, totp_secret=creds.totp_secret)
    asyncio.run(experiment(client._http.cookies.jar))
