from flask import Blueprint, render_template, request, current_app
from local_document_search.services.search_service import fetch_failed_documents

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('search.html')

@bp.route('/process')
def convert_page():
    # Backward compatibility; real logic in convert blueprint.
    return render_template('convert.html', page_title="文档导入")

@bp.route('/search')
def search_page():
    return render_template('search.html')

@bp.route('/errors')
def errors_page():
    try:
        file_name_search = request.args.get('file_name', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')

        errors = fetch_failed_documents(file_name_search, date_from, date_to).all()

        return render_template('errors.html', errors=errors, file_name_search=file_name_search, date_from=date_from, date_to=date_to)
    except Exception as e:
        current_app.logger.error(f"Error loading errors page: {e}", exc_info=True)
        return render_template('errors.html', errors=[], error_message="Could not load error data.")
