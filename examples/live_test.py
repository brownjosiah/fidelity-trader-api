"""Live test — login and pull real data from Fidelity Trader+ APIs."""
import sys
sys.path.insert(0, "src")

from fidelity_trader import FidelityClient
from fidelity_trader.credentials import SecretsManagerProvider

# Load credentials from AWS Secrets Manager
print("[0] Loading credentials from AWS Secrets Manager...")
provider = SecretsManagerProvider(
    username_secret="fidelity/username",
    password_secret="fidelity/password",
)
creds = provider.get_credentials()
print(f"    Username: {creds.username[:3]}***")

with FidelityClient() as client:
    # --- Login ---
    print("\n[1] Logging in...")
    try:
        result = client.login(creds.username, creds.password, totp_secret=creds.totp_secret)
        print(f"    Status: {result['responseBaseInfo']['status']['message']}")
        print(f"    Authenticated: {client.is_authenticated}")
    except Exception as e:
        print(f"    LOGIN FAILED: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    # --- Positions ---
    print("\n[2] Fetching positions...")
    try:
        acct_nums = ["Z25485019", "Z33359950", "257619270", "652274226"]
        pos = client.positions.get_positions(acct_nums)
        pd = pos.portfolio_detail
        if pd and pd.portfolio_gain_loss_detail:
            gl = pd.portfolio_gain_loss_detail
            print(f"    Portfolio value: ${gl.portfolio_total_val:,.2f}" if gl.portfolio_total_val else "    Portfolio value: N/A")
            print(f"    Total gain/loss: ${gl.total_gain_loss:,.2f}" if gl.total_gain_loss else "    Total G/L: N/A")
        print(f"    Accounts: {len(pos.accounts)}")
        for acct in pos.accounts:
            print(f"\n    Account {acct.acct_num} ({len(acct.positions)} positions):")
            for p in acct.positions[:5]:
                price = p.price_detail.last_price if p.price_detail else "N/A"
                mval = p.market_val_detail.market_val if p.market_val_detail else "N/A"
                print(f"      {p.symbol:20s} qty={p.quantity:>10.2f}  price=${price}  mktval=${mval}")
    except Exception as e:
        print(f"    POSITIONS FAILED: {e}")
        import traceback; traceback.print_exc()

    # --- Balances ---
    print("\n[3] Fetching balances...")
    try:
        bal = client.balances.get_balances(acct_nums)
        for ab in bal.accounts:
            nw = "N/A"
            cash = "N/A"
            if ab.recent_balance_detail and ab.recent_balance_detail.acct_val_detail:
                nw = f"${ab.recent_balance_detail.acct_val_detail.net_worth:,.2f}" if ab.recent_balance_detail.acct_val_detail.net_worth is not None else "N/A"
            if ab.recent_balance_detail and ab.recent_balance_detail.cash_detail:
                cash = f"${ab.recent_balance_detail.cash_detail.core_balance:,.2f}" if ab.recent_balance_detail.cash_detail.core_balance is not None else "N/A"
            print(f"    Account {ab.acct_num}: net_worth={nw}  core_cash={cash}")
    except Exception as e:
        print(f"    BALANCES FAILED: {e}")
        import traceback; traceback.print_exc()

    # --- Order Status ---
    print("\n[4] Fetching order status...")
    try:
        orders = client.orders.get_order_status(acct_nums)
        print(f"    Account summaries: {len(orders.account_summaries)}")
        for s in orders.account_summaries:
            summary = s.order_summary
            print(f"      {s.acct_num}: {summary.open_count} open, {summary.filled_count} filled, {summary.cancelled_count} cancelled")
        print(f"    Total order details: {len(orders.orders)}")
        for o in orders.orders[:3]:
            desc = o.base_order_detail.description if o.base_order_detail else "N/A"
            print(f"      [{o.status_detail.status_code}] {desc[:80]}")
    except Exception as e:
        print(f"    ORDERS FAILED: {e}")
        import traceback; traceback.print_exc()

    # --- Research ---
    print("\n[5] Fetching earnings data...")
    try:
        earnings = client.research.get_earnings(["AAPL", "MSFT"])
        for e in earnings.earnings:
            latest = e.quarters[0] if e.quarters else None
            eps = f"EPS={latest.adjusted_eps}" if latest and latest.adjusted_eps is not None else "no data"
            print(f"    {e.sec_detail.symbol}: {eps}")
    except Exception as e:
        print(f"    EARNINGS FAILED: {e}")
        import traceback; traceback.print_exc()

    # --- Streaming News Auth ---
    print("\n[6] Authorizing streaming news...")
    try:
        stream = client.streaming.authorize()
        print(f"    Streaming host: {stream.streaming_host}:{stream.streaming_port}")
        print(f"    Polling host:   {stream.polling_host}:{stream.polling_port}")
        print(f"    Token:          {stream.access_token[:50]}...")
    except Exception as e:
        print(f"    STREAMING FAILED: {e}")
        import traceback; traceback.print_exc()

    print("\n[7] Logging out...")
    client.logout()
    print(f"    Authenticated: {client.is_authenticated}")
    print("\nDone!")
