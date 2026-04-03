# Quick Start

Pick the interface that fits your workflow:

=== "CLI (Fastest)"

    ```bash
    pip install fidelity-trader-api[cli]

    # Login (prompts for credentials, or reads FIDELITY_USERNAME / FIDELITY_PASSWORD env vars)
    ft login

    # See your positions
    ft positions

    # Get a quote
    ft quote AAPL TSLA

    # Preview a trade (dry-run by default — no order placed)
    ft buy AAPL 10 --limit 150.00

    # Stream live quotes
    ft stream AAPL TSLA NVDA
    ```

=== "Python SDK"

    ```python
    from fidelity_trader import FidelityClient

    with FidelityClient() as client:
        client.login(username="your_username", password="your_password")

        # Discover accounts
        accounts = client.accounts.discover_accounts()
        acct_nums = [a.acct_num for a in accounts.accounts]

        # Get positions
        positions = client.positions.get_positions(acct_nums)
        for acct in positions.accounts:
            for p in acct.positions:
                print(f"{p.symbol}: {p.quantity} shares @ ${p.price_detail.last_price}")

        # Get balances
        balances = client.balances.get_balances(acct_nums)
    ```

=== "REST Service"

    ```bash
    pip install fidelity-trader-api[service]

    # Start the service
    python -m service

    # Or with Docker
    docker compose -f docker/docker-compose.yml up -d

    # Login
    curl -X POST http://localhost:8787/api/v1/auth/login \
      -H "Content-Type: application/json" \
      -d '{"username": "...", "password": "..."}'

    # Get positions
    curl http://localhost:8787/api/v1/accounts/Z12345678/positions
    ```
