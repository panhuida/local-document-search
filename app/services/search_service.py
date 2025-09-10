import re
from app.models import Document
from app.extensions import db
from sqlalchemy import func, cast, TEXT

def search_documents(keyword, sort_by='relevance', sort_order='desc', page=1, per_page=20, file_types=None, date_from=None, date_to=None):
    """搜索文档"""
    query = Document.query

    if file_types:
        query = query.filter(Document.file_type.in_(file_types))

    if date_from:
        query = query.filter(Document.file_modified_time >= date_from)
    if date_to:
        query = query.filter(Document.file_modified_time <= date_to)

    if keyword:
        # Process keyword for full-text search
        # Replace spaces and plus signs with '&' for AND logic
        processed_keyword = ' & '.join(re.split(r'[\s+]+', keyword))
        
        query = query.filter(
            db.or_(
                Document.search_vector.match(processed_keyword, postgresql_regconfig='simple'),
                func.similarity(cast(Document.file_name, TEXT), cast(keyword, TEXT)) > 0.1
            )
        )
        query = query.order_by(
            func.ts_rank(Document.search_vector, func.to_tsquery('simple', processed_keyword)).desc(),
            func.similarity(cast(Document.file_name, TEXT), cast(keyword, TEXT)).desc()
        )
    elif sort_by == 'filename':
        order = Document.file_name.desc() if sort_order == 'desc' else Document.file_name.asc()
        query = query.order_by(order)
    else:
        # Default sort order
        order = Document.file_modified_time.desc() if sort_order == 'desc' else Document.file_modified_time.asc()
        query = query.order_by(order)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return pagination