"""add branch walkin fields to applications

Revision ID: 0005
Revises: 0004
Create Date: 2025-03-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("applications", sa.Column(
        "branch_code",             sa.String(),  nullable=True))
    op.add_column("applications", sa.Column(
        "branch_name",             sa.String(),  nullable=True))
    op.add_column("applications", sa.Column(
        "staff_id",                sa.String(),  nullable=True))
    op.add_column("applications", sa.Column(
        "staff_name",              sa.String(),  nullable=True))
    op.add_column("applications", sa.Column(
        "kyc_physically_seen",     sa.Boolean(), nullable=True))
    op.add_column("applications", sa.Column(
        "customer_consent_signed", sa.Boolean(), nullable=True))
    op.add_column("applications", sa.Column(
        "walk_in_timestamp",       sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("applications", "walk_in_timestamp")
    op.drop_column("applications", "customer_consent_signed")
    op.drop_column("applications", "kyc_physically_seen")
    op.drop_column("applications", "staff_name")
    op.drop_column("applications", "staff_id")
    op.drop_column("applications", "branch_name")
    op.drop_column("applications", "branch_code")
