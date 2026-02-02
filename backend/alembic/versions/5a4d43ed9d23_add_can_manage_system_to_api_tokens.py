"""add_can_manage_system_to_api_tokens

Revision ID: 5a4d43ed9d23
Revises: b785cb7ff951
Create Date: 2026-02-02 04:30:19.842666

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a4d43ed9d23'
down_revision = 'b785cb7ff951'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('api_tokens', sa.Column('can_manage_system', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('api_tokens', 'can_manage_system')
