from flask import Blueprint, render_template
from app.models import ConversionError

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('search.html')

@bp.route('/process')
def convert_page():
    return render_template('convert.html')

@bp.route('/search')
def search_page():
    return render_template('search.html')

@bp.route('/errors')
def errors_page():
    errors = ConversionError.query.order_by(ConversionError.created_at.desc()).all()
    return render_template('errors.html', errors=errors)