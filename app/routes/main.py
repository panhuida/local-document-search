from flask import Blueprint, render_template

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/process')
def convert_page():
    return render_template('convert.html')

@bp.route('/search')
def search_page():
    return render_template('search.html')
