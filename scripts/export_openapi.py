"""Export the OpenAPI spec from the FastAPI service to openapi.json.

By default, exports as OpenAPI 3.1 (what FastAPI generates natively).
Use --downgrade to convert to 3.0.3 for compatibility with client
generators that don't support 3.1 yet (oapi-codegen, openapi-generator).
"""

import json
import os
import sys

# Ensure the project root is on the path so 'service' can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from service.app import create_app


def downgrade_to_3_0(spec: dict) -> dict:
    """Convert an OpenAPI 3.1.x spec to 3.0.3 for broader tool compatibility.

    Key changes:
    - openapi version 3.1.0 → 3.0.3
    - anyOf with null → nullable: true (3.0 style)
    - type arrays like ["string", "null"] → type: "string" + nullable: true
    - Remove const (3.1-only keyword)
    """
    spec["openapi"] = "3.0.3"

    def _fix_schema(schema):
        if not isinstance(schema, dict):
            return schema

        # Handle anyOf with null type (Pydantic v2 generates this for Optional)
        if "anyOf" in schema:
            non_null = [s for s in schema["anyOf"] if s != {"type": "null"}]
            has_null = len(non_null) < len(schema["anyOf"])
            if has_null and len(non_null) == 1:
                # anyOf: [SomeType, null] → SomeType + nullable: true
                schema.update(non_null[0])
                schema["nullable"] = True
                del schema["anyOf"]
            elif has_null and len(non_null) > 1:
                schema["anyOf"] = non_null
                schema["nullable"] = True

        # Handle type: "null" (from Optional[None] / NoneType)
        if schema.get("type") == "null":
            schema["nullable"] = True
            schema.pop("type")

        # Handle type arrays like ["string", "null"]
        if isinstance(schema.get("type"), list):
            types = schema["type"]
            non_null_types = [t for t in types if t != "null"]
            if "null" in types:
                schema["nullable"] = True
            if len(non_null_types) == 1:
                schema["type"] = non_null_types[0]
            elif len(non_null_types) == 0:
                schema.pop("type", None)

        # Remove const (3.1-only)
        schema.pop("const", None)

        # Recurse into nested schemas
        for key in ("properties", "items", "additionalProperties"):
            if key in schema:
                if isinstance(schema[key], dict):
                    if key == "properties":
                        for prop_name, prop_schema in schema[key].items():
                            _fix_schema(prop_schema)
                    else:
                        _fix_schema(schema[key])

        if "allOf" in schema:
            for item in schema["allOf"]:
                _fix_schema(item)
        if "anyOf" in schema:
            for item in schema["anyOf"]:
                _fix_schema(item)
        if "oneOf" in schema:
            for item in schema["oneOf"]:
                _fix_schema(item)

        return schema

    # Fix all component schemas
    for schema in spec.get("components", {}).get("schemas", {}).values():
        _fix_schema(schema)

    # Fix parameters and request/response bodies in paths
    for path_methods in spec.get("paths", {}).values():
        for details in path_methods.values():
            if not isinstance(details, dict):
                continue
            for param in details.get("parameters", []):
                if "schema" in param:
                    _fix_schema(param["schema"])
            req_body = details.get("requestBody", {})
            for content in req_body.get("content", {}).values():
                if "schema" in content:
                    _fix_schema(content["schema"])
            for resp in details.get("responses", {}).values():
                for content in resp.get("content", {}).values():
                    if "schema" in content:
                        _fix_schema(content["schema"])

    return spec


app = create_app()
spec = app.openapi()

downgrade = "--downgrade" in sys.argv
output_file = next((a for a in sys.argv[1:] if not a.startswith("--")), None)

if downgrade:
    spec = downgrade_to_3_0(spec)
    version_str = "3.0.3"
else:
    version_str = spec.get("openapi", "3.1.0")

if output_file:
    with open(output_file, "w") as f:
        json.dump(spec, f, indent=2)
    print(f"Wrote {output_file} (OpenAPI {version_str}, {len(spec['paths'])} paths, {len(spec.get('components', {}).get('schemas', {}))} schemas)")
else:
    print(json.dumps(spec, indent=2))
