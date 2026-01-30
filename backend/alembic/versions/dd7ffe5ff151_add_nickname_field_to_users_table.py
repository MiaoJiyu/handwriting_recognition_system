"""Add nickname field to users table

Revision ID: dd7ffe5ff151
Revises: 001
Create Date: 2026-01-29 04:34:46.010643

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'dd7ffe5ff151'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nickname column to users table
    op.add_column('users', sa.Column('nickname', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Remove nickname column from users table
    op.drop_column('users', 'nickname')
