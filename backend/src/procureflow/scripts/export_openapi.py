"""
Export FastAPI OpenAPI specification to a static JSON file.
Ensures documentation is versioned and avoids drift.
"""

import json
from pathlib import Path

from procureflow.main import app


def find_repo_root() -> Path:
    # Walk upwards looking for .git or README.md
    curr = Path(__file__).resolve()
    for parent in curr.parents:
        if (parent / "README.md").exists() and (parent / "backend").exists():
            return parent
    # Fallback to backend parent or current working directory
    return Path.cwd()


def export_openapi(output_path: Path | None = None) -> Path:
    if output_path is None:
        root = find_repo_root()
        output_path = root / "docs" / "api" / "openapi.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    print(f"Exported OpenAPI spec ({len(schema.get('paths', {}))} paths) to {output_path}")
    return output_path


if __name__ == "__main__":
    export_openapi()
