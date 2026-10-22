"""add_company_capability_profile_fields

Revision ID: 9f2b3c4d5e6a
Revises: 8e1d2c3b4a5f
Create Date: 2026-10-23 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9f2b3c4d5e6a'
down_revision: Union[str, None] = '8e1d2c3b4a5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add capability & compliance profile columns to companies
    op.add_column('companies', sa.Column('trade_name', sa.String(length=255), nullable=True))
    op.add_column('companies', sa.Column('constitution', sa.String(length=50), server_default='PRIVATE_LIMITED', nullable=True))
    op.add_column('companies', sa.Column('pan_number', sa.String(length=10), nullable=True))
    op.add_column('companies', sa.Column('gstin', sa.String(length=15), nullable=True))
    op.add_column('companies', sa.Column('udyam_number', sa.String(length=50), nullable=True))
    op.add_column('companies', sa.Column('dpiit_recognition_number', sa.String(length=50), nullable=True))
    op.add_column('companies', sa.Column('address', sa.JSON(), server_default='{}', nullable=True))
    op.add_column('companies', sa.Column('contact_details', sa.JSON(), server_default='{}', nullable=True))
    op.add_column('companies', sa.Column('technical_capabilities', sa.JSON(), server_default='{}', nullable=True))
    op.add_column('companies', sa.Column('workforce_metrics', sa.JSON(), server_default='{}', nullable=True))
    op.add_column('companies', sa.Column('tender_exemptions', sa.JSON(), server_default='{}', nullable=True))
    op.add_column('companies', sa.Column('declarations', sa.JSON(), server_default='{}', nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'declarations')
    op.drop_column('companies', 'tender_exemptions')
    op.drop_column('companies', 'workforce_metrics')
    op.drop_column('companies', 'technical_capabilities')
    op.drop_column('companies', 'contact_details')
    op.drop_column('companies', 'address')
    op.drop_column('companies', 'dpiit_recognition_number')
    op.drop_column('companies', 'udyam_number')
    op.drop_column('companies', 'gstin')
    op.drop_column('companies', 'pan_number')
    op.drop_column('companies', 'constitution')
    op.drop_column('companies', 'trade_name')
