import re
import time
from dataclasses import dataclass
from typing import List, Optional, Mapping

from flask import current_app
from local_document_search.models import Document
from local_document_search.extensions import db
from sqlalchemy import func, cast, TEXT, literal_column
import sqlalchemy as sa

ALLOWED_SORT_BY = {"relevance", "filename", "mtime"}
ALLOWED_SORT_ORDER = {"asc", "desc"}
ALLOWED_SEARCH_TYPES = {"full_text", "trigram"}

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
    source: Optional[str] = None
    conversion_types: Optional[List[int]] = None

    def normalized(self, app_config) -> "SearchParams":
        """Return a normalized copy with safe defaults."""
        sort_by = self.sort_by if self.sort_by in ALLOWED_SORT_BY else app_config.get("SEARCH_DEFAULT_SORT_BY", "relevance")
        sort_order = self.sort_order if self.sort_order in ALLOWED_SORT_ORDER else "desc"
        search_type = self.search_type if self.search_type in ALLOWED_SEARCH_TYPES else "full_text"
        page = self.page if isinstance(self.page, int) and self.page > 0 else 1
        per_page_default = app_config.get("SEARCH_DEFAULT_PER_PAGE", 20)
        per_page = self.per_page if isinstance(self.per_page, int) and self.per_page > 0 else per_page_default
        return SearchParams(
            keyword=self.keyword,
            search_type=search_type,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
            file_types=self.file_types,
            date_from=self.date_from,
            date_to=self.date_to,
            source=self.source,
            conversion_types=self.conversion_types,
        )


def build_search_params(args: Mapping, app_config) -> SearchParams:
    """Parse and normalize request args into SearchParams."""
    keyword = args.get("keyword")
    sort_by = args.get("sort_by", app_config.get("SEARCH_DEFAULT_SORT_BY", "relevance"))
    sort_order = str(args.get("sort_order", "desc")).lower()
    search_type = args.get("search_type", "full_text")
    try:
        page = int(args.get("page", 1))
    except Exception:
        page = 1
    try:
        per_page = int(args.get("per_page", app_config.get("SEARCH_DEFAULT_PER_PAGE", 20)))
    except Exception:
        per_page = app_config.get("SEARCH_DEFAULT_PER_PAGE", 20)

    file_types_raw = args.get("file_types")
    file_types = None
    if file_types_raw:
        file_types = [ft.strip().lower() for ft in str(file_types_raw).split(",") if ft.strip()]

    conv_types_raw = args.get("conversion_types")
    conversion_types = None
    if conv_types_raw:
        try:
            conversion_types = [int(x) for x in str(conv_types_raw).split(",") if str(x).strip().isdigit()]
        except Exception:
            conversion_types = None

    params = SearchParams(
        keyword=keyword,
        search_type=search_type,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
        file_types=file_types,
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
        source=args.get("source"),
        conversion_types=conversion_types,
    )
    return params.normalized(app_config)

def search_documents(params: SearchParams):
    """搜索文档"""
    logger = current_app.logger
    start_time = time.time()

    # Start query by filtering for completed documents only
    query = Document.query.filter(Document.status == 'completed')

    if params.file_types:
        query = query.filter(Document.file_type.in_(params.file_types))

    if params.conversion_types:
        query = query.filter(Document.conversion_type.in_(params.conversion_types))

    if params.date_from:
        query = query.filter(Document.file_modified_time >= params.date_from)
    if params.date_to:
        query = query.filter(Document.file_modified_time <= params.date_to)

    if params.source:
        query = query.filter(Document.source == params.source)

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


def fetch_failed_documents(file_name: Optional[str], date_from: Optional[str], date_to: Optional[str]):
    """Encapsulate failed document query logic for reuse."""
    query = Document.query.filter_by(status='failed')
    if file_name:
        query = query.filter(Document.file_name.ilike(f'%{file_name}%'))
    if date_from:
        query = query.filter(Document.updated_at >= date_from)
    if date_to:
        query = query.filter(Document.updated_at <= date_to)
    return query.order_by(Document.updated_at.desc())
