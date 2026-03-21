"""add dob employment income to applications

Revision ID: 0006
Revises: 0005
Create Date: 2025-03-22
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("applications", sa.Column(
        "date_of_birth",   sa.String(), nullable=True))
    op.add_column("applications", sa.Column(
        "employment_type", sa.String(), nullable=True))
    op.add_column("applications", sa.Column(
        "monthly_income",  sa.Float(),  nullable=True))


def downgrade() -> None:
    op.drop_column("applications", "monthly_income")
    op.drop_column("applications", "employment_type")
    op.drop_column("applications", "date_of_birth")
