# Error Handling

```python
from fidelity_trader import (
    FidelityError,          # Base exception
    AuthenticationError,    # Login failed
    SessionExpiredError,    # Session cookies expired
    CSRFTokenError,         # CSRF token error
    APIError,               # API error (has .status_code, .response_body)
    DryRunError,            # Order blocked by dry-run mode
)
```
