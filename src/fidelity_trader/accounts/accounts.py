import httpx
from fidelity_trader._http import BASE_URL
from fidelity_trader.models.account import Account, Balance, Position
from fidelity_trader.exceptions import APIError


class AccountsAPI:
    def __init__(self, http: httpx.Client, csrf_token: str = None) -> None:
        self._http = http
        self._csrf_token = csrf_token
        self._accounts: list[Account] = []

    def _csrf_headers(self) -> dict[str, str]:
        if not self._csrf_token:
            raise APIError("CSRF token required for this endpoint")
        return {"X-CSRF-TOKEN": self._csrf_token}

    def discover_accounts(self) -> list[Account]:
        """POST /ftgw/digital/pico/api/v1/context/account"""
        resp = self._http.post(f"{BASE_URL}/ftgw/digital/pico/api/v1/context/account", json={})
        resp.raise_for_status()
        data = resp.json()
        self._accounts = [Account.model_validate(acct) for acct in data.get("acctDetails", [])]
        return self._accounts

    def get_account(self, acct_num: str) -> Account:
        if not self._accounts:
            self.discover_accounts()
        for acct in self._accounts:
            if acct.acct_num == acct_num:
                return acct
        raise APIError(f"Account {acct_num} not found")

    def get_balances(self, acct_num: str) -> Balance:
        """POST /ftgw/digital/trade-options/api/balances (CSRF required)"""
        acct = self.get_account(acct_num) if self._accounts else None
        body = {
            "account": {
                "acctNum": acct_num,
                "isDefaultAcct": False,
                "accountDetails": {
                    "acctType": acct.acct_type if acct else "Brokerage",
                    "acctSubType": acct.acct_sub_type if acct else "Brokerage",
                    "acctSubTypeDesc": acct.acct_sub_type_desc if acct else "",
                    "name": acct.nickname if acct else "",
                    "isRetirement": acct.is_retirement if acct else False,
                },
                "optionLevel": acct.option_level if acct else 0,
                "isMarginEstb": acct.is_margin if acct else False,
                "isOptionEstb": acct.is_options_enabled if acct else False,
            }
        }
        resp = self._http.post(
            f"{BASE_URL}/ftgw/digital/trade-options/api/balances",
            json=body,
            headers=self._csrf_headers(),
        )
        resp.raise_for_status()
        return Balance.model_validate(resp.json())

    def get_positions(self, acct_num: str) -> list[Position]:
        """POST /ftgw/digital/trade-options/api/positions (CSRF required)"""
        acct = self.get_account(acct_num) if self._accounts else None
        body = {
            "acctNum": acct_num,
            "acctType": acct.acct_type if acct else "Brokerage",
            "acctSubType": acct.acct_sub_type if acct else "Brokerage",
            "retirementInd": acct.is_retirement if acct else False,
        }
        resp = self._http.post(
            f"{BASE_URL}/ftgw/digital/trade-options/api/positions",
            json=body,
            headers=self._csrf_headers(),
        )
        resp.raise_for_status()
        return [Position.model_validate(p) for p in resp.json().get("positionDetails", [])]
