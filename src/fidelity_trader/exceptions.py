class FidelityError(Exception):
    """Base exception for all SDK errors."""

class AuthenticationError(FidelityError):
    """Login or session creation failed."""

class SessionExpiredError(FidelityError):
    """Session cookies are no longer valid."""

class CSRFTokenError(FidelityError):
    """Failed to obtain CSRF token for protected endpoints."""

class APIError(FidelityError):
    """Fidelity API returned an unexpected error."""
    def __init__(self, message: str, status_code: int = None, response_body: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
