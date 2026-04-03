import os
from pathlib import Path

APP_NAME = "ft"


def get_config_dir() -> Path:
    """Cross-platform config directory: ~/.config/ft (Linux/Mac) or %APPDATA%/ft (Windows)."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home() / ".config"
    config_dir = base / APP_NAME
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


SESSION_FILE_NAME = "session.json"

# Environment variable names
ENV_USERNAME = "FIDELITY_USERNAME"
ENV_PASSWORD = "FIDELITY_PASSWORD"
ENV_TOTP_SECRET = "FIDELITY_TOTP_SECRET"
ENV_ACCOUNT = "FIDELITY_ACCOUNT"
ENV_LIVE_TRADING = "FIDELITY_LIVE_TRADING"
