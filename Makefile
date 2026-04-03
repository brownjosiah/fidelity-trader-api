.PHONY: openapi client-ts client-go clients test lint docs

# Export OpenAPI spec (3.1 native)
openapi:
	python scripts/export_openapi.py openapi.json

# Export OpenAPI spec downgraded to 3.0.3 (for client generators)
openapi-compat:
	python scripts/export_openapi.py openapi.json --downgrade

# Generate TypeScript client from OpenAPI spec
client-ts: openapi
	mkdir -p clients/typescript/src
	npx openapi-typescript openapi.json -o clients/typescript/src/types.ts

# Generate Go client from OpenAPI spec
client-go: openapi-compat
	mkdir -p clients/go
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
