"""Full walkthrough — hit every API module and print real results."""
import sys
import json
import time

sys.path.insert(0, "src")

from fidelity_trader import FidelityClient
from fidelity_trader.credentials import SecretsManagerProvider

provider = SecretsManagerProvider(
    username_secret="fidelity/username",
    password_secret="fidelity/password",
    totp_secret_name="fidelity/totp_secret",
)
creds = provider.get_credentials()

with FidelityClient() as client:

    # =========================================================================
    # 1. LOGIN
    # =========================================================================
    print("=" * 70)
    print("  1. LOGIN")
    print("=" * 70)
    try:
        result = client.login(creds.username, creds.password, totp_secret=creds.totp_secret)
        status = result["responseBaseInfo"]["status"]
        print(f"  Status:  {status['message']} (code {status['code']})")
        print(f"  Auth:    {client.is_authenticated}")
    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)

    # =========================================================================
    # 2. ACCOUNT DISCOVERY
    # =========================================================================
    print("\n" + "=" * 70)
    print("  2. ACCOUNT DISCOVERY")
    print("=" * 70)
    acct_nums = []
    try:
        accts = client.accounts.discover_accounts()
        print(f"  Found {len(accts.accounts)} accounts:\n")
        for a in accts.accounts:
            label = a.preference_detail.name if a.preference_detail else a.acct_num
            hidden = " (hidden)" if a.preference_detail and a.preference_detail.is_hidden else ""
            trade = ""
            if a.acct_trade_attr_detail:
                t = a.acct_trade_attr_detail
                trade = f"  optLvl={t.option_level} margin={t.mrgn_estb} options={t.option_estb}"
            wp = ""
            if a.workplace_plan_detail:
                w = a.workplace_plan_detail
                wp = f"  plan={w.plan_type_name} mktVal=${w.market_value}"
            print(f"    {a.acct_num:15s} {a.acct_type:12s} {a.acct_sub_type:25s} {label}{hidden}{trade}{wp}")
            if a.acct_type == "Brokerage":
                acct_nums.append(a.acct_num)
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    if not acct_nums:
        acct_nums = ["Z25485019", "Z33359950"]

    # =========================================================================
    # 3. POSITIONS
    # =========================================================================
    print("\n" + "=" * 70)
    print("  3. POSITIONS")
    print("=" * 70)
    try:
        pos = client.positions.get_positions(acct_nums)
        gl = pos.portfolio_detail.portfolio_gain_loss_detail if pos.portfolio_detail else None
        if gl:
            ptv = f"${gl.portfolio_total_val:,.2f}" if gl.portfolio_total_val is not None else "N/A"
            tgl = f"${gl.total_gain_loss:,.2f}" if gl.total_gain_loss is not None else "N/A"
            print(f"  Portfolio Value:  {ptv}")
            print(f"  Total Gain/Loss:  {tgl}")
        print(f"  Accounts: {len(pos.accounts)}\n")
        for acct in pos.accounts:
            print(f"    Account {acct.acct_num} ({len(acct.positions)} positions):")
            for p in acct.positions[:5]:
                price = f"${p.price_detail.last_price}" if p.price_detail and p.price_detail.last_price is not None else "N/A"
                mval = f"${p.market_val_detail.market_val:,.2f}" if p.market_val_detail and p.market_val_detail.market_val is not None else "N/A"
                print(f"      {p.symbol:20s} qty={p.quantity:>12.2f}  price={price:>10}  mktval={mval:>12}")
            if len(acct.positions) > 5:
                print(f"      ... and {len(acct.positions) - 5} more")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    # =========================================================================
    # 4. BALANCES
    # =========================================================================
    print("\n" + "=" * 70)
    print("  4. BALANCES")
    print("=" * 70)
    try:
        bal = client.balances.get_balances(acct_nums)
        print(f"  {len(bal.accounts)} accounts:\n")
        for ab in bal.accounts:
            nw = cash = bp = "N/A"
            if ab.recent_balance_detail:
                r = ab.recent_balance_detail
                if r.acct_val_detail and r.acct_val_detail.net_worth is not None:
                    nw = f"${r.acct_val_detail.net_worth:,.2f}"
                if r.cash_detail and r.cash_detail.core_balance is not None:
                    cash = f"${r.cash_detail.core_balance:,.2f}"
                if r.buying_power_detail and r.buying_power_detail.cash is not None:
                    bp = f"${r.buying_power_detail.cash:,.2f}"
            print(f"    {ab.acct_num:15s}  net_worth={nw:>14}  cash={cash:>14}  buying_power={bp:>14}")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    # =========================================================================
    # 5. ORDER STATUS
    # =========================================================================
    print("\n" + "=" * 70)
    print("  5. ORDER STATUS")
    print("=" * 70)
    try:
        orders = client.order_status.get_order_status(acct_nums)
        print(f"  Account summaries: {len(orders.account_summaries)}")
        for s in orders.account_summaries:
            sm = s.order_summary
            print(f"    {s.acct_num:15s}  orders={sm.order_count}  open={sm.open_count}  filled={sm.filled_count}  cancelled={sm.cancelled_count}")
        print(f"\n  Order details: {len(orders.orders)}")
        for o in orders.orders[:5]:
            status_code = o.status_detail.status_code if o.status_detail else "??"
            desc = o.base_order_detail.description[:70] if o.base_order_detail else "N/A"
            print(f"    [{status_code:10s}] {desc}")
        if len(orders.orders) > 5:
            print(f"    ... and {len(orders.orders) - 5} more")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    # =========================================================================
    # 6. OPTION SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("  6. OPTION POSITIONS SUMMARY")
    print("=" * 70)
    try:
        # Use known option-enabled accounts
        option_accts = ["Z21772945"]
        opt_sum = client.option_summary.get_option_summary(option_accts)
        print(f"  Accounts with options: {len(opt_sum.accounts)}")
        for oa in opt_sum.accounts:
            print(f"\n    Account {oa.acct_num}:")
            if oa.account_gain_loss_detail:
                g = oa.account_gain_loss_detail
                print(f"      Total cost basis:  ${g.total_cost_basis:,.2f}" if g.total_cost_basis is not None else "      Cost basis: N/A")
                print(f"      Total mkt value:   ${g.total_market_value:,.2f}" if g.total_market_value is not None else "      Mkt value: N/A")
                print(f"      Total gain/loss:   ${g.total_gain_loss:,.2f}" if g.total_gain_loss is not None else "      G/L: N/A")
            print(f"      Underlyings: {len(oa.underlying_details)}")
            for u in oa.underlying_details[:3]:
                print(f"        {u.leg_expiration_date}  {u.pairing_count} pairings  G/L=${u.total_gain_loss:,.2f}" if u.total_gain_loss is not None else f"        {u.leg_expiration_date}")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    # =========================================================================
    # 7. TRANSACTION HISTORY
    # =========================================================================
    print("\n" + "=" * 70)
    print("  7. TRANSACTION HISTORY (last 7 days)")
    print("=" * 70)
    try:
        now = int(time.time())
        week_ago = now - (7 * 86400)
        txns = client.transactions.get_transaction_history(acct_nums[:2], from_date=week_ago, to_date=now)
        print(f"  Accounts: {len(txns.accounts)}")
        for ta in txns.accounts:
            print(f"\n    Account {ta.acct_num}: {len(ta.transactions)} transactions")
            for t in ta.transactions[:5]:
                net = f"${t.amt_detail.net:,.2f}" if t.amt_detail and t.amt_detail.net is not None else ""
                cat = t.cat_detail.txn_cat_desc if t.cat_detail else ""
                print(f"      {t.short_desc[:50]:50s}  {net:>12}  {cat}")
            if len(ta.transactions) > 5:
                print(f"      ... and {len(ta.transactions) - 5} more")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    # =========================================================================
    # 8. SYMBOL SEARCH
    # =========================================================================
    print("\n" + "=" * 70)
    print("  8. SYMBOL SEARCH (autosuggest)")
    print("=" * 70)
    try:
        for query in ["AAPL", "SPX", "TSLA"]:
            results = client.search.autosuggest(query)
            top = results.suggestions[0] if results.suggestions else None
            if top:
                print(f"    '{query}' -> {top.symbol:8s} {top.desc[:40]:40s}  type={top.type}  exchange={top.exchange}")
            else:
                print(f"    '{query}' -> no results")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    # =========================================================================
    # 9. EARNINGS
    # =========================================================================
    print("\n" + "=" * 70)
    print("  9. EARNINGS DATA")
    print("=" * 70)
    try:
        earnings = client.research.get_earnings(["AAPL", "MSFT", "NVDA", "TSLA"])
        for e in earnings.earnings:
            sym = e.sec_detail.symbol if e.sec_detail else "??"
            latest = e.quarters[-1] if e.quarters else None
            if latest:
                eps = f"EPS={latest.adjusted_eps}" if latest.adjusted_eps is not None else "no EPS"
                est = f"est={latest.consensus_est}" if latest.consensus_est is not None else ""
                print(f"    {sym:6s}  Q{latest.fiscal_qtr} {latest.fiscal_yr}  {eps:>12}  {est:>12}  reported={latest.report_date}")
            else:
                print(f"    {sym:6s}  no earnings data")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    # =========================================================================
    # 10. DIVIDENDS
    # =========================================================================
    print("\n" + "=" * 70)
    print("  10. DIVIDENDS DATA")
    print("=" * 70)
    try:
        divs = client.research.get_dividends(["AAPL", "MSFT", "KO"])
        for d in divs.dividends:
            sym = d.sec_detail.symbol if d.sec_detail else "??"
            amt = f"${d.amt:.2f}" if d.amt is not None else "N/A"
            yld = f"{d.yld_ttm:.2f}%" if d.yld_ttm is not None else "N/A"
            ann = f"${d.indicated_ann_div:.2f}" if d.indicated_ann_div is not None else "N/A"
            print(f"    {sym:6s}  last_div={amt:>8}  yield={yld:>8}  ann_div={ann:>8}  ex_date={d.ex_div_date or 'N/A'}")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    # =========================================================================
    # 11. OPTION CHAIN (FastQuote XML)
    # =========================================================================
    print("\n" + "=" * 70)
    print("  11. OPTION CHAIN (FastQuote)")
    print("=" * 70)
    try:
        chain = client.option_chain.get_option_chain("AAPL")
        # Debug if XML parse fails:
        # resp = client._http.get("https://fastquote.fidelity.com/service/quote/chainLite", params={"productid": "atn", "symbols": "AAPL"})
        # print(f"    Status: {resp.status_code}, Content-Type: {resp.headers.get('content-type')}, Body[:200]: {resp.text[:200]}")
        print(f"    Symbol: {chain.symbol}")
        print(f"    Call expirations: {len(chain.calls)}")
        print(f"    Put expirations:  {len(chain.puts)}")
        if chain.calls:
            exp = chain.calls[0]
            print(f"\n    Nearest expiration: {exp.date} ({len(exp.options)} strikes)")
            for o in exp.options[:5]:
                print(f"      {o.symbol:25s}  strike={o.strike:>8}  type={o.expiry_type}")
            if len(exp.options) > 5:
                print(f"      ... and {len(exp.options) - 5} more strikes")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    # =========================================================================
    # 12. DEPTH OF MARKET (Montage)
    # =========================================================================
    print("\n" + "=" * 70)
    print("  12. DEPTH OF MARKET (Montage)")
    print("=" * 70)
    try:
        # Pick the first option from the chain
        if chain.calls and chain.calls[0].options:
            opt_sym = chain.calls[0].options[len(chain.calls[0].options) // 2].symbol
            montage = client.option_chain.get_montage(opt_sym)
            print(f"    Option:  {montage.symbol}")
            print(f"    Strike:  {montage.strike}")
            print(f"    Type:    {montage.call_put}")
            print(f"    Expiry:  {montage.expiration}")
            print(f"    Exchanges: {len(montage.quotes)}\n")
            for q in montage.quotes:
                print(f"      {q.exchange_name:35s}  bid={q.bid:>8.2f} x{q.bid_size:<5}  ask={q.ask:>8.2f} x{q.ask_size:<5}")
        else:
            print("    (no option chain data to query montage)")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    # =========================================================================
    # 13. OPTION ANALYTICS
    # =========================================================================
    print("\n" + "=" * 70)
    print("  13. OPTION ANALYTICS")
    print("=" * 70)
    try:
        legs = [
            {"symbol": "AAPL260417C200", "qty": 1, "price": 0, "equity": False},
            {"symbol": "AAPL260417C210", "qty": -1, "price": 0, "equity": False},
        ]
        analytics = client.option_analytics.analyze_position("AAPL", legs)
        if analytics.evaluations:
            ev = analytics.evaluations[0]
            print(f"    Eval date: {ev.eval_date}")
            if ev.position_details:
                pd = ev.position_details[0]
                pos = pd.position_detail
                print(f"    Position P/L:    ${pos.profit}" if pos else "    No position detail")
                print(f"    Max Profit:      ${pos.max_profit}" if pos else "")
                print(f"    Max Loss:        ${pos.max_loss}" if pos else "")
                print(f"    Prob of Profit:  {pos.prob_profit}" if pos else "")
                print(f"    Legs: {len(pd.leg_details)}")
                for i, leg in enumerate(pd.leg_details):
                    print(f"      Leg {i+1}: delta={leg.delta}  theta={leg.theta}  IV={leg.iv}  P/L=${leg.profit}")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    # =========================================================================
    # 14. WATCHLISTS
    # =========================================================================
    print("\n" + "=" * 70)
    print("  14. WATCHLISTS")
    print("=" * 70)
    try:
        wl = client.watchlists.get_watchlists()
        print(f"    Found {len(wl.watchlists)} watchlists:\n")
        for w in wl.watchlists:
            syms = [s.symbol for s in w.security_details[:8]]
            more = f" +{len(w.security_details) - 8} more" if len(w.security_details) > 8 else ""
            print(f"    {w.watchlist_name:20s}  ({len(w.security_details)} symbols)  [{', '.join(syms)}{more}]")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    # =========================================================================
    # 15. STREAMING NEWS AUTH
    # =========================================================================
    print("\n" + "=" * 70)
    print("  15. STREAMING NEWS AUTH")
    print("=" * 70)
    try:
        stream = client.streaming.authorize()
        print(f"    Streaming host:  {stream.streaming_host}:{stream.streaming_port}")
        print(f"    Polling host:    {stream.polling_host}:{stream.polling_port}")
        print(f"    Token:           {stream.access_token[:60]}...")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    # =========================================================================
    # 16. ALERTS SUBSCRIPTION
    # =========================================================================
    print("\n" + "=" * 70)
    print("  16. ALERTS SUBSCRIPTION")
    print("=" * 70)
    try:
        alert = client.alerts.subscribe()
        print(f"    Result:      {alert.result_code}")
        print(f"    Status:      {alert.activation_status}")
        print(f"    Server:      {alert.server_url}")
        print(f"    Destination: {alert.destination}")
        print(f"    User ID:     {alert.user_id}")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    # =========================================================================
    # 17. MDDS STREAMING (protocol test — no live connection)
    # =========================================================================
    print("\n" + "=" * 70)
    print("  17. MDDS STREAMING (protocol layer)")
    print("=" * 70)
    try:
        from fidelity_trader.streaming.mdds import MDDSClient
        mdds = MDDSClient()

        # Simulate connection
        session = mdds.handle_connect_message(json.dumps({
            "Message": "success",
            "SessionId": "test-session-id",
            "Status": "Ok",
            "host": "demo.us-east-2a",
            "productid": "atn",
        }))
        print(f"    Session ID:  {session.session_id}")
        print(f"    Connected:   {session.connected}")

        # Build subscribe message
        sub_msg = mdds.build_subscribe_message([".SPX", "AAPL", "-AAPL260417C200"])
        sub = json.loads(sub_msg)
        print(f"    Subscribe:   {sub['Symbol']}")
        print(f"    Conflation:  {sub['ConflationRate']}ms")
        print(f"    Greeks:      {sub['IncludeGreeks']}")

        # Parse a real captured response
        quotes = mdds.parse_message('{"Command":"subscribe","ResponseType":"1","Data":[{"0":"success","1":"Rocket Lab","6":"RKLB","10":"RKLB","12":"-3.55","13":"-5.8264","18":"56.73","20":"56.6","21":"100","23":"2969239","26":"61.64","27":"56.132","31":"61.45","32":"60.93","33":"21933537","57":"34694009211.24","124":"57.38","128":"EQ","169":"realtime"}],"Delay":"8ms","Request":"test"}')
        if quotes:
            q = quotes[0]
            print(f"\n    Parsed quote: {q.symbol}")
            print(f"      Last:      ${q.last_price}")
            print(f"      Bid:       ${q.bid}")
            print(f"      Ask:       ${q.ask}")
            print(f"      Volume:    {q.volume:,}")
            print(f"      Change:    ${q.net_change}")
            print(f"      Type:      {q.security_type}")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()

    # =========================================================================
    # DONE
    # =========================================================================
    print("\n" + "=" * 70)
    print("  LOGOUT")
    print("=" * 70)
    client.logout()
    print(f"    Authenticated: {client.is_authenticated}")

    print("\n" + "=" * 70)
    print("  WALKTHROUGH COMPLETE — 17 modules tested")
    print("=" * 70)
