"""add_manage_users_and_manage_schools_to_api_tokens

Revision ID: 7a1b2c3d4e5f
Revises: 6b87c62d8e9a
Create Date: 2026-02-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '7a1b2c3d4e5f'
down_revision = '6b87c62d8e9a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add can_manage_users column before can_manage_training
    op.add_column('api_tokens',
        sa.Column('can_manage_users', mysql.TINYINT(), nullable=False, server_default='0')
    )

    # Add can_manage_schools column before can_manage_training
    op.add_column('api_tokens',
        sa.Column('can_manage_schools', mysql.TINYINT(), nullable=False, server_default='0')
    )


def downgrade() -> None:
    # Drop can_manage_users column
    op.drop_column('api_tokens', 'can_manage_users')

    # Drop can_manage_schools column
    op.drop_column('api_tokens', 'can_manage_schools')
