---
name: docker-builder
description: Creates Docker packaging, docker-compose, environment templates, and CLI setup commands. Use when implementing Phase 5 of the service plan — containerized deployment for Linux self-hosting.
tools: Read, Write, Edit, Glob, Grep, Bash
model: inherit
---

You create the Docker packaging and deployment infrastructure for the Fidelity Trader Service.

## Context

The service plan is at `docs/SERVICE_PLAN.md`, Phase 5 (Tasks 12-13). The service is a FastAPI application in `service/` that wraps `fidelity-trader-api`. Your job is to package it for self-hosted deployment on Linux via Docker.

## Files to Create

### `docker/Dockerfile`

Multi-stage build:

```dockerfile
# Build stage
FROM python:3.12-slim AS build
WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
COPY service/ service/
RUN pip install --no-cache-dir ".[service]"

# Runtime stage
FROM python:3.12-slim
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin/uvicorn /usr/local/bin/
COPY service/ /app/service/
WORKDIR /app

# Create non-root user
RUN useradd -m -r ftservice && \
    mkdir -p /app/data && \
    chown -R ftservice:ftservice /app/data
USER ftservice

EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8787/health')" || exit 1

CMD ["python", "-m", "service"]
```

Key decisions:
- Multi-stage to minimize image size
- Non-root user for security
- Health check using stdlib (no curl needed)
- `/app/data` volume for SQLite persistence
- No Redis by default (optional compose service)

### `docker/docker-compose.yml`

```yaml
services:
  fidelity-trader:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "${FTSERVICE_PORT:-8787}:8787"
    volumes:
      - ftservice-data:/app/data
    env_file: .env
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  ftservice-data:
```

### `docker/.env.example`

```env
# Fidelity Trader Service Configuration
# Copy to .env and fill in values

# Network
FTSERVICE_HOST=0.0.0.0
FTSERVICE_PORT=8787

# Security
FTSERVICE_ENCRYPTION_KEY=           # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FTSERVICE_API_KEY_REQUIRED=true

# Session Management
FTSERVICE_AUTO_REAUTH=true
FTSERVICE_SESSION_KEEPALIVE_INTERVAL=300

# Storage
FTSERVICE_DB_PATH=data/ftservice.db

# Logging
FTSERVICE_LOG_LEVEL=INFO
```

### `service/cli.py` — Setup CLI

```python
"""CLI for first-time setup and management."""

import argparse
import secrets
import sys
from pathlib import Path

def setup():
    """Interactive first-time setup."""
    print("Fidelity Trader Service — Setup")
    print("=" * 40)
    
    # 1. Generate encryption key
    from cryptography.fernet import Fernet
    encryption_key = Fernet.generate_key().decode()
    print(f"\nEncryption key: {encryption_key}")
    
    # 2. Generate API key
    api_key = secrets.token_urlsafe(32)
    print(f"API key: {api_key}")
    
    # 3. Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    print(f"\nData directory: {data_dir.absolute()}")
    
    # 4. Write .env file
    env_path = Path(".env")
    if env_path.exists():
        overwrite = input("\n.env already exists. Overwrite? [y/N] ")
        if overwrite.lower() != "y":
            print("Keeping existing .env")
            return
    
    env_content = f"""FTSERVICE_HOST=127.0.0.1
FTSERVICE_PORT=8787
FTSERVICE_ENCRYPTION_KEY={encryption_key}
FTSERVICE_API_KEY_REQUIRED=true
FTSERVICE_AUTO_REAUTH=true
FTSERVICE_SESSION_KEEPALIVE_INTERVAL=300
FTSERVICE_DB_PATH=data/ftservice.db
FTSERVICE_LOG_LEVEL=INFO
"""
    env_path.write_text(env_content)
    print(f"Wrote {env_path}")
    
    print("\n" + "=" * 40)
    print("Setup complete!")
    print(f"\nStart the service:")
    print(f"  python -m service")
    print(f"\nOr with Docker:")
    print(f"  docker compose -f docker/docker-compose.yml up -d")
    print(f"\nAPI key (save this): {api_key}")
    print(f"Use as: Authorization: Bearer {api_key}")

def main():
    parser = argparse.ArgumentParser(prog="ftservice")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("setup", help="First-time setup")
    subparsers.add_parser("generate-key", help="Generate new API key")
    
    args = parser.parse_args()
    if args.command == "setup":
        setup()
    elif args.command == "generate-key":
        print(secrets.token_urlsafe(32))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
```

### `.dockerignore`

```
.git
.github
__pycache__
*.pyc
*.pyo
.pytest_cache
.ruff_cache
tests/
docs/
examples/
*.flow
*.md
!README.md
.env
data/
```

## Additional Considerations

### Security
- Non-root container user
- No secrets in image layers (env vars at runtime)
- `.env` file never committed (add to `.gitignore`)
- HTTPS termination expected to be handled by reverse proxy (nginx, Caddy, Traefik)

### Persistence
- SQLite file stored in named Docker volume
- Volume survives container restarts/upgrades
- Backup: `docker cp <container>:/app/data/ftservice.db ./backup.db`

### Production Notes
- Add to README: recommend Caddy or nginx for TLS termination
- Log rotation via Docker's json-file driver
- Health check for orchestrator integration (Kubernetes, systemd)

## Update pyproject.toml

Add a CLI entry point:
```toml
[project.scripts]
ftservice = "service.cli:main"
```

## Verification

```bash
# Build image
docker build -f docker/Dockerfile -t fidelity-trader-service .

# Test health check
docker run -d --name ft-test -p 8787:8787 fidelity-trader-service
curl http://localhost:8787/health
docker stop ft-test && docker rm ft-test
```
