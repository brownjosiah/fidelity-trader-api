"""Live MDDS WebSocket streaming — connect and print real-time quotes."""
import sys
import json
import asyncio
import ssl

sys.path.insert(0, "src")

import websockets
from fidelity_trader import FidelityClient
from fidelity_trader.credentials import SecretsManagerProvider
from fidelity_trader.streaming.mdds import MDDSClient, MDDS_URL
from fidelity_trader.streaming.mdds_fields import parse_fields

SYMBOLS = [".SPX", "AAPL", "TSLA", "NVDA", "UAL", "QS"]
DURATION = 30  # seconds to stream


async def stream_quotes(cookies: dict):
    """Connect to MDDS WebSocket and stream real-time quotes."""

    # Build cookie header from session cookies
    cookie_str = "; ".join(f"{c.name}={c.value}" for c in cookies)

    # SSL context — Fidelity uses standard TLS
    ssl_ctx = ssl.create_default_context()

    print(f"\nConnecting to {MDDS_URL}...")

    async with websockets.connect(
        MDDS_URL,
        additional_headers={"Cookie": cookie_str},
        ssl=ssl_ctx,
    ) as ws:
        # Read connection message
        connect_msg = await ws.recv()
        connect_data = json.loads(connect_msg)
        session_id = connect_data.get("SessionId", "")
        status = connect_data.get("Status", "")
        host = connect_data.get("host", "")
        print(f"Connected! Session={session_id[:20]}... Host={host} Status={status}\n")

        if status != "Ok":
            print(f"Connection failed: {connect_data}")
            return

        # Subscribe
        sub_msg = json.dumps({
            "SessionId": session_id,
            "Command": "subscribe",
            "Symbol": ",".join(SYMBOLS),
            "ConflationRate": 1000,
            "IncludeGreeks": False,
        })
        await ws.send(sub_msg)
        print(f"Subscribed to: {', '.join(SYMBOLS)}")
        print(f"Streaming for {DURATION} seconds...\n")
        print(f"{'Symbol':>8}  {'Last':>10}  {'Bid':>10}  {'Ask':>10}  {'Change':>10}  {'Chg%':>8}  {'Volume':>12}  {'Type':>4}")
        print("-" * 90)

        # Use the MDDS client for parsing
        mdds = MDDSClient()
        mdds._session.session_id = session_id
        mdds._session.connected = True

        # Stream for DURATION seconds
        seen = {}
        try:
            async with asyncio.timeout(DURATION):
                while True:
                    msg = await ws.recv()
                    quotes = mdds.parse_message(msg)
                    for q in quotes:
                        sym = q.data.get("display_symbol", q.symbol)
                        if not sym or sym in seen:
                            continue
                        seen[sym] = True

                        last = q.last_price
                        bid = q.bid
                        ask = q.ask
                        chg = q.net_change
                        chg_pct = q.data.get("net_change_pct", "")
                        vol = q.volume
                        sec = q.security_type

                        last_s = f"${last:.2f}" if last else ""
                        bid_s = f"${bid:.2f}" if bid else ""
                        ask_s = f"${ask:.2f}" if ask else ""
                        chg_s = f"${chg:+.2f}" if chg else ""
                        pct_s = f"{float(chg_pct):+.2f}%" if chg_pct else ""
                        vol_s = f"{vol:,}" if vol else ""

                        print(f"{sym:>8}  {last_s:>10}  {bid_s:>10}  {ask_s:>10}  {chg_s:>10}  {pct_s:>8}  {vol_s:>12}  {sec:>4}")

        except (asyncio.TimeoutError, TimeoutError):
            print(f"\n--- {DURATION}s elapsed ---")

        # Unsubscribe
        unsub = json.dumps({
            "SessionId": session_id,
            "Command": "unsubscribe",
            "Symbol": ",".join(SYMBOLS),
        })
        await ws.send(unsub)
        print(f"Unsubscribed. Total unique quotes: {len(seen)}")


def main():
    print("=" * 70)
    print("  LIVE MDDS STREAMING TEST")
    print("=" * 70)

    # Login
    creds = SecretsManagerProvider(
        username_secret="fidelity/username",
        password_secret="fidelity/password",
        totp_secret_name="fidelity/totp_secret",
    ).get_credentials()

    with FidelityClient() as client:
        print("Logging in...")
        client.login(creds.username, creds.password, totp_secret=creds.totp_secret)
        print(f"Authenticated: {client.is_authenticated}")

        # Get cookies from the session
        cookies = client._http.cookies.jar

        # Run async streaming
        asyncio.run(stream_quotes(cookies))

    print("\nDone!")


if __name__ == "__main__":
    main()
