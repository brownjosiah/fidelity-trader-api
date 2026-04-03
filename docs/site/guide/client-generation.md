# Client Generation (Go / TypeScript)

The REST service auto-generates a fully typed [OpenAPI spec](https://swagger.io/specification/) with **268 component schemas** covering all 51 JSON endpoints. Use it to generate native clients in any language — no hand-written API wrappers needed.

## Pre-generated Clients

Ready-to-use clients are included in the repo:

| Language | Location | Lines | Generator |
|----------|----------|-------|-----------|
| **Go** | `clients/go/client.gen.go` | 9,756 | [oapi-codegen](https://github.com/oapi-codegen/oapi-codegen) |
| **TypeScript** | `clients/typescript/src/types.ts` | 6,172 | [openapi-typescript](https://github.com/openapi-ts/openapi-typescript) |

## Go

### Installation

```go
go get github.com/brownjosiah/fidelity-trader-api/clients/go
```

### Usage

```go
package main

import (
    "context"
    "fmt"
    fidelitytrader "github.com/brownjosiah/fidelity-trader-api/clients/go"
)

func main() {
    client, err := fidelitytrader.NewClient("http://localhost:8787")
    if err != nil {
        panic(err)
    }

    ctx := context.Background()

    // Get positions
    resp, err := client.GetApiV1AccountsAcctPositions(ctx, "Z12345678")
    if err != nil {
        panic(err)
    }
    defer resp.Body.Close()
    // Parse resp.Body as APIResponsePositionsResponse
}
```

## TypeScript

### Installation

```bash
npm install openapi-fetch
```

Copy `clients/typescript/src/types.ts` into your project, or install directly from the repo.

### Usage

```typescript
import type { paths } from "./types";
import createClient from "openapi-fetch";

const client = createClient<paths>({ baseUrl: "http://localhost:8787" });

// Get positions (fully typed response)
const { data, error } = await client.GET("/api/v1/accounts/{acct}/positions", {
  params: { path: { acct: "Z12345678" } },
});

if (data?.ok) {
  console.log(data.data); // typed as PositionsResponse
}
```

## Regenerate Clients

If the API changes, regenerate the clients from the updated spec:

```bash
# Export the OpenAPI spec
make openapi            # OpenAPI 3.1 (for TypeScript)
make openapi-compat     # OpenAPI 3.0.3 (for Go / openapi-generator)

# Generate clients
make client-ts          # TypeScript types
make client-go          # Go client + types
make clients            # Both
```

## Other Languages

Export the spec and use any [OpenAPI Generator](https://openapi-generator.tech/):

```bash
make openapi-compat

# Java
npx @openapitools/openapi-generator-cli generate \
  -i openapi.json -g java -o clients/java

# Rust
npx @openapitools/openapi-generator-cli generate \
  -i openapi.json -g rust -o clients/rust

# C#
npx @openapitools/openapi-generator-cli generate \
  -i openapi.json -g csharp -o clients/csharp

# Python (alternative SDK)
npx @openapitools/openapi-generator-cli generate \
  -i openapi.json -g python -o clients/python-generated
```

See the full list of supported languages at [openapi-generator.tech/docs/generators](https://openapi-generator.tech/docs/generators/).

## OpenAPI Spec Details

The spec is generated from the FastAPI service and includes:

- **48 paths** covering all REST endpoints
- **268 component schemas** with full nested type definitions
- **Typed request bodies** for orders, login, analytics, etc.
- **Typed response envelopes** — every response is `APIResponse[T]` with typed `data` field

!!! note "OpenAPI 3.1 vs 3.0"
    The service natively generates **OpenAPI 3.1**. TypeScript tooling supports 3.1 natively. Go and most other generators require **3.0.3** — use `make openapi-compat` which automatically downgrades `anyOf` null types, type arrays, and other 3.1-specific features.

## Viewing the Spec

The spec is available at runtime from the service:

```bash
# Interactive docs (Swagger UI)
open http://localhost:8787/docs

# Raw JSON spec
curl http://localhost:8787/openapi.json

# ReDoc
open http://localhost:8787/redoc
```

The `openapi.json` is also attached to every [GitHub Release](https://github.com/brownjosiah/fidelity-trader-api/releases) as a downloadable artifact.
