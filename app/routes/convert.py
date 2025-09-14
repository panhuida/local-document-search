import os
import json
import tkinter as tk
import unicodedata
from tkinter import filedialog
from flask import Blueprint, request, jsonify, current_app, Response
from app.services.ingest import ingest_folder
from app.models import Document
from app.extensions import db

bp = Blueprint('convert', __name__, url_prefix='/api')

@bp.route('/browse-folder', methods=['GET'])
def browse_folder():
    """
    Opens a dialog for the user to select a folder.
    Returns the selected folder path.
    """
    try:
        root = tk.Tk()
        root.withdraw()  # Hide the main tkinter window
        root.attributes('-topmost', True)
        folder_path = filedialog.askdirectory(master=root)
        return jsonify({'status': 'success', 'folder_path': folder_path})
    except Exception as e:
        current_app.logger.error(f"Error opening folder dialog: {e}")
        return jsonify({'status': 'error', 'message': 'Could not open folder dialog.'}), 500

@bp.route('/convert-stream')
def convert_stream_route():
    folder_path = request.args.get('folder_path')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    recursive = request.args.get('recursive', 'true').lower() == 'true'
    file_types = request.args.get('file_types')

    # --- Path Normalization ---
    if folder_path:
        # 1. Normalize to OS-native format (e.g., C:\Users...\ on Windows)
        # 2. Get absolute path to resolve any relative parts and get correct casing
        abs_path = os.path.abspath(folder_path)
        # 3. Normalize unicode representation
        nfc_path = unicodedata.normalize('NFC', abs_path)
        # 4. For consistency in logs and DB, convert to forward slashes
        folder_path = nfc_path.replace('\\', '/')

    current_app.logger.info(
        f"Starting conversion stream with parameters: folder_path='{folder_path}', "
        f"date_from='{date_from}', date_to='{date_to}', recursive={recursive}, file_types='{file_types}'"
    )

    if not folder_path or not os.path.isdir(folder_path):
        def error_stream():
            error_data = {'level': 'critical', 'message': 'Invalid or missing folder path.', 'stage': 'critical_error'}
            yield f"data: {json.dumps(error_data)}\n\n"
        return Response(error_stream(), mimetype='text/event-stream')
    
    app = current_app._get_current_object()
    def generate_stream(app):
        with app.app_context():
            for progress_update in ingest_folder(folder_path, date_from, date_to, recursive, file_types):
                yield f"data: {json.dumps(progress_update)}\n\n"

    return Response(generate_stream(app), mimetype='text/event-stream')

@bp.route('/retry-conversion/<int:doc_id>', methods=['POST'])
def retry_conversion(doc_id):
    """
    Retries the conversion for a document that previously failed.
    """
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({'status': 'error', 'message': 'Document not found.'}), 404

    if doc.status != 'failed':
        return jsonify({'status': 'error', 'message': 'Document is not in a failed state.'}), 400

    try:
        from app.services.ingest import _convert_to_markdown
        
        content, conversion_type = _convert_to_markdown(doc.file_path, doc.file_type)

        if conversion_type is None: # Conversion failed again
            doc.error_message = content # content is the error message
            db.session.commit()
            return jsonify({'status': 'error', 'message': f'Retry failed: {content}'})
        
        # Conversion succeeded
        doc.markdown_content = content
        doc.conversion_type = conversion_type
        doc.status = 'completed'
        doc.error_message = None
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Document successfully reconverted.'})

    except Exception as e:
        current_app.logger.error(f"Error retrying conversion for doc {doc_id}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'An internal error occurred during retry.'}), 500

