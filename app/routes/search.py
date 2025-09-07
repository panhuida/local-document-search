import os
import sys
import subprocess
import time
from flask import Blueprint, request, jsonify, current_app
from app.services.search_service import search_documents
import markdown

bp = Blueprint('search', __name__, url_prefix='/api')

@bp.route('/search', methods=['GET'])
def search_route():
    logger = current_app.logger
    start_time = time.time()
    keyword = request.args.get('keyword')
    logger.info(f"Received search query with keyword: '{keyword}'")
    search_type = request.args.get('search_type', 'simple')
    sort_by = request.args.get('sort_by', 'relevance')
    sort_order = request.args.get('sort_order', 'desc')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    file_types = request.args.get('file_types')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if file_types:
        file_types = file_types.split(',')

    pagination = search_documents(keyword, search_type, sort_by, sort_order, page, per_page, file_types, date_from, date_to)
    end_time = time.time()
    search_time = f'{end_time - start_time:.2f}s'

    results = []
    for doc in pagination.items:
        results.append({
            'id': doc.id,
            'filename': doc.file_name,
            'filepath': doc.file_path,
            'filetype': doc.file_type,
            'filesize': doc.file_size,
            'file_modified_time': doc.file_modified_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'snippet': doc.markdown_content[:200] + '...' if doc.markdown_content else '' # Simple snippet
        })

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

@bp.route('/config/file-types', methods=['GET'])
def get_file_types_config():
    from flask import current_app
    return jsonify({
        'status': 'success',
        'data': {
            'native_markdown_types': [{'ext': ext, 'name': f'{ext.upper()} file', 'process': 'Direct Storage'} for ext in current_app.config.get('NATIVE_MARKDOWN_TYPES', [])],
            'code_to_markdown_types': [{'ext': ext, 'name': f'{ext.upper()} file', 'process': 'Convert to Code Block'} for ext in current_app.config.get('CODE_TO_MARKDOWN_TYPES', [])],
            'structured_to_markdown_types': [{'ext': ext, 'name': f'{ext.upper()} file', 'process': 'markitdown conversion'} for ext in current_app.config.get('STRUCTURED_TO_MARKDOWN_TYPES', [])],
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
    rendered_html = markdown.markdown(doc.markdown_content)
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