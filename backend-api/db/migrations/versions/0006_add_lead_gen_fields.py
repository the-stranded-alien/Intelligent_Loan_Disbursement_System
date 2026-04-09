"""add lead gen fields

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-09
"""

from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('applications', sa.Column('city',                     sa.String(),  nullable=True))
    op.add_column('applications', sa.Column('state',                    sa.String(),  nullable=True))
    op.add_column('applications', sa.Column('residential_status',       sa.String(),  nullable=True))
    op.add_column('applications', sa.Column('years_at_current_address', sa.Integer(), nullable=True))
    op.add_column('applications', sa.Column('employer_name',            sa.String(),  nullable=True))
    op.add_column('applications', sa.Column('years_in_current_job',     sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('applications', 'years_in_current_job')
    op.drop_column('applications', 'employer_name')
    op.drop_column('applications', 'years_at_current_address')
    op.drop_column('applications', 'residential_status')
    op.drop_column('applications', 'state')
    op.drop_column('applications', 'city')
