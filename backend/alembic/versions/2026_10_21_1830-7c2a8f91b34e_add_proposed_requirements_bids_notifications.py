"""add_proposed_requirements_bids_notifications

Revision ID: 7c2a8f91b34e
Revises: ef93ccad0bf2
Create Date: 2026-10-21 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7c2a8f91b34e'
down_revision: Union[str, None] = 'ef93ccad0bf2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tender extensions for automated requirement extraction & approval
    op.add_column(
        'tenders',
        sa.Column(
            'proposed_requirements',
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
            nullable=True,
        )
    )
    op.add_column(
        'tenders',
        sa.Column(
            'requirements_approval_status',
            sa.String(length=50),
            server_default='APPROVED',
            nullable=False,
        )
    )
    op.create_index(
        op.f('ix_tenders_requirements_approval_status'),
        'tenders',
        ['requirements_approval_status'],
        unique=False,
    )

    # 2. Bid Application Tracking
    op.create_table(
        'bid_applications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('tender_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='IDENTIFIED', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('target_submission_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'tender_id', name='uq_company_tender_bid'),
    )
    op.create_index(op.f('ix_bid_applications_company_id'), 'bid_applications', ['company_id'], unique=False)
    op.create_index(op.f('ix_bid_applications_tender_id'), 'bid_applications', ['tender_id'], unique=False)
    op.create_index(op.f('ix_bid_applications_status'), 'bid_applications', ['status'], unique=False)

    # 3. Proactive Deadline Notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('tender_id', sa.Uuid(), nullable=True),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'tender_id', 'notification_type', name='uq_company_tender_notification'),
    )
    op.create_index(op.f('ix_notifications_company_id'), 'notifications', ['company_id'], unique=False)
    op.create_index(op.f('ix_notifications_tender_id'), 'notifications', ['tender_id'], unique=False)
    op.create_index(op.f('ix_notifications_notification_type'), 'notifications', ['notification_type'], unique=False)
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notifications_is_read'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_notification_type'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_tender_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_company_id'), table_name='notifications')
    op.drop_table('notifications')

    op.drop_index(op.f('ix_bid_applications_status'), table_name='bid_applications')
    op.drop_index(op.f('ix_bid_applications_tender_id'), table_name='bid_applications')
    op.drop_index(op.f('ix_bid_applications_company_id'), table_name='bid_applications')
    op.drop_table('bid_applications')

    op.drop_index(op.f('ix_tenders_requirements_approval_status'), table_name='tenders')
    op.drop_column('tenders', 'requirements_approval_status')
    op.drop_column('tenders', 'proposed_requirements')
