import re
import jieba
from app.models import Document
from app.extensions import db
from sqlalchemy import func, cast, TEXT

def search_documents(keyword, search_type='full_text', sort_by='relevance', sort_order='desc', page=1, per_page=20, file_types=None, date_from=None, date_to=None):
    """搜索文档"""
    query = Document.query

    if file_types:
        query = query.filter(Document.file_type.in_(file_types))

    if date_from:
        query = query.filter(Document.file_modified_time >= date_from)
    if date_to:
        query = query.filter(Document.file_modified_time <= date_to)

    if keyword:
        if search_type == 'full_text':
            # Use jieba to segment Chinese keywords for full-text search
            segmented_keyword = ' & '.join(jieba.cut_for_search(keyword))
            query = query.filter(Document.search_vector.match(segmented_keyword, postgresql_regconfig='simple'))
        
        elif search_type == 'trigram':
            # Calculate similarity score against content and filename
            similarity_score = func.greatest(
                func.similarity(Document.markdown_content, keyword),
                func.similarity(Document.file_name, keyword)
            ).label("similarity")
            
            # Add the score to the query's selectable entities
            query = query.with_entities(Document, similarity_score)

    # --- UNIFIED AND RESTRUCTURED SORTING LOGIC ---
    order_by_clause = None

    # 1. Handle relevance sort first
    if keyword and sort_by == 'relevance':
        if search_type == 'full_text':
            processed_keyword = ' & '.join(re.split(r'[\s+]+', keyword))
            order_by_clause = func.ts_rank(Document.search_vector, func.to_tsquery('simple', processed_keyword)).desc()
        elif search_type == 'trigram':
            # For trigram, we now order by the calculated similarity score
            order_by_clause = db.desc("similarity")

    # 2. If relevance sort was not applicable, handle other sort options
    if order_by_clause is None:
        if sort_by == 'filename':
            order_by_clause = Document.file_name.desc() if sort_order == 'desc' else Document.file_name.asc()
        elif sort_by == 'mtime':
            order_by_clause = Document.file_modified_time.desc() if sort_order == 'desc' else Document.file_modified_time.asc()
        else:
            # 3. Final fallback to default sort order
            order_by_clause = Document.file_modified_time.desc()

    query = query.order_by(order_by_clause)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return pagination