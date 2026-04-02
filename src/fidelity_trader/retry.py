"""Retry transport for httpx with exponential backoff and rate-limit awareness."""

import time
import logging

import httpx

logger = logging.getLogger(__name__)

# Transient connection errors worth retrying
_RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.ConnectTimeout,
)


class RetryTransport(httpx.BaseTransport):
    """httpx transport wrapper that retries on transient failures.

    Wraps an underlying transport (defaults to ``httpx.HTTPTransport``) and
    replays requests that fail with connection errors, timeouts, or
    server-side status codes (429, 5xx).

    Rate-limit responses (HTTP 429) with a ``Retry-After`` header are
    respected: the transport sleeps for that many seconds instead of using
    exponential backoff.
    """

    def __init__(
        self,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
        retry_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504),
    ):
        self._transport = transport or httpx.HTTPTransport()
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._backoff_factor = backoff_factor
        self._retry_status_codes = retry_status_codes

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        last_exc: Exception | None = None
        last_response: httpx.Response | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = self._transport.handle_request(request)
            except _RETRYABLE_EXCEPTIONS as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    delay = self._retry_delay * (self._backoff_factor ** attempt)
                    logger.warning(
                        "Retry %d/%d for %s %s after %s (waiting %.1fs)",
                        attempt + 1,
                        self._max_retries,
                        request.method.decode() if isinstance(request.method, bytes) else request.method,
                        request.url,
                        type(exc).__name__,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                # Max retries exhausted — raise the last exception
                raise

            # Got a response — check if it's retryable
            if response.status_code not in self._retry_status_codes:
                return response

            last_response = response

            if attempt < self._max_retries:
                # For 429, respect Retry-After header if present
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after is not None:
                        try:
                            delay = float(retry_after)
                        except (ValueError, TypeError):
                            delay = self._retry_delay * (self._backoff_factor ** attempt)
                    else:
                        delay = self._retry_delay * (self._backoff_factor ** attempt)
                else:
                    delay = self._retry_delay * (self._backoff_factor ** attempt)

                logger.warning(
                    "Retry %d/%d for %s %s after HTTP %d (waiting %.1fs)",
                    attempt + 1,
                    self._max_retries,
                    request.method.decode() if isinstance(request.method, bytes) else request.method,
                    request.url,
                    response.status_code,
                    delay,
                )
                time.sleep(delay)
                continue

        # Max retries exhausted — return the last response
        assert last_response is not None
        return last_response

    def close(self) -> None:
        self._transport.close()
