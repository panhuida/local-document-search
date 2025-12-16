from sqlalchemy import (Column, Integer, String, Text, TIMESTAMP, BigInteger, Index)
from sqlalchemy.sql import func
from local_document_search.extensions import db
from sqlalchemy.dialects import postgresql

class ConversionType:
    DIRECT = 0
    TEXT_TO_MD = 1
    CODE_TO_MD = 2
    STRUCTURED_TO_MD = 3
    XMIND_TO_MD = 4
    IMAGE_TO_MD = 5
    VIDEO_METADATA = 6
    DRAWIO_TO_MD = 7
    HTML_TO_MD = 8  # New: standalone HTML conversion

class Document(db.Model):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    file_name = Column(String(200), nullable=False)
    file_type = Column(String(10))
    file_size = Column(BigInteger)
    file_created_at = Column(TIMESTAMP(timezone=True))
    file_modified_time = Column(TIMESTAMP(timezone=True))
    file_path = Column(Text, nullable=False, unique=True)
    markdown_content = Column(Text)
    conversion_type = Column(Integer)  # See ConversionType class
    status = Column(String(10), nullable=True) # pending, completed, failed
    error_message = Column(Text)
    source = Column(String(30), index=True)
    source_url = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_documents_file_path', 'file_path', unique=True),
        # Note: PGroonga indexes are created manually via SQL in the migration
        # and are not explicitly defined in the model's __table_args__.
    )

class IngestState(db.Model):
    __tablename__ = 'ingest_state'

    id = Column(Integer, primary_key=True)
    source = Column(String(30), nullable=False)
    scope_key = Column(Text, nullable=False)
    last_started_at = Column(TIMESTAMP(timezone=True))
    last_ended_at = Column(TIMESTAMP(timezone=True))
    last_error_message = Column(Text)
    cursor_updated_at = Column(TIMESTAMP(timezone=True))
    total_files = Column(Integer)
    processed = Column(Integer)
    skipped = Column(Integer)
    errors = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_ingest_state_source_scope', 'source', 'scope_key', unique=True),
    )

# The ConversionError table is no longer needed as its functionality is merged into the Document table.
# class ConversionError(db.Model):
#     __tablename__ = 'conversion_errors'
#
#     id = Column(Integer, primary_key=True)
#     file_name = Column(String(200), nullable=False)
#     file_path = Column(Text, nullable=False)
#     error_message = Column(Text)
#     created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
#     updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())



