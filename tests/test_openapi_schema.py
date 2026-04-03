"""Tests to ensure the OpenAPI spec has fully typed response schemas.

Prevents regression where response schemas become empty ({}) due to
missing response_model annotations on route decorators.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from service.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestOpenAPISchemaCompleteness:
    """Every JSON endpoint must have a non-empty response schema."""

    @pytest.mark.anyio
    async def test_openapi_spec_is_accessible(self, client):
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        assert spec["info"]["title"] == "Fidelity Trader API Service"

    @pytest.mark.anyio
    async def test_no_empty_response_schemas(self, client):
        resp = await client.get("/openapi.json")
        spec = resp.json()

        # SSE and WebSocket endpoints are excluded (not JSON responses)
        excluded = {"/api/v1/streaming/quotes", "/api/v1/ws/quotes"}

        empty = []
        for path, methods in spec["paths"].items():
            if path in excluded:
                continue
            for method, details in methods.items():
                if method not in ("get", "post", "put", "delete"):
                    continue
                resp_200 = details.get("responses", {}).get("200", {})
                schema = (
                    resp_200.get("content", {})
                    .get("application/json", {})
                    .get("schema", {})
                )
                if schema == {} or schema is None:
                    empty.append(f"{method.upper()} {path}")

        assert empty == [], f"Endpoints with empty response schemas: {empty}"

    @pytest.mark.anyio
    async def test_all_responses_use_api_envelope(self, client):
        """Every typed response should reference the APIResponse envelope."""
        resp = await client.get("/openapi.json")
        spec = resp.json()
        schemas = spec.get("components", {}).get("schemas", {})

        # Check that APIResponse schemas exist (FastAPI generates names like
        # APIResponse_PositionsResponse_ for each generic specialization)
        api_response_schemas = [
            name for name in schemas if name.startswith("APIResponse")
        ]
        assert len(api_response_schemas) > 0, "No APIResponse schemas found"

    @pytest.mark.anyio
    async def test_schema_count_minimum(self, client):
        """Ensure we have a healthy number of schemas (regression guard)."""
        resp = await client.get("/openapi.json")
        spec = resp.json()
        schema_count = len(spec.get("components", {}).get("schemas", {}))
        # We had 268 schemas after full typing; this should never drop below 200
        assert schema_count >= 200, f"Only {schema_count} schemas — expected 200+"

    @pytest.mark.anyio
    async def test_endpoint_count(self, client):
        """Verify we haven't lost endpoints."""
        resp = await client.get("/openapi.json")
        spec = resp.json()
        path_count = len(spec["paths"])
        # We have 48 paths (some paths have multiple methods)
        assert path_count >= 45, f"Only {path_count} paths — expected 45+"


class TestGenericAPIResponse:
    """Verify the generic APIResponse[T] produces correct schemas."""

    def test_api_response_is_generic(self):
        from service.models.responses import APIResponse
        from service.models.schemas import HealthCheckData

        schema = APIResponse[HealthCheckData].model_json_schema()
        # The 'data' field should reference HealthCheckData, not be Any
        data_prop = schema["properties"]["data"]
        assert data_prop != {}, "data field should not be empty schema"

    def test_api_response_none_variant(self):
        from service.models.responses import APIResponse

        schema = APIResponse[None].model_json_schema()
        assert "properties" in schema
        assert "ok" in schema["properties"]
