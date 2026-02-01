"""add_api_tokens_table

Revision ID: 6b87c62d8e9a
Revises: dd7ffe5ff151
Create Date: 2026-01-31 14:52:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '6b87c62d8e9a'
down_revision = 'dd7ffe5ff151'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'api_tokens',
        sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('token', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255), nullable=False),
        sa.Column('name', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100), nullable=False),
        sa.Column('app_name', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100), nullable=True),
        sa.Column('app_version', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=50), nullable=True),
        sa.Column('scope', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=50), nullable=False, server_default='read'),
        sa.Column('can_read_samples', mysql.TINYINT(), nullable=False, server_default='1'),
        sa.Column('can_write_samples', mysql.TINYINT(), nullable=False, server_default='0'),
        sa.Column('can_recognize', mysql.TINYINT(), nullable=False, server_default='0'),
        sa.Column('can_read_users', mysql.TINYINT(), nullable=False, server_default='1'),
        sa.Column('can_manage_training', mysql.TINYINT(), nullable=False, server_default='0'),
        sa.Column('user_id', mysql.INTEGER(), nullable=False),
        sa.Column('school_id', mysql.INTEGER(), nullable=True),
        sa.Column('is_active', mysql.TINYINT(), nullable=False, server_default='1'),
        sa.Column('is_revoked', mysql.TINYINT(), nullable=False, server_default='0'),
        sa.Column('created_at', mysql.DATETIME(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('expires_at', mysql.DATETIME(), nullable=True),
        sa.Column('last_used_at', mysql.DATETIME(), nullable=True),
        sa.Column('revoked_at', mysql.DATETIME(), nullable=True),
        sa.Column('usage_count', mysql.INTEGER(), nullable=False, server_default='0'),
        sa.Column('last_ip', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=50), nullable=True),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        mysql_collate='utf8mb4_unicode_ci',
        mysql_default_charset='utf8mb4',
        mysql_engine='InnoDB'
    )
    op.create_index(op.f('ix_api_tokens_token'), 'api_tokens', ['token'], unique=True)
    op.create_index(op.f('ix_api_tokens_user_id'), 'api_tokens', ['user_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_api_tokens_user_id'), table_name='api_tokens')
    op.drop_index(op.f('ix_api_tokens_token'), table_name='api_tokens')
    op.drop_table('api_tokens')
