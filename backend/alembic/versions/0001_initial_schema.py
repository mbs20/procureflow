"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. RFQs
    op.create_table(
        'rfqs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'ACTIVE', 'EVALUATING', 'DECIDED', 'ARCHIVED', name='rfqstatus'), nullable=False),
        sa.Column('reference_currency', sa.String(length=3), nullable=False),
        sa.Column('created_by', sa.String(length=100), nullable=False),
        sa.Column('is_archived', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. RFQ Line Items
    op.create_table(
        'rfq_line_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rfq_id', sa.String(length=36), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['rfq_id'], ['rfqs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Evaluation Criteria
    op.create_table(
        'evaluation_criteria',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rfq_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('weight', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('direction', sa.Enum('LOWER_IS_BETTER', 'HIGHER_IS_BETTER', name='criteriondirection'), nullable=False),
        sa.Column('is_knockout', sa.Boolean(), nullable=False),
        sa.Column('data_type', sa.Enum('PRICE', 'DAYS', 'PERCENTAGE', 'ENUM', 'BOOLEAN', 'TEXT', name='criteriondatatype'), nullable=False),
        sa.ForeignKeyConstraint(['rfq_id'], ['rfqs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. Supplier Quotations
    op.create_table(
        'supplier_quotations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rfq_id', sa.String(length=36), nullable=False),
        sa.Column('supplier_name', sa.String(length=255), nullable=False),
        sa.Column('supplier_reference', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('UPLOADED', 'QUEUED', 'EXTRACTING', 'NEEDS_REVIEW', 'APPROVED', 'REJECTED', 'FAILED', name='quotationstatus'), nullable=False),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['rfq_id'], ['rfqs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. Quotation Documents
    op.create_table(
        'quotation_documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('quotation_id', sa.String(length=36), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['quotation_id'], ['supplier_quotations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. Extracted Quotations
    op.create_table(
        'extracted_quotations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('quotation_id', sa.String(length=36), nullable=False),
        sa.Column('extraction_model', sa.String(length=100), nullable=False),
        sa.Column('extraction_version', sa.String(length=50), nullable=False),
        sa.Column('extracted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('overall_confidence', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=False),
        sa.Column('raw_llm_output', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('acknowledged_warnings', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['quotation_id'], ['supplier_quotations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 7. Extracted Quotation Fields
    op.create_table(
        'extracted_quotation_fields',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('extracted_quotation_id', sa.String(length=36), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('raw_value', sa.Text(), nullable=True),
        sa.Column('normalised_value', sa.JSON(), nullable=True),
        sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('source_evidence', sa.JSON(), nullable=True),
        sa.Column('source_bbox', sa.JSON(), nullable=True),
        sa.Column('human_corrected', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['extracted_quotation_id'], ['extracted_quotations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 8. Extracted Line Items
    op.create_table(
        'extracted_line_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('extracted_quotation_id', sa.String(length=36), nullable=False),
        sa.Column('rfq_line_item_id', sa.String(length=36), nullable=True),
        sa.Column('description_raw', sa.String(length=500), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('total_price', sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column('calculated_total_price', sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column('lead_time_days', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('source_evidence', sa.JSON(), nullable=True),
        sa.Column('source_bbox', sa.JSON(), nullable=True),
        sa.Column('human_corrected', sa.Boolean(), nullable=False),
        sa.Column('is_removed', sa.Boolean(), nullable=False),
        sa.Column('removal_reason', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['extracted_quotation_id'], ['extracted_quotations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rfq_line_item_id'], ['rfq_line_items.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 9. Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rfq_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('actor_type', sa.Enum('USER', 'SYSTEM', name='actortype'), nullable=False),
        sa.Column('actor_id', sa.String(length=100), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(['rfq_id'], ['rfqs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_rfq_time', 'audit_logs', ['rfq_id', 'timestamp'], unique=False)

    # 10. Legacy Scoring & Decision Tables (Phase 0)
    op.create_table(
        'score_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rfq_id', sa.String(length=36), nullable=False),
        sa.Column('scoring_strategy', sa.String(length=100), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('currency_snapshot', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['rfq_id'], ['rfqs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'supplier_scores',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('score_result_id', sa.String(length=36), nullable=False),
        sa.Column('quotation_id', sa.String(length=36), nullable=False),
        sa.Column('supplier_name', sa.String(length=255), nullable=False),
        sa.Column('total_score', sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('is_eliminated', sa.Boolean(), nullable=False),
        sa.Column('elimination_reason', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['quotation_id'], ['supplier_quotations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['score_result_id'], ['score_results.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'criterion_scores',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('supplier_score_id', sa.String(length=36), nullable=False),
        sa.Column('criterion_id', sa.String(length=36), nullable=False),
        sa.Column('criterion_name', sa.String(length=100), nullable=False),
        sa.Column('raw_value', sa.String(length=100), nullable=True),
        sa.Column('normalised_value', sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column('weighted_contribution', sa.Numeric(precision=7, scale=4), nullable=False),
        sa.ForeignKeyConstraint(['criterion_id'], ['evaluation_criteria.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_score_id'], ['supplier_scores.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'ai_narratives',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('score_result_id', sa.String(length=36), nullable=False),
        sa.Column('model_used', sa.String(length=100), nullable=False),
        sa.Column('prompt_hash', sa.String(length=64), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('edited_text', sa.Text(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['score_result_id'], ['score_results.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'procurement_decisions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rfq_id', sa.String(length=36), nullable=False),
        sa.Column('score_result_id', sa.String(length=36), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('decided_by', sa.String(length=100), nullable=False),
        sa.Column('selected_quotation_ids', sa.JSON(), nullable=False),
        sa.Column('justification', sa.Text(), nullable=False),
        sa.Column('followed_ai_recommendation', sa.Boolean(), nullable=False),
        sa.Column('is_partial_award', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['rfq_id'], ['rfqs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['score_result_id'], ['score_results.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('procurement_decisions')
    op.drop_table('ai_narratives')
    op.drop_table('criterion_scores')
    op.drop_table('supplier_scores')
    op.drop_table('score_results')
    op.drop_table('audit_logs')
    op.drop_table('extracted_line_items')
    op.drop_table('extracted_quotation_fields')
    op.drop_table('extracted_quotations')
    op.drop_table('quotation_documents')
    op.drop_table('supplier_quotations')
    op.drop_table('evaluation_criteria')
    op.drop_table('rfq_line_items')
    op.drop_table('rfqs')
