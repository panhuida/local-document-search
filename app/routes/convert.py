import os
import json
import sys
import unicodedata

# Defer importing tkinter until needed to avoid import errors on headless servers.
_tk_available = True
tk = None
filedialog = None

def ensure_tk():
    """Attempt to import tkinter on demand. Returns True if available."""
    global _tk_available, tk, filedialog
    if tk is not None and filedialog is not None:
        return _tk_available
    try:
        import tkinter as _tk
        from tkinter import filedialog as _filedialog
        tk = _tk
        filedialog = _filedialog
        _tk_available = True
    except Exception:
        # In headless environments (like many Ubuntu servers) tkinter may not be installed
        _tk_available = False
    return _tk_available
from flask import Blueprint, request, jsonify, current_app, Response
from app.services.ingestion_manager import (
    run_local_ingestion,
    request_cancel_ingestion,
    get_active_session_ids,
    get_session_debug,
    start_async_ingestion,
    stream_async_session,
)
from app.services.converters import convert_to_markdown
from app.models import Document
from app.extensions import db

bp = Blueprint('convert', __name__, url_prefix='/api')

@bp.route('/browse-folder', methods=['GET'])
def browse_folder():
    """
    Opens a dialog for the user to select a folder.
    Returns the selected folder path.
    """
    if not ensure_tk():
        current_app.logger.warning('tkinter is not available in this environment; browse-folder is not supported.')
        return jsonify({'status': 'error', 'message': 'tkinter (GUI) is not available on this server. Use the API with a folder_path parameter instead.'}), 400

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
    async_mode = request.args.get('async', 'true').lower() == 'true'

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

    if async_mode:
        # Start async session and then stream queue
        session_id = start_async_ingestion(folder_path, date_from, date_to, recursive, file_types)
        def async_gen():
            with app.app_context():
                # Emit immediate session_info-like notice so client knows session id quickly
                # Initial session info event
                yield f"data: {json.dumps({'level':'info','message':f'Session started: {session_id}','stage':'session_info','session_id':session_id})}\n\n"
                for evt in stream_async_session(session_id):
                    yield f"data: {json.dumps(evt)}\n\n"
        return Response(async_gen(), mimetype='text/event-stream')
    else:
        def generate_stream(app):
            with app.app_context():
                for progress_update in run_local_ingestion(folder_path, date_from, date_to, recursive, file_types):
                    yield f"data: {json.dumps(progress_update)}\n\n"
        return Response(generate_stream(app), mimetype='text/event-stream')

@bp.route('/convert/stop', methods=['POST'])
def stop_conversion():
    """Request cancellation of an ingestion session.

    Body JSON: {"session_id": "..."} (optional)
    Logic:
      - If session_id provided: cancel that session.
      - If omitted:
          * 0 active -> 400
          * 1 active -> cancel it
          * >1 active -> choose the most recently started (best-effort heuristic via debug info)
    """
    data = request.get_json(silent=True) or {}
    requested_session_id = data.get('session_id')
    try:
        active = get_active_session_ids()
        chosen = requested_session_id
        if not chosen:
            if len(active) == 0:
                return jsonify({'status': 'error', 'message': 'No active sessions.'}), 400
            if len(active) == 1:
                chosen = active[0]
            else:
                # Pick the latest started
                debug_list = [get_session_debug(sid) for sid in active]
                debug_list = [d for d in debug_list if d]
                debug_list.sort(key=lambda d: d.get('started_at') or '', reverse=True)
                chosen = debug_list[0]['session_id'] if debug_list else active[0]
        ok = request_cancel_ingestion(chosen)
        if not ok:
            return jsonify({'status': 'error', 'message': 'Session not found or already ended', 'session_id': chosen}), 404
        current_app.logger.info(f"[CancelAPI] cancellation requested session={chosen} active={active}")
        return jsonify({'status': 'success', 'message': f'Cancellation requested for session {chosen}.', 'session_id': chosen})
    except Exception as e:
        current_app.logger.error(f"Error requesting cancellation: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Failed to request cancellation.'}), 500

@bp.route('/convert/stop-all', methods=['POST'])
def stop_all_conversions():
    """Cancel all active ingestion sessions."""
    try:
        active = get_active_session_ids()
        if not active:
            return jsonify({'status': 'success', 'message': 'No active sessions.'})
        cancelled = []
        for sid in active:
            if request_cancel_ingestion(sid):
                cancelled.append(sid)
        current_app.logger.info(f"[CancelAPI] stop-all requested cancelled={cancelled}")
        return jsonify({'status': 'success', 'message': 'Cancellation requested for all active sessions.', 'sessions': cancelled})
    except Exception as e:
        current_app.logger.error(f"Error in stop-all: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Failed to request stop-all.'}), 500

@bp.route('/convert/sessions', methods=['GET'])
def list_sessions():
    """Return list of active ingestion session IDs for debugging/diagnostics."""
    try:
        return jsonify({'status': 'success', 'sessions': get_active_session_ids()})
    except Exception as e:
        current_app.logger.error(f"Error listing sessions: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to list sessions.'}), 500

@bp.route('/convert/sessions/detail', methods=['GET'])
def list_sessions_detail():
    try:
        details = []
        for sid in get_active_session_ids():
            details.append(get_session_debug(sid))
        return jsonify({'status': 'success', 'sessions': details})
    except Exception as e:
        current_app.logger.error(f"Error listing session details: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to list session details.'}), 500

@bp.route('/convert/sessions/history', methods=['GET'])
def list_sessions_with_history():
    """Return active async sessions with last events for UI reconnection.

    Response:
    {
      status: 'success',
      sessions: [
        { session_id, folder_path, params, done, stop, history: [ {level, message, stage, ...}, ... ] }
      ]
    }
    """
    try:
        sessions_out = []
        sessions = current_app.config.get('INGEST_SESSIONS', {})
        for sid, data in sessions.items():
            if data.get('mode') != 'async':
                continue
            hist = list(data.get('history', []))
            sessions_out.append({
                'session_id': sid,
                'folder_path': data.get('folder_path'),
                'params': data.get('params', {}),
                'done': data.get('done'),
                'stop': data.get('stop'),
                'history': hist
            })
        return jsonify({'status': 'success', 'sessions': sessions_out})
    except Exception as e:
        current_app.logger.error(f"Error listing session history: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Failed to list session history.'}), 500

@bp.route('/convert/batch', methods=['POST'])
def start_batch_ingestion():
    """Start multiple ingestion sessions (one per directory) in parallel.

    Request JSON:
    {
        "directories": ["E:/docs/a", "E:/docs/b"],
        "recursive": true,
        "date_from": "",   # optional
        "date_to": "",     # optional
        "file_types": "pdf,md,txt"  # optional (if omitted front-end should supply default)
    }

    Response:
    {
        "status": "success",
        "batch": [
            {"directory": "E:/docs/a", "stream_url": "/api/convert-stream?...encoded..."},
            {"directory": "E:/docs/b", "stream_url": "/api/convert-stream?..."}
        ]
    }

    Frontend then creates separate EventSource objects for each stream_url.
    """
    try:
        payload = request.get_json(silent=True) or {}
        directories = payload.get('directories') or []
        if not isinstance(directories, list) or not directories:
            return jsonify({'status': 'error', 'message': 'directories must be a non-empty list'}), 400
        recursive = bool(payload.get('recursive', True))
        date_from = payload.get('date_from') or ''
        date_to = payload.get('date_to') or ''
        file_types = payload.get('file_types')  # allow None -> UI fallback

        batch_entries = []
        for raw_dir in directories:
            if not raw_dir or not os.path.isdir(raw_dir):
                batch_entries.append({
                    'directory': raw_dir,
                    'error': 'invalid_directory'
                })
                continue
            # Reuse normalization logic (mirror convert_stream_route)
            abs_path = os.path.abspath(raw_dir)
            dir_norm = unicodedata.normalize('NFC', abs_path).replace('\\', '/')
            from urllib.parse import urlencode, quote
            params = {
                'folder_path': dir_norm,
                'recursive': str(recursive).lower(),
                'date_from': date_from,
                'date_to': date_to,
            }
            if file_types:
                params['file_types'] = file_types
            query = urlencode(params, quote_via=quote)
            batch_entries.append({
                'directory': dir_norm,
                'stream_url': f"/api/convert-stream?{query}"
            })

        return jsonify({'status': 'success', 'batch': batch_entries})
    except Exception as e:
        current_app.logger.error(f"Error starting batch ingestion: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Failed to start batch ingestion'}), 500

@bp.route('/retry-conversion/<int:doc_id>', methods=['POST'])
def retry_conversion(doc_id):
    """Retry conversion using new ConversionResult structure."""
    current_app.logger.info(f"Attempting to retry conversion for document ID: {doc_id}")
    doc = Document.query.get(doc_id)
    if not doc:
        current_app.logger.warning(f"Retry failed: Document with ID {doc_id} not found.")
        return jsonify({'status': 'error', 'message': 'Document not found.'}), 404
    if doc.status != 'failed':
        current_app.logger.warning(f"Retry skipped: Document {doc_id} is not in a failed state (current state: {doc.status}).")
        return jsonify({'status': 'error', 'message': 'Document is not in a failed state.'}), 400
    try:
        current_app.logger.info(f"Retrying conversion for file: {doc.file_path}")
        result = convert_to_markdown(doc.file_path, doc.file_type)
        if not result.success:
            doc.error_message = result.error
            doc.status = 'failed'
            db.session.commit()
            current_app.logger.error(f"Retry failed for document {doc_id}: {result.error}")
            return jsonify({'status': 'error', 'message': f'Retry failed: {result.error}'})
        
        doc.markdown_content = result.content
        doc.conversion_type = result.conversion_type
        doc.status = 'completed'
        doc.error_message = None
        db.session.commit()
        current_app.logger.info(f"Successfully retried and converted document {doc_id}.")
        return jsonify({'status': 'success', 'message': 'Document successfully reconverted.'})
    except Exception as e:
        current_app.logger.error(f"Error retrying conversion for doc {doc_id}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'An internal error occurred during retry.'}), 500

