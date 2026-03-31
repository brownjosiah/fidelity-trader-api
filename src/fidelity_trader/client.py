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
from fidelity_trader.research.data import ResearchAPI
from fidelity_trader.research.search import SearchAPI
from fidelity_trader.streaming.news import StreamingNewsAPI
from fidelity_trader.watchlists.watchlists import WatchlistAPI
from fidelity_trader.portfolio.accounts import AccountsAPI
from fidelity_trader.market_data.fastquote import FastQuoteAPI
from fidelity_trader.research.analytics import OptionAnalyticsAPI
from fidelity_trader.alerts.subscription import AlertsAPI


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

        # All modules share the same httpx client (and its cookie jar)
        self.positions = PositionsAPI(self._http)
        self.balances = BalancesAPI(self._http)
        self.option_summary = OptionSummaryAPI(self._http)
        self.transactions = TransactionsAPI(self._http)
        self.order_status = OrderStatusAPI(self._http)
        self.equity_orders = EquityOrderAPI(self._http)
        self.option_orders = MultiLegOptionOrderAPI(self._http)
        self.cancel_order = OrderCancelAPI(self._http)
        self.research = ResearchAPI(self._http)
        self.search = SearchAPI(self._http)
        self.streaming = StreamingNewsAPI(self._http)
        self.watchlists = WatchlistAPI(self._http)
        self.accounts = AccountsAPI(self._http)
        self.option_chain = FastQuoteAPI(self._http)
        self.option_analytics = OptionAnalyticsAPI(self._http)
        self.alerts = AlertsAPI(self._http)

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

    def close(self) -> None:
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
