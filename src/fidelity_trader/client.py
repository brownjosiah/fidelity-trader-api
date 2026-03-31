"""Main client that composes all Fidelity API modules."""

from fidelity_trader._http import create_atp_session, BASE_URL, AUTH_URL
from fidelity_trader.auth.session import AuthSession
from fidelity_trader.portfolio.positions import PositionsAPI
from fidelity_trader.portfolio.balances import BalancesAPI
from fidelity_trader.portfolio.option_summary import OptionSummaryAPI
from fidelity_trader.portfolio.transactions import TransactionsAPI
from fidelity_trader.orders.status import OrderStatusAPI
from fidelity_trader.research.data import ResearchAPI
from fidelity_trader.streaming.news import StreamingNewsAPI


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
        self.orders = OrderStatusAPI(self._http)
        self.research = ResearchAPI(self._http)
        self.streaming = StreamingNewsAPI(self._http)

    def login(self, username: str, password: str, totp_secret: str = None) -> dict:
        """Authenticate with Fidelity and establish a session.

        If totp_secret is provided, generates and submits a TOTP code for 2FA.
        """
        return self._auth.login(username, password, totp_secret=totp_secret)

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
