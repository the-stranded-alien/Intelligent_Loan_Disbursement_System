"""add applicant financial fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('applications', sa.Column('date_of_birth',       sa.String(),  nullable=True))
    op.add_column('applications', sa.Column('employment_type',     sa.String(),  nullable=True, server_default='salaried'))
    op.add_column('applications', sa.Column('monthly_income',      sa.Float(),   nullable=True, server_default='0'))
    op.add_column('applications', sa.Column('existing_emi_amount', sa.Float(),   nullable=True, server_default='0'))
    op.add_column('applications', sa.Column('bank_account_number', sa.String(),  nullable=True))
    op.add_column('applications', sa.Column('ifsc_code',           sa.String(),  nullable=True))


def downgrade() -> None:
    op.drop_column('applications', 'ifsc_code')
    op.drop_column('applications', 'bank_account_number')
    op.drop_column('applications', 'existing_emi_amount')
    op.drop_column('applications', 'monthly_income')
    op.drop_column('applications', 'employment_type')
    op.drop_column('applications', 'date_of_birth')
