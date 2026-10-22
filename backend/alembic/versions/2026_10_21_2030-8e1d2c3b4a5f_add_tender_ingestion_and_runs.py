"""add_tender_ingestion_and_runs

Revision ID: 8e1d2c3b4a5f
Revises: 7c2a8f91b34e
Create Date: 2026-10-21 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8e1d2c3b4a5f'
down_revision: Union[str, None] = '7c2a8f91b34e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tender extensions for automated government tender ingestion
    op.add_column(
        'tenders',
        sa.Column('source_portal', sa.String(length=50), server_default='MANUAL', nullable=False),
    )
    op.create_index('ix_tenders_source_portal', 'tenders', ['source_portal'], unique=False)

    op.add_column(
        'tenders',
        sa.Column('source_tender_id', sa.String(length=100), nullable=True),
    )
    op.create_index('ix_tenders_source_tender_id', 'tenders', ['source_tender_id'], unique=False)

    op.add_column(
        'tenders',
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'tenders',
        sa.Column(
            'ingestion_metadata',
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
            nullable=True,
        ),
    )
    op.create_index('ix_tenders_source_portal_id', 'tenders', ['source_portal', 'source_tender_id'], unique=False)

    # 2. Ingestion Runs Audit Table
    op.create_table(
        'ingestion_runs',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('source_portal', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='RUNNING', nullable=False),
        sa.Column('tenders_found', sa.Integer(), server_default='0', nullable=False),
        sa.Column('tenders_ingested', sa.Integer(), server_default='0', nullable=False),
        sa.Column('tenders_updated', sa.Integer(), server_default='0', nullable=False),
        sa.Column('tenders_skipped', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column(
            'run_metadata',
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
            nullable=True,
        ),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_ingestion_runs_source_portal', 'ingestion_runs', ['source_portal'], unique=False)
    op.create_index('ix_ingestion_runs_status', 'ingestion_runs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ingestion_runs_status', table_name='ingestion_runs')
    op.drop_index('ix_ingestion_runs_source_portal', table_name='ingestion_runs')
    op.drop_table('ingestion_runs')

    op.drop_index('ix_tenders_source_portal_id', table_name='tenders')
    op.drop_column('tenders', 'ingestion_metadata')
    op.drop_column('tenders', 'last_synced_at')
    op.drop_index('ix_tenders_source_tender_id', table_name='tenders')
    op.drop_column('tenders', 'source_tender_id')
    op.drop_index('ix_tenders_source_portal', table_name='tenders')
    op.drop_column('tenders', 'source_portal')
