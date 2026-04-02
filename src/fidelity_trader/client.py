"""Main client that composes all Fidelity API modules."""

from fidelity_trader._http import create_atp_session, BASE_URL, AUTH_URL
from fidelity_trader.auth.session import AuthSession
from fidelity_trader.portfolio.positions import PositionsAPI
from fidelity_trader.portfolio.balances import BalancesAPI
from fidelity_trader.portfolio.option_summary import OptionSummaryAPI
from fidelity_trader.portfolio.transactions import TransactionsAPI
from fidelity_trader.orders.status import OrderStatusAPI
from fidelity_trader.orders.equity import EquityOrderAPI
from fidelity_trader.orders.options import MultiLegOptionOrderAPI
from fidelity_trader.orders.cancel import OrderCancelAPI
from fidelity_trader.orders.single_option import SingleOptionOrderAPI
from fidelity_trader.orders.cancel_replace import CancelReplaceAPI
from fidelity_trader.orders.staged import StagedOrderAPI
from fidelity_trader.orders.conditional import ConditionalOrderAPI
from fidelity_trader.research.data import ResearchAPI
from fidelity_trader.research.search import SearchAPI
from fidelity_trader.streaming.news import StreamingNewsAPI
from fidelity_trader.watchlists.watchlists import WatchlistAPI
from fidelity_trader.portfolio.accounts import AccountsAPI
from fidelity_trader.market_data.fastquote import FastQuoteAPI
from fidelity_trader.market_data.chart import ChartAPI
from fidelity_trader.research.analytics import OptionAnalyticsAPI
from fidelity_trader.research.screener import ScreenerAPI
from fidelity_trader.alerts.subscription import AlertsAPI
from fidelity_trader.portfolio.closed_positions import ClosedPositionsAPI
from fidelity_trader.portfolio.loaned_securities import LoanedSecuritiesAPI
from fidelity_trader.portfolio.tax_lots import TaxLotAPI
from fidelity_trader.reference.markets import AvailableMarketsAPI
from fidelity_trader.settings.preferences import PreferencesAPI
from fidelity_trader.auth.security_context import SecurityContextAPI
from fidelity_trader.auth.session_keepalive import SessionKeepAliveAPI
from fidelity_trader.auth.auto_refresh import SessionAutoRefresh
from fidelity_trader.reference.holiday_calendar import HolidayCalendarAPI
from fidelity_trader.alerts.price_triggers import PriceTriggersAPI


class FidelityClient:
    """Unofficial Fidelity Trader+ API client.

    Usage:
        with FidelityClient() as client:
            client.login(username="...", password="...")
            positions = client.positions.get_positions(["Z12345678"])
            balances = client.balances.get_balances(["Z12345678"])
            orders = client.orders.get_order_status(["Z12345678"])
            earnings = client.research.get_earnings(["AAPL", "MSFT"])
    """

    def __init__(self) -> None:
        self._http = create_atp_session()
        self._auth = AuthSession(self._http, BASE_URL, AUTH_URL)
        self._auto_refresh: SessionAutoRefresh | None = None

        # All modules share the same httpx client (and its cookie jar)
        self.positions = PositionsAPI(self._http)
        self.balances = BalancesAPI(self._http)
        self.option_summary = OptionSummaryAPI(self._http)
        self.transactions = TransactionsAPI(self._http)
        self.order_status = OrderStatusAPI(self._http)
        self.equity_orders = EquityOrderAPI(self._http)
        self.option_orders = MultiLegOptionOrderAPI(self._http)
        self.cancel_order = OrderCancelAPI(self._http)
        self.single_option_orders = SingleOptionOrderAPI(self._http)
        self.cancel_replace = CancelReplaceAPI(self._http)
        self.research = ResearchAPI(self._http)
        self.search = SearchAPI(self._http)
        self.streaming = StreamingNewsAPI(self._http)
        self.watchlists = WatchlistAPI(self._http)
        self.accounts = AccountsAPI(self._http)
        self.option_chain = FastQuoteAPI(self._http)
        self.chart = ChartAPI(self._http)
        self.option_analytics = OptionAnalyticsAPI(self._http)
        self.alerts = AlertsAPI(self._http)
        self.closed_positions = ClosedPositionsAPI(self._http)
        self.loaned_securities = LoanedSecuritiesAPI(self._http)
        self.tax_lots = TaxLotAPI(self._http)
        self.available_markets = AvailableMarketsAPI(self._http)
        self.preferences = PreferencesAPI(self._http)
        self.security_context = SecurityContextAPI(self._http)
        self.session_keepalive = SessionKeepAliveAPI(self._http)
        self.holiday_calendar = HolidayCalendarAPI(self._http)
        self.staged_orders = StagedOrderAPI(self._http)
        self.price_triggers = PriceTriggersAPI(self._http)
        self.conditional_orders = ConditionalOrderAPI(self._http)
        self.screener = ScreenerAPI(self._http)

    def login(self, username: str, password: str, totp_secret: str = None) -> dict:
        """Authenticate with Fidelity and establish a session.

        If totp_secret is provided, generates and submits a TOTP code for 2FA.
        After login, initializes the security context (required for real-time
        quote access on fastquote.fidelity.com).
        """
        result = self._auth.login(username, password, totp_secret=totp_secret)

        # Initialize security context — required for real-time quote
        # entitlements on fastquote.fidelity.com (without this, montage
        # returns "Delayed quotes not supported")
        try:
            self._http.post(
                f"{BASE_URL}/ftgw/digital/pico/api/v1/context/security",
                json={},
            )
        except Exception:
            pass  # Non-fatal — quotes still work, just may be delayed

        return result

    def logout(self) -> None:
        """Clear the current session."""
        self._auth.logout()

    @property
    def is_authenticated(self) -> bool:
        return self._auth.is_authenticated

    # ------------------------------------------------------------------
    # Auto-refresh
    # ------------------------------------------------------------------

    def enable_auto_refresh(self, interval: int = 300) -> None:
        """Start background session refresh every *interval* seconds."""
        if self._auto_refresh is not None and self._auto_refresh.is_running:
            self._auto_refresh.stop()
        self._auto_refresh = SessionAutoRefresh(
            self.session_keepalive, interval=interval
        )
        self._auto_refresh.start()

    def disable_auto_refresh(self) -> None:
        """Stop background session refresh."""
        if self._auto_refresh is not None:
            self._auto_refresh.stop()
            self._auto_refresh = None

    def close(self) -> None:
        self.disable_auto_refresh()
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
