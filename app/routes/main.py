from flask import Blueprint, render_template, request, current_app
from app.models import Document

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('search.html')

@bp.route('/process')
def convert_page():
    # This route is now handled by the 'convert' blueprint.
    # This is kept for backward compatibility of bookmarks, but should be removed later.
    return render_template('convert.html')

@bp.route('/search')
def search_page():
    return render_template('search.html')

@bp.route('/errors')
def errors_page():
    try:
        # Query for documents with a 'failed' status
        query = Document.query.filter_by(status='failed')

        # Search by filename
        file_name_search = request.args.get('file_name', '')
        if file_name_search:
            query = query.filter(Document.file_name.ilike(f'%{file_name_search}%'))

        # Filter by date
        date_from = request.args.get('date_from', '')
        if date_from:
            query = query.filter(Document.updated_at >= date_from)
        
        date_to = request.args.get('date_to', '')
        if date_to:
            query = query.filter(Document.updated_at <= date_to)

        # Sort by updated_at
        query = query.order_by(Document.updated_at.desc())

        errors = query.all()

        return render_template('errors.html', errors=errors, file_name_search=file_name_search, date_from=date_from, date_to=date_to)
    except Exception as e:
        current_app.logger.error(f"Error loading errors page: {e}", exc_info=True)
        return render_template('errors.html', errors=[], error_message="Could not load error data.")