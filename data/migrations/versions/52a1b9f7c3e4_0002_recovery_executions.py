"""0002_recovery_executions

Revision ID: 52a1b9f7c3e4
Revises: ed105aca8bfc
Create Date: 2026-09-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '52a1b9f7c3e4'
down_revision: Union[str, None] = 'ed105aca8bfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'recovery_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('proposal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('amount_minor', sa.BigInteger(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('provider_reference', sa.String(length=255), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_error_code', sa.String(length=100), nullable=True),
        sa.Column('last_error_message', sa.String(length=500), nullable=True),
        sa.CheckConstraint('amount_minor >= 0', name=op.f('ck_recovery_executions_amount_non_negative')),
        sa.ForeignKeyConstraint(['case_id'], ['recovery_cases.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_recovery_executions')),
        sa.UniqueConstraint('idempotency_key', name=op.f('uq_recovery_executions_idempotency_key')),
    )
    op.create_index(op.f('ix_recovery_executions_case_id'), 'recovery_executions', ['case_id'], unique=False)
    op.create_index(op.f('ix_recovery_executions_proposal_id'), 'recovery_executions', ['proposal_id'], unique=False)
    op.create_index(op.f('ix_recovery_executions_target_id'), 'recovery_executions', ['target_id'], unique=False)
    op.create_index(op.f('ix_recovery_executions_customer_id'), 'recovery_executions', ['customer_id'], unique=False)
    op.create_index(op.f('ix_recovery_executions_status'), 'recovery_executions', ['status'], unique=False)
    op.create_index(op.f('ix_recovery_executions_provider_reference'), 'recovery_executions', ['provider_reference'], unique=False)
    op.create_index(op.f('ix_recovery_executions_idempotency_key'), 'recovery_executions', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_recovery_executions_created_at'), 'recovery_executions', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('recovery_executions')
