import re
from app.models import Document
from app.extensions import db
from sqlalchemy import func, cast, TEXT, literal_column
import sqlalchemy as sa

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
            # Use the &@~ operator for web-style search on the markdown_content column.
            score_col = literal_column("pgroonga_score(documents)").label("score")
            query = query.with_entities(Document, score_col)
            query = query.filter(Document.markdown_content.op('&@~')(keyword))
        
        elif search_type == 'trigram':
            # NOTE: similarity() functions are not suitable for filtering short keywords in long documents in this environment.
            # Instead, use a LIKE query, which is accelerated by the GIN trigram index, to find all documents containing the keyword.

            # We can still calculate a similarity score for ranking the results.
            similarity_score = func.greatest(
                func.similarity(Document.markdown_content, keyword),
                func.similarity(Document.file_name, keyword)
            ).label("similarity")
            
            query = query.with_entities(Document, similarity_score)

            # Use a case-insensitive LIKE query to find the substring. This is fast with the GIN index.
            search_pattern = f'%{keyword}%'
            query = query.filter(
                (Document.markdown_content.ilike(search_pattern)) |
                (Document.file_name.ilike(search_pattern))
            )

    # --- UNIFIED AND RESTRUCTURED SORTING LOGIC ---
    order_by_clause = None

    # 1. Handle relevance sort first
    if keyword and sort_by == 'relevance':
        if search_type == 'full_text':
            # For PGroonga, we order by the calculated score
            order_by_clause = db.desc("score")
        elif search_type == 'trigram':
            # For trigram, we order by the calculated similarity score
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