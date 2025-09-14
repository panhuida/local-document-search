import re
import time
from dataclasses import dataclass
from typing import List, Optional

from flask import current_app
from app.models import Document
from app.extensions import db
from sqlalchemy import func, cast, TEXT, literal_column
import sqlalchemy as sa

@dataclass
class SearchParams:
    """A data class to hold all search parameters."""
    keyword: Optional[str] = None
    search_type: str = 'full_text'
    sort_by: str = 'relevance'
    sort_order: str = 'desc'
    page: int = 1
    per_page: int = 20
    file_types: Optional[List[str]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

def search_documents(params: SearchParams):
    """搜索文档"""
    logger = current_app.logger
    start_time = time.time()

    # Start query by filtering for completed documents only
    query = Document.query.filter(Document.status == 'completed')

    if params.file_types:
        query = query.filter(Document.file_type.in_(params.file_types))

    if params.date_from:
        query = query.filter(Document.file_modified_time >= params.date_from)
    if params.date_to:
        query = query.filter(Document.file_modified_time <= params.date_to)

    if params.keyword:
        if params.search_type == 'full_text':
            # Use the &@~ operator for web-style search on the content column.
            score_col = literal_column("pgroonga_score(documents)").label("score")
            query = query.with_entities(Document, score_col)
            query = query.filter(Document.markdown_content.op('&@~')(params.keyword))
        
        elif params.search_type == 'trigram':
            # NOTE: similarity() functions are not suitable for filtering short keywords in long documents in this environment.
            # Instead, use a LIKE query, which is accelerated by the GIN trigram index, to find all documents containing the keyword.

            # We can still calculate a similarity score for ranking the results.
            similarity_score = func.greatest(
                func.similarity(Document.markdown_content, params.keyword),
                func.similarity(Document.file_name, params.keyword)
            ).label("similarity")
            
            query = query.with_entities(Document, similarity_score)

            # Use a case-insensitive LIKE query to find the substring. This is fast with the GIN index.
            search_pattern = f'%{params.keyword}%'
            query = query.filter(
                (Document.markdown_content.ilike(search_pattern)) |
                (Document.file_name.ilike(search_pattern))
            )

    # --- UNIFIED AND RESTRUCTURED SORTING LOGIC ---
    order_by_clause = None

    # 1. Handle relevance sort first
    if params.keyword and params.sort_by == 'relevance':
        if params.search_type == 'full_text':
            # For PGroonga, we order by the calculated score
            order_by_clause = db.desc("score")
        elif params.search_type == 'trigram':
            # For trigram, we order by the calculated similarity score
            order_by_clause = db.desc("similarity")

    # 2. If relevance sort was not applicable, handle other sort options
    if order_by_clause is None:
        if params.sort_by == 'filename':
            order_by_clause = Document.file_name.desc() if params.sort_order == 'desc' else Document.file_name.asc()
        elif params.sort_by == 'mtime':
            order_by_clause = Document.file_modified_time.desc() if params.sort_order == 'desc' else Document.file_modified_time.asc()
        else:
            # 3. Final fallback to default sort order
            order_by_clause = Document.file_modified_time.desc()

    query = query.order_by(order_by_clause)

    # Log the final query for debugging
    try:
        # This is a simplified representation for logging. The actual query sent to the DB might be more complex.
        final_sql = str(query.statement.compile(dialect=db.engine.dialect, compile_kwargs={"literal_binds": True}))
        logger.debug(f"Executing search query: {final_sql}")
    except Exception as e:
        logger.warning(f"Could not compile search query for logging: {e}")


    pagination = query.paginate(page=params.page, per_page=params.per_page, error_out=False)
    
    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"Search completed in {duration:.4f} seconds. Found {pagination.total} results.")
    
    return pagination