from sqlalchemy import (Column, Integer, String, Text, TIMESTAMP, BigInteger, Index, event)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.sql import func
from app.extensions import db
import jieba

# Define a limit for the text to be indexed, slightly less than 1MB
TSVECTOR_MAX_LENGTH = 1000000

def segment_for_search(text):
    """Segments and truncates text for search indexing."""
    if not text:
        return ""
    # Truncate the text before segmentation to stay within limits
    truncated_text = text[:TSVECTOR_MAX_LENGTH]
    return " ".join(jieba.cut_for_search(truncated_text))

class Document(db.Model):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    file_name = Column(String(200), nullable=False)
    file_type = Column(String(50))
    file_size = Column(BigInteger)
    file_created_at = Column(TIMESTAMP)
    file_modified_time = Column(TIMESTAMP)
    file_path = Column(Text, nullable=False, unique=True)
    markdown_content = Column(Text)
    is_converted = Column(Integer)  # 0-直接存储，1-文本转Markdown，2-代码转Markdown，3-结构化转Markdown，4-转换失败
    search_vector = Column(TSVECTOR)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_documents_file_path', 'file_path', unique=True),
        Index('idx_documents_search_vector', 'search_vector', postgresql_using='gin')
    )

# --- SQLAlchemy Event Listeners to auto-update search_vector with Jieba --- 
@event.listens_for(Document, 'before_insert')
def before_document_insert(mapper, connection, target):
    """Create the search vector before a new document is inserted."""
    full_text = segment_for_search(target.file_name) + " " + segment_for_search(target.markdown_content)
    target.search_vector = func.to_tsvector('simple', full_text)

@event.listens_for(Document, 'before_update')
def before_document_update(mapper, connection, target):
    """Update the search vector if content has changed before an update."""
    if db.inspect(target).attrs.markdown_content.history.has_changes() or db.inspect(target).attrs.file_name.history.has_changes():
        full_text = segment_for_search(target.file_name) + " " + segment_for_search(target.markdown_content)
        target.search_vector = func.to_tsvector('simple', full_text)

class ConversionError(db.Model):
    __tablename__ = 'conversion_errors'

    id = Column(Integer, primary_key=True)
    file_name = Column(String(200), nullable=False)
    file_path = Column(Text, nullable=False)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

