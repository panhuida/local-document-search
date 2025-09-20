from sqlalchemy import (Column, Integer, String, Text, TIMESTAMP, BigInteger, Index)
from sqlalchemy.sql import func
from app.extensions import db
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


class WechatList(db.Model):
    """公众号列表"""
    __tablename__ = 'wechat_list'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='公众号列表ID')
    wechat_account_name = Column(String(100), nullable=False, comment='公众号名称')
    memo = Column(String(200), comment='备注')
    start_date = Column(db.Date, comment='开始日期')
    end_date = Column(db.Date, comment='结束日期')
    fakeid = Column(String(100), comment='公众号唯一标识')
    token = Column(String(100), comment='Token信息')
    cookie = Column(Text, comment='Cookie信息')
    begin = Column(Integer, default=0, comment='起始位置')
    count = Column(Integer, default=5, comment='采集数量')
    create_time = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment='创建时间')
    update_time = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), comment='更新时间')

    def to_dict(self):
        return {
            'id': self.id,
            'wechat_account_name': self.wechat_account_name,
            'memo': self.memo,
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'fakeid': self.fakeid,
            'token': self.token,
            'cookie': self.cookie,
            'begin': self.begin,
            'count': self.count,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S') if self.update_time else None
        }

class WechatArticleList(db.Model):
    """公众号文章列表"""
    __tablename__ = 'wechat_article_list'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='公众号文章列表ID')
    wechat_list_id = Column(Integer, comment='公众号列表ID')
    wechat_account_name = Column(String(100), comment='公众号名称')
    article_id = Column(String(100), comment='文章ID')
    article_title = Column(String(255), comment='文章标题')
    article_cover = Column(String(500), comment='文章封面')
    article_link = Column(String(500), comment='文章链接')
    article_author_name = Column(String(100), comment='文章作者')
    article_is_deleted = Column(String(10), comment='文章是否删除')
    is_downloaded = Column(String(10), default='否', comment='是否已下载')
    article_create_time = Column(TIMESTAMP(timezone=True), comment='文章创建时间')
    article_update_time = Column(TIMESTAMP(timezone=True), comment='文章更新时间')
    create_time = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment='创建时间')
    update_time = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), comment='更新时间')

    def to_dict(self):
        return {
            'id': self.id,
            'wechat_list_id': self.wechat_list_id,
            'wechat_account_name': self.wechat_account_name,
            'article_id': self.article_id,
            'article_title': self.article_title,
            'article_cover': self.article_cover,
            'article_link': self.article_link,
            'article_author_name': self.article_author_name,
            'article_is_deleted': self.article_is_deleted,
            'is_downloaded': self.is_downloaded,
            'article_create_time': self.article_create_time.strftime('%Y-%m-%d %H:%M:%S') if self.article_create_time else None,
            'article_update_time': self.article_update_time.strftime('%Y-%m-%d %H:%M:%S') if self.article_update_time else None,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S') if self.update_time else None
        }

