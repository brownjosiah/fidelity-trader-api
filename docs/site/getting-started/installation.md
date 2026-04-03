# Installation

```bash
pip install fidelity-trader-api
```

## Extras

| Extra | Install | What it adds |
|-------|---------|-------------|
| `cli` | `pip install fidelity-trader-api[cli]` | `ft` command-line tool (typer + rich) |
| `service` | `pip install fidelity-trader-api[service]` | FastAPI REST service + Docker support |
| `aws` | `pip install fidelity-trader-api[aws]` | AWS Secrets Manager / SSM credential providers |
| `dev` | `pip install fidelity-trader-api[dev]` | Testing (pytest, respx, boto3) |

**Requirements:** Python 3.10+ and a Fidelity brokerage account with Trader+ access.

## Verify CLI Installation

After installing with `[cli]`, verify the `ft` command is available:

```bash
ft --help
```

If you get "command not found", the Python Scripts directory isn't in your PATH:

**Windows (PowerShell):**
```powershell
# Find where pip installed it
python -c "import sysconfig; print(sysconfig.get_path('scripts'))"

# Add to PATH permanently (replace path with your output above)
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\Users\YourUser\AppData\Local\Programs\Python\Python312\Scripts", "User")

# Restart your terminal, then verify
ft --help
```

**Linux / macOS:**
```bash
# Usually ~/.local/bin — add to your shell profile if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Alternative** — invoke without PATH setup:
```bash
python -m fidelity_trader.cli --help
```
