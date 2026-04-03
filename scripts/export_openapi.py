"""Export the OpenAPI spec from the FastAPI service to openapi.json."""

import json
import os
import sys

# Ensure the project root is on the path so 'service' can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from service.app import create_app

app = create_app()
spec = app.openapi()

if len(sys.argv) > 1:
    with open(sys.argv[1], "w") as f:
        json.dump(spec, f, indent=2)
    print(f"Wrote {sys.argv[1]} ({len(spec['paths'])} paths, {len(spec.get('components', {}).get('schemas', {}))} schemas)")
else:
    print(json.dumps(spec, indent=2))
