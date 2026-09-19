"""
Unit tests for Actor & Credential Protection.

Ensures that secret API keys and tokens such as procureflow_dev_api_key_12345
are never exposed through serialized responses, audit logs, event streams, or revision histories.
"""

from datetime import datetime, timezone
import pytest

from procureflow.api.deps import get_safe_principal, sanitize_actor
from procureflow.schemas.decision import (
    AwardDecisionEventResponse,
    AwardEventType,
    NarrativeRevisionResponse,
)
from procureflow.schemas.audit import AuditLogRead
from procureflow.models.audit import ActorType


class TestActorProtection:
    @pytest.mark.parametrize(
        "raw_secret,expected_label",
        [
            ("procureflow_dev_api_key_12345", "Development API Principal"),
            ("dev_api_key_custom", "Development API Principal"),
            ("sk_test_123456789", "Authenticated API Principal"),
            ("pk_test_987654321", "Authenticated API Principal"),
            ("test_key_master", "test_key_master"),
            ("procureflow_sec_9999", "Authenticated API Principal"),
            ("api_key_production_secret", "Authenticated API Principal"),
            ("buyer_officer_42", "buyer_officer_42"),
            ("evaluator_admin", "evaluator_admin"),
            ("", "System User"),
            (None, "System User"),
        ],
    )
    def test_get_safe_principal(self, raw_secret: str | None, expected_label: str):
        assert get_safe_principal(raw_secret) == expected_label
        assert sanitize_actor(raw_secret) == expected_label

    def test_award_decision_event_response_sanitizes_actor(self):
        event = AwardDecisionEventResponse(
            id="evt-1",
            award_decision_id="award-1",
            event_type=AwardEventType.DRAFT_CREATED,
            event_number=1,
            event_payload={"test": "data"},
            actor_principal="procureflow_dev_api_key_12345",
            created_at=datetime.now(timezone.utc),
        )
        assert event.actor_principal == "Development API Principal"
        assert "procureflow_dev_api_key_12345" not in event.model_dump_json()

    def test_narrative_revision_response_sanitizes_revised_by(self):
        revision = NarrativeRevisionResponse(
            id="rev-1",
            narrative_generation_id="narr-1",
            revision_number=1,
            revised_text="Updated text",
            revision_rationale="Clarification",
            revised_by="procureflow_dev_api_key_12345",
            revised_at=datetime.now(timezone.utc),
        )
        assert revision.revised_by == "Development API Principal"
        assert "procureflow_dev_api_key_12345" not in revision.model_dump_json()

    def test_audit_log_read_sanitizes_actor_id(self):
        log = AuditLogRead(
            id="log-1",
            rfq_id="rfq-1",
            event_type="LINE_ITEM_CORRECTED",
            actor_type=ActorType.USER,
            actor_id="procureflow_dev_api_key_12345",
            timestamp=datetime.now(timezone.utc),
        )
        assert log.actor_id == "Development API Principal"
        assert "procureflow_dev_api_key_12345" not in log.model_dump_json()
