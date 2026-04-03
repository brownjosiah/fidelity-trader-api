.PHONY: openapi client-ts client-go clients test lint docs

# Export OpenAPI spec from the running service
openapi:
	python scripts/export_openapi.py openapi.json

# Generate TypeScript client from OpenAPI spec
client-ts: openapi
	npx openapi-typescript openapi.json -o clients/typescript/src/types.ts

# Generate Go client from OpenAPI spec
client-go: openapi
	oapi-codegen --package fidelitytrader --generate types,client \
		openapi.json > clients/go/client.gen.go

# Generate all clients
clients: client-ts client-go

# Run tests
test:
	python -m pytest tests/ -q --tb=short

# Lint
lint:
	ruff check src/ service/ tests/

# Build docs locally
docs:
	mkdocs serve
