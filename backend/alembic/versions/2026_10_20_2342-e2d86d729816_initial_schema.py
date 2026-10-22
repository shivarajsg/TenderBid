"""initial_schema_users_companies_documents

Revision ID: e2d86d729816
Revises: 
Create Date: 2026-10-20 23:42:43.886463

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2d86d729816'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), server_default='MSME_USER', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Create companies table
    op.create_table(
        'companies',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('owner_id', sa.Uuid(), nullable=False),
        sa.Column('legal_name', sa.String(length=255), nullable=False),
        sa.Column('registration_number', sa.String(length=100), nullable=False),
        sa.Column('business_type', sa.String(length=50), server_default='SMALL', nullable=False),
        sa.Column('sector', sa.String(length=100), nullable=False),
        sa.Column('incorporation_date', sa.Date(), nullable=False),
        sa.Column('annual_turnover', sa.JSON(), nullable=False),
        sa.Column('certifications', sa.JSON(), nullable=False),
        sa.Column('work_experience', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_companies_owner_id'), 'companies', ['owner_id'], unique=True)
    op.create_index(op.f('ix_companies_registration_number'), 'companies', ['registration_number'], unique=True)
    op.create_index(op.f('ix_companies_sector'), 'companies', ['sector'], unique=False)

    # 3. Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('uploaded_by', sa.Uuid(), nullable=True),
        sa.Column('document_category', sa.String(length=50), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(length=512), nullable=False),
        sa.Column('mime_type', sa.String(length=100), server_default='application/pdf', nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('verification_status', sa.String(length=50), server_default='UNVERIFIED', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_documents_company_id'), 'documents', ['company_id'], unique=False)
    op.create_index(op.f('ix_documents_uploaded_by'), 'documents', ['uploaded_by'], unique=False)
    op.create_index(op.f('ix_documents_sha256_hash'), 'documents', ['sha256_hash'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_documents_sha256_hash'), table_name='documents')
    op.drop_index(op.f('ix_documents_uploaded_by'), table_name='documents')
    op.drop_index(op.f('ix_documents_company_id'), table_name='documents')
    op.drop_table('documents')

    op.drop_index(op.f('ix_companies_sector'), table_name='companies')
    op.drop_index(op.f('ix_companies_registration_number'), table_name='companies')
    op.drop_index(op.f('ix_companies_owner_id'), table_name='companies')
    op.drop_table('companies')

    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
