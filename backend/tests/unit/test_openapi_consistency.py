import json
from pathlib import Path
import pytest

from procureflow.main import app
from procureflow.scripts.export_openapi import find_repo_root


def test_openapi_spec_is_up_to_date() -> None:
    """Ensure committed docs/api/openapi.json matches the actual FastAPI schema."""
    root = find_repo_root()
    spec_path = root / "docs" / "api" / "openapi.json"
    if not spec_path.exists() and Path("/app/docs/api/openapi.json").exists():
        spec_path = Path("/app/docs/api/openapi.json")

    if not spec_path.exists():
        # If in an isolated container without the docs volume mounted
        pytest.skip(f"OpenAPI spec does not exist at {spec_path} (docs not mounted in container). Verified in CI/host.")

    with open(spec_path, "r", encoding="utf-8") as f:
        committed_spec = json.load(f)

    current_spec = app.openapi()
    assert committed_spec == current_spec, (
        "Committed docs/api/openapi.json has drifted from current app.openapi(). "
        "Run `python -m procureflow.scripts.export_openapi` to regenerate."
    )
