"""add gin index for trigram search

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-09-10 20:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'idx_documents_file_name_gin',
        'documents',
        ['file_name'],
        postgresql_using='gin',
        postgresql_ops={'file_name': 'gin_trgm_ops'}
    )
    op.create_index(
        'idx_documents_markdown_content_gin',
        'documents',
        ['markdown_content'],
        postgresql_using='gin',
        postgresql_ops={'markdown_content': 'gin_trgm_ops'}
    )


def downgrade():
    op.drop_index('idx_documents_markdown_content_gin', table_name='documents')
    op.drop_index('idx_documents_file_name_gin', table_name='documents')
