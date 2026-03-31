import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.transaction import TransactionHistoryResponse


class TransactionsAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_transaction_history(
        self,
        account_numbers: list[str],
        from_date: int,
        to_date: int,
        account_types: list[dict] = None,
    ) -> TransactionHistoryResponse:
        """Fetch transaction history for the given accounts.

        Args:
            account_numbers: List of account number strings.
            from_date: Start of date range as a Unix timestamp (seconds).
            to_date: End of date range as a Unix timestamp (seconds).
            account_types: Optional list of dicts with acctType, acctNum, sysOfRcd keys.
                If not provided, defaults to brokerage type for all accounts.
        """
        if account_types is None:
            acct_details = [
                {
                    "acctType": "brokerage",
                    "acctNum": num,
                    "sysOfRcd": None,
                }
                for num in account_numbers
            ]
        else:
            acct_details = account_types

        body = {
            "acctDetails": acct_details,
            "searchCriteriaDetail": {
                "txnType": None,
                "txnCat": None,
                "txnSubCat": None,
                "txnFromDate": from_date,
                "txnToDate": to_date,
                "securityDetail": None,
                "filterCriteriaDetail": {
                    "hasCoreStlmnt": False,
                    "hasFrgnTxn": False,
                    "hasPortfolioRetirementIncDetail": True,
                    "hasOnlyPortfolioRetirementIncDetail": True,
                    "hasAcctRetirementIncDetail": True,
                    "hasOnlyAcctRetirementIncDetail": True,
                    "hasIntradayTxn": False,
                    "hasJournaledTxn": False,
                    "hasOnlyContributionTxn": True,
                    "hasBasketName": True,
                },
            },
        }

        resp = self._http.post(
            f"{DPSERVICE_URL}/ftgw/dp/accountmanagement/transaction/history/v2",
            json=body,
        )
        resp.raise_for_status()
        return TransactionHistoryResponse.from_api_response(resp.json())
