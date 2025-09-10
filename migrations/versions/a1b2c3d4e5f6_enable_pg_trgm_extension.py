"""enable pg_trgm extension

Revision ID: a1b2c3d4e5f6
Revises: 94099d3bfeb5
Create Date: 2025-09-10 20:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '3804e7d41343'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm;')


def downgrade():
    op.execute('DROP EXTENSION IF EXISTS pg_trgm;')
