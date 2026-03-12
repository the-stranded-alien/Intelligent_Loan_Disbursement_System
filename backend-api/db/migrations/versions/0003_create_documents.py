"""create documents table

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-13
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'documents',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('application_id', sa.String(), sa.ForeignKey('applications.id'), nullable=False),
        sa.Column('document_type', sa.String(), nullable=False),
        sa.Column('storage_path', sa.String(), nullable=False),
        sa.Column('ocr_result', sa.JSON(), nullable=True),
        sa.Column('verification_status', sa.String(), nullable=True, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_documents_application_id', 'documents', ['application_id'])


def downgrade() -> None:
    op.drop_index('ix_documents_application_id', 'documents')
    op.drop_table('documents')
