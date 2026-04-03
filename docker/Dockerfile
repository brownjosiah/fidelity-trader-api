# --- Build stage ---
FROM python:3.12-slim AS build
WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
COPY service/ service/
RUN pip install --no-cache-dir ".[service]"

# --- Runtime stage ---
FROM python:3.12-slim
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin/uvicorn /usr/local/bin/
COPY service/ /app/service/
COPY src/ /app/src/
WORKDIR /app

RUN useradd -m -r ftservice && \
    mkdir -p /app/data && \
    chown -R ftservice:ftservice /app/data
USER ftservice

EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8787/health')" || exit 1

CMD ["python", "-m", "service"]
