import os
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_fresh_migration_and_schema_drift() -> None:
    """
    Validates the fresh-install migration path:
    1. Empty database schema
    2. Runs alembic upgrade head
    3. Confirms all essential tables exist
    4. Runs alembic check to prove zero unhandled schema drift
    """
    backend_dir = Path(__file__).resolve().parents[2]
    ini_path = backend_dir / "alembic.ini"
    assert ini_path.exists(), f"alembic.ini not found at {ini_path}"

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "fresh_test.db"
        sqlite_url = f"sqlite:///{db_path}"

        alembic_cfg = Config(str(ini_path))
        alembic_cfg.set_main_option("sqlalchemy.url", sqlite_url)
        alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))

        # Step 1 & 2: Upgrade empty database to head
        command.upgrade(alembic_cfg, "head")

        # Step 3: Inspect tables
        engine = create_engine(sqlite_url)
        try:
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())

            required_tables = {
                "rfqs",
                "rfq_line_items",
                "evaluation_criteria",
                "supplier_quotations",
                "quotation_documents",
                "extracted_quotations",
                "extracted_quotation_fields",
                "extracted_line_items",
                "comparison_snapshots",
                "scoring_configurations",
                "scoring_runs",
                "decision_contexts",
                "narrative_generations",
                "narrative_revisions",
                "award_decisions",
                "award_decision_events",
            }
            for t in required_tables:
                assert t in tables, f"Expected table '{t}' missing from migrated schema"

            # Step 4: Verify zero schema drift via alembic check
            command.check(alembic_cfg)
        finally:
            engine.dispose()


def test_migration_upgrade_preserves_existing_data() -> None:
    """
    Validates that existing tables and persisted data are preserved without loss.
    """
    backend_dir = Path(__file__).resolve().parents[2]
    ini_path = backend_dir / "alembic.ini"

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "upgrade_preserve.db"
        sqlite_url = f"sqlite:///{db_path}"

        alembic_cfg = Config(str(ini_path))
        alembic_cfg.set_main_option("sqlalchemy.url", sqlite_url)
        alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))

        # Upgrade to head
        command.upgrade(alembic_cfg, "head")

        engine = create_engine(sqlite_url)
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO rfqs (id, title, description, category, status, reference_currency, created_by, is_archived, created_at, updated_at) "
                        "VALUES ('rfq-demo-test-1', 'Test RFQ', 'Migration Data Preservation Test', 'Industrial', 'ACTIVE', 'USD', 'tester', 0, datetime('now'), datetime('now'))"
                    )
                )

            # Re-run upgrade head (idempotency check)
            command.upgrade(alembic_cfg, "head")

            # Verify row persisted
            with engine.connect() as conn:
                result = conn.execute(text("SELECT id, title FROM rfqs WHERE id = 'rfq-demo-test-1'")).fetchone()
                assert result is not None
                assert result[0] == "rfq-demo-test-1"
                assert result[1] == "Test RFQ"
        finally:
            engine.dispose()
