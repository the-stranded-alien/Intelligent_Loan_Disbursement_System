"""add agent_traces table

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'agent_traces',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('application_id', sa.String(), sa.ForeignKey('applications.id'), nullable=True),
        sa.Column('agent_role', sa.String(), nullable=False),
        sa.Column('node_name', sa.String(), nullable=False),
        sa.Column('prompt_rendered', sa.Text()),
        sa.Column('raw_llm_response', sa.Text()),
        sa.Column('parsed_output', sa.JSON()),
        sa.Column('duration_ms', sa.Integer()),
        sa.Column('model', sa.String()),
        sa.Column('input_tokens', sa.Integer()),
        sa.Column('output_tokens', sa.Integer()),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_agent_traces_application_id', 'agent_traces', ['application_id'])
    op.create_index('ix_agent_traces_node_name', 'agent_traces', ['node_name'])


def downgrade() -> None:
    op.drop_index('ix_agent_traces_node_name', 'agent_traces')
    op.drop_index('ix_agent_traces_application_id', 'agent_traces')
    op.drop_table('agent_traces')
