"""create rm_reviews table

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-13
"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rm_reviews',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('application_id', sa.String(), sa.ForeignKey('applications.id'), nullable=False),
        sa.Column('rm_id', sa.String(), nullable=False),
        sa.Column('decision', sa.String(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('conditions', sa.JSON(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_rm_reviews_application_id', 'rm_reviews', ['application_id'])


def downgrade() -> None:
    op.drop_index('ix_rm_reviews_application_id', 'rm_reviews')
    op.drop_table('rm_reviews')
