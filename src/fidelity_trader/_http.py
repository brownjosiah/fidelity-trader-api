import uuid
import httpx

from fidelity_trader.retry import RetryTransport

BASE_URL = "https://digital.fidelity.com"
AUTH_URL = "https://ecaap.fidelity.com"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0 "
        "ATPNext/4.4.1.7 FTPlusDesktop/4.4.1.7"
    ),
    "AppId": "RETAIL-CC-LOGIN-SDK",
    "AppName": "PILoginExperience",
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
    "Accept-Token-Type": "ET",
    "Accept-Token-Location": "HEADER",
    "Token-Location": "HEADER",
    "Cache-Control": "no-cache, no-store, must-revalidate",
}

# Data/Trading API host (from captured traffic)
DPSERVICE_URL = "https://dpservice.fidelity.com"
ALERTS_URL = "https://ecawsgateway.fidelity.com"
STREAMING_NEWS_URL = "https://streaming-news.mds.fidelity.com"
FASTQUOTE_URL = "https://fastquote.fidelity.com"

# Headers used by Fidelity Trader+ desktop app for data APIs
# (different from login headers which use RETAIL-CC-LOGIN-SDK)
ATP_HEADERS = {
    "AppId": "AP149323",
    "AppName": "Active Trader Desktop for Windows",
    "User-Agent": "ATPNext/4.4.1.7 FTPlusDesktop/4.4.1.7",
    "Content-Type": "application/json; charset=utf-8",
    "Accept": "application/json",
}

def create_session(timeout: float = 30.0) -> httpx.Client:
    return httpx.Client(follow_redirects=True, timeout=timeout, headers=REQUEST_HEADERS)

def create_atp_session(
    timeout: float = 30.0,
    max_retries: int = 0,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> httpx.Client:
    """Create a pre-configured httpx client for Fidelity Trader+ data APIs.

    When *max_retries* > 0, the underlying transport is wrapped in a
    :class:`RetryTransport` that retries on transient failures (connection
    errors, timeouts, 429/5xx status codes) with exponential backoff.
    The default (*max_retries=0*) preserves existing behaviour with no retry.
    """
    transport: httpx.BaseTransport | None = None
    if max_retries > 0:
        transport = RetryTransport(
            max_retries=max_retries,
            retry_delay=retry_delay,
            backoff_factor=backoff_factor,
        )
    return httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers=ATP_HEADERS,
        transport=transport,
    )

def make_req_id() -> str:
    return f"REQ{uuid.uuid4().hex}"
