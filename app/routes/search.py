import os
import sys
import subprocess
import time
import re
from flask import Blueprint, request, jsonify, current_app
from app.services.search_service import search_documents, SearchParams
from markdown_it import MarkdownIt
from app.extensions import db

bp = Blueprint('search', __name__, url_prefix='/api')

def highlight_text(text, keyword):
    if not text or not keyword:
        return text

    try:
        keywords = re.split(r'[\s+]+', keyword)
        keywords = [k for k in keywords if k]

        if not keywords:
            return text

        highlighted_text = text
        for kw in keywords:
            highlighted_text = re.sub(f'({re.escape(kw)})', r'<mark>\1</mark>', highlighted_text, flags=re.IGNORECASE)
        
        return highlighted_text
    except Exception:
        return text

def create_highlighted_snippet(content, keyword, length=200):
    if not content or not keyword:
        return (content or '')[:length]

    try:
        # Split keyword into individual words
        keywords = re.split(r'[\s+]+', keyword)
        keywords = [k for k in keywords if k] # remove empty strings

        if not keywords:
            return (content or '')[:length]

        # Find the first match to center the snippet
        first_match = None
        for kw in keywords:
            match = re.search(kw, content, re.IGNORECASE)
            if match:
                first_match = match
                break
        
        if not first_match:
            # If no match in content, just return the beginning of the content
            snippet = (content or '')[:length]
            if len(content) > length:
                snippet += '...'
            return snippet

        start_pos = first_match.start()
        
        # Calculate snippet start and end
        snippet_start = max(0, start_pos - length // 2)
        snippet_end = min(len(content), start_pos + len(keywords[0]) + length // 2)

        if snippet_start == 0:
            snippet_end = min(len(content), length)
        if snippet_end == len(content):
            snippet_start = max(0, len(content) - length)

        snippet = content[snippet_start:snippet_end]

        if snippet_start > 0:
            snippet = "..." + snippet
        if snippet_end < len(content):
            snippet = snippet + "..."

        # Highlight all keywords
        return highlight_text(snippet, keyword)

    except Exception:
        return (content or '')[:length] # Fallback


@bp.route('/search', methods=['GET'])
def search_route():
    logger = current_app.logger
    start_time = time.time()
    
    try:
        keyword = request.args.get('keyword')
        sort_by = request.args.get('sort_by', current_app.config['SEARCH_DEFAULT_SORT_BY'])
        search_type = request.args.get('search_type', 'full_text')
        sort_order = request.args.get('sort_order', 'desc')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', current_app.config['SEARCH_DEFAULT_PER_PAGE'], type=int)
        file_types = request.args.get('file_types')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        source = request.args.get('source')

        logger.info(
            f"Search request received. Keyword: '{keyword}', Type: '{search_type}', "
            f"Sort: '{sort_by}'/'{sort_order}', Page: {page}, PerPage: {per_page}, "
            f"FileTypes: '{file_types}', DateFrom: '{date_from}', DateTo: '{date_to}', "
            f"Source: '{source}'"
        )

        if file_types:
            file_types = file_types.split(',')

        search_params = SearchParams(
            keyword=keyword,
            search_type=search_type,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
            file_types=file_types,
            date_from=date_from,
            date_to=date_to,
            source=source
        )

        pagination = search_documents(params=search_params)
        end_time = time.time()
        search_time = f'{end_time - start_time:.2f}s'

        results = []
        for item in pagination.items:
            # Unpack the document and score if the search returns scores
            if (search_type == 'full_text' or search_type == 'trigram') and keyword:
                doc, score = item
            else:
                doc, score = item, None

            snippet = create_highlighted_snippet(doc.markdown_content, keyword)
            highlighted_filename = highlight_text(doc.file_name, keyword)
            result_item = {
                'id': doc.id,
                'filename': highlighted_filename,
                'filepath': doc.file_path,
                'filetype': doc.file_type,
                'filesize': doc.file_size,
                'file_modified_time': doc.file_modified_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'snippet': snippet,
                'source': doc.source,
                'source_url': doc.source_url
            }
            if score is not None:
                result_item['relevance'] = round(score, 3)
            results.append(result_item)

        return jsonify({
            'status': 'success',
            'data': {
                'search_info': {
                    'keyword': keyword,
                    'search_type': search_type,
                    'sort_by': sort_by,
                    'total_results': pagination.total,
                    'search_time': search_time
                },
                'results': results,
                'pagination': {
                    'page': pagination.page,
                    'per_page': pagination.per_page,
                    'total_pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            }
        })
    except Exception as e:
        logger.error("An error occurred during search.", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'An error occurred during the search. Please check the logs for details.'
        }), 500

@bp.route('/config/file-types', methods=['GET'])
def get_file_types_config():
    from flask import current_app
    
    # A helper to create the list for a given category
    def create_type_list(category_name):
        config_key = f'{category_name.upper()}_TYPES'
        types = current_app.config.get(config_key, [])
        
        # Use the description from the central FILE_TYPE_CONFIG
        return [{
            'ext': ext, 
            'name': current_app.config['FILE_TYPE_CONFIG'].get(ext, {}).get('description', ext.upper()),
        } for ext in types]

    return jsonify({
        'status': 'success',
        'data': {
            'native_markdown_types': create_type_list('NATIVE_MARKDOWN'),
            'plain_text_to_markdown_types': create_type_list('PLAIN_TEXT_TO_MARKDOWN'),
            'code_to_markdown_types': create_type_list('CODE_TO_MARKDOWN'),
            'xmind_to_markdown_types': create_type_list('XMIND_TO_MARKDOWN'),
            'structured_to_markdown_types': create_type_list('STRUCTURED_TO_MARKDOWN'),
            'image_to_markdown_types': create_type_list('IMAGE_TO_MARKDOWN'),
            'conversion_info': {
                'target_format': 'Markdown',
                'ai_agent_ready': True,
                'unified_search': True
            }
        }
    })

@bp.route('/preview/markdown/<int:document_id>', methods=['GET'])
def get_markdown_preview(document_id):
    from app.models import Document
    doc = Document.query.get_or_404(document_id)
    
    # 使用 markdown-it-py 进行渲染，支持 GFM (GitHub Flavored Markdown)
    md = MarkdownIt("gfm-like")
    rendered_html = md.render(doc.markdown_content or '')

    return jsonify({
        'status': 'success',
        'data': {
            'id': doc.id,
            'file_name': doc.file_name,
            'file_type': doc.file_type,
            'file_size': doc.file_size,
            'file_modified_time': doc.file_modified_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'markdown_content': doc.markdown_content,
            'rendered_html': rendered_html
        }
    })

@bp.route('/open-file')
def open_file():
    path = request.args.get('path')
    if not path or not os.path.exists(path):
        return jsonify({'status': 'error', 'message': 'File not found or path is invalid'}), 404

    try:
        if sys.platform == "win32":
            os.startfile(os.path.realpath(path))
        elif sys.platform == "darwin":
            subprocess.run(['open', path], check=True)
        else:
            subprocess.run(['xdg-open', path], check=True)
        return jsonify({'status': 'success', 'message': 'Request to open file sent.'})
    except Exception as e:
        current_app.logger.error(f"Failed to open file {path}: {e}")
        return jsonify({'status': 'error', 'message': f'Failed to open file: {e}'}), 500

@bp.route('/sources', methods=['GET'])
def get_sources():
    from app.models import Document
    try:
        sources = db.session.query(Document.source).distinct().all()
        source_list = [source[0] for source in sources if source[0]]
        return jsonify({
            'status': 'success',
            'data': source_list
        })
    except Exception as e:
        current_app.logger.error("An error occurred while fetching sources.", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'An error occurred while fetching sources.'
        }), 500
