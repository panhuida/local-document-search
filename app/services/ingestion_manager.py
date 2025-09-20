"""Ingestion manager: manages folder ingestion sessions with cancellation support.

This is a clean reimplementation after corruption. Key features:
 - Session storage in `app.config['INGEST_SESSIONS']` (survives dev server reload).
 - Every emitted event includes `session_id`.
 - Control-plane events (e.g. CANCEL_ACK) queued so they are flushed ASAP.
 - Heartbeat / debug events to help diagnose cancellation timing.
"""

import os
import json
import uuid
import traceback
import threading
import time
from collections import deque
from datetime import datetime, timezone
from flask import current_app

from app.extensions import db
from app.models import Document, IngestState
from app.utils.file_utils import get_file_metadata
from app.services.filesystem_scanner import find_files
from app.services.converters import convert_to_markdown
from app.services.conversion_result import ConversionResult
from app.services.log_events import LogEvent


# ---------------- Session Store Helpers ---------------- #
def _get_sessions():
    cfg = current_app.config
    if 'INGEST_SESSIONS' not in cfg:
        cfg['INGEST_SESSIONS'] = {}
    return cfg['INGEST_SESSIONS']


def start_session() -> str:
    sid = uuid.uuid4().hex
    sessions = _get_sessions()
    sessions[sid] = {
        'stop': False,
        'started_at': datetime.now(timezone.utc),
        'control_events': [],  # control-plane queue (CANCEL_ACK etc)
        'event_queue': deque(),  # for async/background mode
        'done': False,
        'mode': 'sync',  # or 'async'
        'folder_path': None,
        'params': {},
        'history': deque(maxlen=1000)  # recent events for reconnection
    }
    return sid


def request_cancel_ingestion(session_id: str) -> bool:
    sessions = _get_sessions()
    if session_id in sessions:
        sess = sessions[session_id]
        if not sess.get('stop'):
            sess['stop'] = True
            sess['cancel_requested_at'] = datetime.now(timezone.utc)
            sess.setdefault('control_events', []).append({
                'level': 'warning',
                'message': '取消请求已收到 (cancel acknowledged).',
                'stage': LogEvent.CANCEL_ACK.value,
                'session_id': session_id
            })
        try:
            current_app.logger.info(f"[Cancel] request received session={session_id}")
        except Exception:
            pass
        return True
    try:
        current_app.logger.warning(f"[Cancel] request for unknown session={session_id}")
    except Exception:
        pass
    return False


def is_cancelled(session_id: str) -> bool:
    sessions = _get_sessions()
    data = sessions.get(session_id)
    return bool(data and data.get('stop'))


def end_session(session_id: str):
    sessions = _get_sessions()
    sessions.pop(session_id, None)


def get_active_session_ids():
    return list(_get_sessions().keys())


def get_session_debug(session_id: str):
    data = _get_sessions().get(session_id)
    if not data:
        return None
    return {
        'session_id': session_id,
        'stop': data.get('stop'),
        'started_at': data.get('started_at').isoformat() if data.get('started_at') else None,
        'cancel_requested_at': data.get('cancel_requested_at').isoformat() if data.get('cancel_requested_at') else None,
        'control_queue_length': len(data.get('control_events', [])),
        'event_queue_length': len(data.get('event_queue', [])),
        'done': data.get('done'),
        'mode': data.get('mode'),
        'folder_path': data.get('folder_path'),
        'params': data.get('params', {})
    }


# ---------------- Ingestion Core ---------------- #
def run_local_ingestion(folder_path, date_from_str, date_to_str, recursive, file_types_str):
    """Generator yielding structured SSE dicts for ingestion progress."""
    logger = current_app.logger
    start_time = datetime.now(timezone.utc)
    session_id = start_session()

    # IngestState fetch / create
    ingest_state = db.session.query(IngestState).filter_by(
        source=current_app.config['SOURCE_LOCAL_FS'], scope_key=folder_path).first()
    if not ingest_state:
        ingest_state = IngestState(source=current_app.config['SOURCE_LOCAL_FS'], scope_key=folder_path)
        db.session.add(ingest_state)
    ingest_state.last_started_at = start_time
    ingest_state.last_error_message = None
    db.session.commit()

    effective_date_from = date_from_str
    if not date_from_str and ingest_state.cursor_updated_at:
        effective_date_from = ingest_state.cursor_updated_at.isoformat()

    processed_files = skipped_files = error_files = 0

    try:
        # Session + scan start events
        yield {'level': 'info', 'message': f'Starting folder scan: {folder_path}', 'stage': LogEvent.SCAN_START.value, 'session_id': session_id}
        yield {'level': 'info', 'message': f'Session started: {session_id}', 'stage': 'session_info', 'session_id': session_id}

        matched_files = find_files(folder_path, recursive, file_types_str, effective_date_from, date_to_str)
        total_files = len(matched_files)
        ingest_state.total_files = total_files
        db.session.commit()
        yield {'level': 'info', 'message': f'Scan found {total_files} matching files.', 'stage': LogEvent.SCAN_COMPLETE.value, 'total_files': total_files, 'session_id': session_id}

        if total_files == 0:
            summary = {'total_files': 0, 'processed_files': 0, 'skipped_files': 0, 'error_files': 0}
            yield {'level': 'info', 'message': 'No files to process.', 'stage': LogEvent.DONE.value, 'summary': summary, 'session_id': session_id}
            ingest_state.cursor_updated_at = start_time
            return

        sessions = _get_sessions()
        for i, file_path in enumerate(matched_files):
            # Drain control events
            ctrl_events = sessions.get(session_id, {}).get('control_events', [])
            while ctrl_events:
                evt = ctrl_events.pop(0)
                logger.info(f"[IngestionControl] emit {evt['stage']} session={session_id}")
                yield evt
            # Heartbeat with richer diagnostic information
            active_ids = list(sessions.keys())
            yield {
                'level': 'info',
                'message': (
                    f"Heartbeat: i={i} stop={sessions.get(session_id, {}).get('stop')} "
                    f"queue={len(sessions.get(session_id, {}).get('control_events', []))} "
                    f"active_sessions={active_ids}"
                ),
                'stage': 'debug_state',
                'session_id': session_id
            }
            if is_cancelled(session_id):
                yield {'level': 'warning', 'message': 'Stopping before next file (cancelled).', 'stage': LogEvent.CANCELLED.value, 'session_id': session_id}
                break

            progress = int(((i + 1) / total_files) * 100)
            metadata = get_file_metadata(file_path)
            if not metadata:
                skipped_files += 1
                logger.warning(f"[Ingestion][{session_id}] SKIP (metadata unavailable) {file_path}")
                yield {'level': 'warning', 'message': f'Could not get metadata for {file_path}, skipping.', 'stage': LogEvent.FILE_SKIP.value, 'session_id': session_id}
                continue

            # Console log for visibility across pages
            logger.info(f"[Ingestion][{session_id}] PROCESS {i+1}/{total_files} :: {metadata['file_name']}")
            yield {'level': 'info', 'message': f"Processing file {i+1}/{total_files}: {metadata['file_name']}", 'stage': LogEvent.FILE_PROCESSING.value, 'progress': progress, 'current_file': metadata['file_name'], 'session_id': session_id}

            # Sidecar metadata (.meta.json)
            source_url = None
            try:
                meta_path = file_path + '.meta.json'
                if os.path.exists(meta_path):
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        mdata = json.load(f)
                        source_url = mdata.get('source_url')
            except Exception as e:
                logger.warning(f"Could not read metadata for {file_path}: {e}")

            # Determine source based on DOWNLOAD_PATH
            source = current_app.config['SOURCE_LOCAL_FS']
            download_path = current_app.config.get('DOWNLOAD_PATH')
            if download_path:
                try:
                    norm_download = os.path.normpath(download_path)
                    norm_file = os.path.normpath(file_path)
                    if norm_file.startswith(norm_download + os.sep):
                        rel = os.path.relpath(norm_file, norm_download)
                        parts = rel.split(os.sep)
                        if len(parts) > 1:
                            source = f"公众号_{parts[0]}"
                except Exception as e:
                    logger.warning(f"Could not derive source from DOWNLOAD_PATH for {file_path}: {e}")

            existing_doc = Document.query.filter(Document.file_path.ilike(metadata['file_path'])).first()
            if existing_doc and existing_doc.file_modified_time == metadata['file_modified_time']:
                skipped_files += 1
                logger.info(f"[Ingestion][{session_id}] SKIP (unchanged) {file_path}")
                yield {'level': 'info', 'message': f'Skipping unchanged file: {file_path}', 'stage': LogEvent.FILE_SKIP.value, 'reason': 'unchanged', 'session_id': session_id}
                continue

            result: ConversionResult = convert_to_markdown(file_path, metadata['file_type'])
            if not result.success:
                error_files += 1
                if existing_doc:
                    existing_doc.status = 'failed'
                    existing_doc.error_message = result.error
                    existing_doc.source = source
                    existing_doc.source_url = source_url
                else:
                    db.session.add(Document(
                        file_name=metadata['file_name'], file_type=metadata['file_type'],
                        file_size=metadata['file_size'], file_created_at=metadata['file_created_at'],
                        file_modified_time=metadata['file_modified_time'], file_path=metadata['file_path'],
                        status='failed', error_message=result.error, source=source, source_url=source_url
                    ))
                logger.error(f"[Ingestion][{session_id}] ERROR converting: {file_path} :: {result.error}")
                yield {'level': 'error', 'message': f'Failed to convert file: {file_path}. Reason: {result.error}', 'stage': LogEvent.FILE_ERROR.value, 'session_id': session_id}
            else:
                if existing_doc:
                    existing_doc.file_size = metadata['file_size']
                    existing_doc.file_modified_time = metadata['file_modified_time']
                    existing_doc.markdown_content = result.content
                    existing_doc.conversion_type = result.conversion_type
                    existing_doc.status = 'completed'
                    existing_doc.error_message = None
                    existing_doc.source = source
                    existing_doc.source_url = source_url
                else:
                    db.session.add(Document(
                        file_name=metadata['file_name'], file_type=metadata['file_type'],
                        file_size=metadata['file_size'], file_created_at=metadata['file_created_at'],
                        file_modified_time=metadata['file_modified_time'], file_path=metadata['file_path'],
                        markdown_content=result.content, conversion_type=result.conversion_type, status='completed',
                        source=source, source_url=source_url
                    ))
                processed_files += 1
                logger.info(f"[Ingestion][{session_id}] SUCCESS {file_path}")
                yield {'level': 'info', 'message': f'Successfully processed: {file_path}', 'stage': LogEvent.FILE_SUCCESS.value, 'session_id': session_id}

            db.session.commit()

            if is_cancelled(session_id):
                # Drain any leftover control events
                ctrl_events2 = sessions.get(session_id, {}).get('control_events', [])
                while ctrl_events2:
                    evt = ctrl_events2.pop(0)
                    logger.info(f"[IngestionControl] emit-post-file {evt['stage']} session={session_id}")
                    yield evt
                yield {'level': 'warning', 'message': '当前文件完成后停止 (stopped after current file).', 'stage': LogEvent.CANCELLED.value, 'session_id': session_id}
                break

        if not is_cancelled(session_id):
            ingest_state.cursor_updated_at = start_time
            summary = {'total_files': total_files, 'processed_files': processed_files, 'skipped_files': skipped_files, 'error_files': error_files}
            yield {'level': 'info', 'message': 'All files processed.', 'stage': LogEvent.DONE.value, 'summary': summary, 'session_id': session_id}
        else:
            summary = {'total_files': total_files, 'processed_files': processed_files, 'skipped_files': skipped_files, 'error_files': error_files}
            yield {'level': 'warning', 'message': 'Processing stopped before completion.', 'stage': LogEvent.DONE.value, 'summary': summary, 'session_id': session_id}

    except Exception as e:
        error_msg = f"A critical error occurred: {e}\n{traceback.format_exc()}"
        logger.critical(error_msg)
        ingest_state.last_error_message = error_msg
        db.session.commit()
        yield {'level': 'critical', 'message': f'A critical error occurred: {str(e)}', 'stage': LogEvent.CRITICAL_ERROR.value, 'session_id': session_id}
    finally:
        ingest_state.processed = processed_files
        ingest_state.skipped = skipped_files
        ingest_state.errors = error_files
        ingest_state.last_ended_at = datetime.now(timezone.utc)
        db.session.commit()
        end_session(session_id)


# ---------------- Asynchronous Ingestion (Background Thread) ---------------- #
def _enqueue(session_id: str, event: dict):
    sessions = _get_sessions()
    sess = sessions.get(session_id)
    if not sess:
        return
    # ensure session_id present
    event.setdefault('session_id', session_id)
    # push into queue
    q = sess.setdefault('event_queue', deque())
    q.append(event)
    # also store in history (skip verbose debug_state to save space)
    if event.get('stage') != 'debug_state':
        hist = sess.setdefault('history', deque(maxlen=1000))
        hist.append(event)


def start_async_ingestion(folder_path, date_from_str, date_to_str, recursive, file_types_str):
    """Start ingestion in a background thread; returns session_id immediately.

    SSE clients can then poll events via poll_async_session(session_id) generator.
    """
    logger = current_app.logger
    session_id = start_session()
    sessions = _get_sessions()
    sessions[session_id]['mode'] = 'async'
    sessions[session_id]['folder_path'] = folder_path
    sessions[session_id]['params'] = {
        'date_from': date_from_str,
        'date_to': date_to_str,
        'recursive': recursive,
        'file_types': file_types_str
    }

    app = current_app._get_current_object()

    def worker():
        with app.app_context():
            start_time = datetime.now(timezone.utc)
            ingest_state = db.session.query(IngestState).filter_by(
                source=current_app.config['SOURCE_LOCAL_FS'], scope_key=folder_path).first()
            if not ingest_state:
                ingest_state = IngestState(source=current_app.config['SOURCE_LOCAL_FS'], scope_key=folder_path)
                db.session.add(ingest_state)
            ingest_state.last_started_at = start_time
            ingest_state.last_error_message = None
            db.session.commit()

            effective_date_from = date_from_str
            if not date_from_str and ingest_state.cursor_updated_at:
                effective_date_from = ingest_state.cursor_updated_at.isoformat()

            processed_files = skipped_files = error_files = 0
            try:
                _enqueue(session_id, {'level': 'info', 'message': f'Starting folder scan: {folder_path}', 'stage': LogEvent.SCAN_START.value})
                _enqueue(session_id, {'level': 'info', 'message': f'Session started: {session_id}', 'stage': 'session_info'})

                matched_files = find_files(folder_path, recursive, file_types_str, effective_date_from, date_to_str)
                total_files = len(matched_files)
                ingest_state.total_files = total_files
                db.session.commit()
                _enqueue(session_id, {'level': 'info', 'message': f'Scan found {total_files} matching files.', 'stage': LogEvent.SCAN_COMPLETE.value, 'total_files': total_files})

                if total_files == 0:
                    summary = {'total_files': 0, 'processed_files': 0, 'skipped_files': 0, 'error_files': 0}
                    ingest_state.cursor_updated_at = start_time
                    db.session.commit()
                    _enqueue(session_id, {'level': 'info', 'message': 'No files to process.', 'stage': LogEvent.DONE.value, 'summary': summary})
                    return

                for i, file_path in enumerate(matched_files):
                    if is_cancelled(session_id):
                        _enqueue(session_id, {'level': 'warning', 'message': 'Stopping before next file (cancelled).', 'stage': LogEvent.CANCELLED.value})
                        break
                    # Drain control events
                    ctrl_events = sessions.get(session_id, {}).get('control_events', [])
                    while ctrl_events:
                        _enqueue(session_id, ctrl_events.pop(0))

                    qlen = len(sessions.get(session_id, {}).get('control_events', []))
                    _enqueue(session_id, {
                        'level': 'info',
                        'message': f"Heartbeat: i={i} stop={is_cancelled(session_id)} queue={qlen}",
                        'stage': 'debug_state'
                    })

                    progress = int(((i + 1) / total_files) * 100)
                    metadata = get_file_metadata(file_path)
                    if not metadata:
                        skipped_files += 1
                        logger.warning(f"[Ingestion][{session_id}] SKIP (metadata unavailable) {file_path}")
                        _enqueue(session_id, {'level': 'warning', 'message': f'Could not get metadata for {file_path}, skipping.', 'stage': LogEvent.FILE_SKIP.value})
                        continue

                    logger.info(f"[Ingestion][{session_id}] PROCESS {i+1}/{total_files} :: {metadata['file_name']}")
                    _enqueue(session_id, {'level': 'info', 'message': f"Processing file {i+1}/{total_files}: {metadata['file_name']}", 'stage': LogEvent.FILE_PROCESSING.value, 'progress': progress, 'current_file': metadata['file_name']})

                    # Sidecar metadata
                    source_url = None
                    try:
                        meta_path = file_path + '.meta.json'
                        if os.path.exists(meta_path):
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                mdata = json.load(f)
                                source_url = mdata.get('source_url')
                    except Exception as e:
                        logger.warning(f"Could not read metadata for {file_path}: {e}")

                    source = current_app.config['SOURCE_LOCAL_FS']
                    download_path = current_app.config.get('DOWNLOAD_PATH')
                    if download_path:
                        try:
                            norm_download = os.path.normpath(download_path)
                            norm_file = os.path.normpath(file_path)
                            if norm_file.startswith(norm_download + os.sep):
                                rel = os.path.relpath(norm_file, norm_download)
                                parts = rel.split(os.sep)
                                if len(parts) > 1:
                                    source = f"公众号_{parts[0]}"
                        except Exception as e:
                            logger.warning(f"Could not derive source from DOWNLOAD_PATH for {file_path}: {e}")

                    existing_doc = Document.query.filter(Document.file_path.ilike(metadata['file_path'])).first()
                    if existing_doc and existing_doc.file_modified_time == metadata['file_modified_time']:
                        skipped_files += 1
                        logger.info(f"[Ingestion][{session_id}] SKIP (unchanged) {file_path}")
                        _enqueue(session_id, {'level': 'info', 'message': f'Skipping unchanged file: {file_path}', 'stage': LogEvent.FILE_SKIP.value, 'reason': 'unchanged'})
                        continue

                    result: ConversionResult = convert_to_markdown(file_path, metadata['file_type'])
                    if not result.success:
                        error_files += 1
                        if existing_doc:
                            existing_doc.status = 'failed'
                            existing_doc.error_message = result.error
                            existing_doc.source = source
                            existing_doc.source_url = source_url
                        else:
                            db.session.add(Document(
                                file_name=metadata['file_name'], file_type=metadata['file_type'],
                                file_size=metadata['file_size'], file_created_at=metadata['file_created_at'],
                                file_modified_time=metadata['file_modified_time'], file_path=metadata['file_path'],
                                status='failed', error_message=result.error, source=source, source_url=source_url
                            ))
                        logger.error(f"[Ingestion][{session_id}] ERROR converting: {file_path} :: {result.error}")
                        _enqueue(session_id, {'level': 'error', 'message': f'Failed to convert file: {file_path}. Reason: {result.error}', 'stage': LogEvent.FILE_ERROR.value})
                    else:
                        if existing_doc:
                            existing_doc.file_size = metadata['file_size']
                            existing_doc.file_modified_time = metadata['file_modified_time']
                            existing_doc.markdown_content = result.content
                            existing_doc.conversion_type = result.conversion_type
                            existing_doc.status = 'completed'
                            existing_doc.error_message = None
                            existing_doc.source = source
                            existing_doc.source_url = source_url
                        else:
                            db.session.add(Document(
                                file_name=metadata['file_name'], file_type=metadata['file_type'],
                                file_size=metadata['file_size'], file_created_at=metadata['file_created_at'],
                                file_modified_time=metadata['file_modified_time'], file_path=metadata['file_path'],
                                markdown_content=result.content, conversion_type=result.conversion_type, status='completed',
                                source=source, source_url=source_url
                            ))
                        processed_files += 1
                        logger.info(f"[Ingestion][{session_id}] SUCCESS {file_path}")
                        _enqueue(session_id, {'level': 'info', 'message': f'Successfully processed: {file_path}', 'stage': LogEvent.FILE_SUCCESS.value})

                    db.session.commit()

                    if is_cancelled(session_id):
                        _enqueue(session_id, {'level': 'warning', 'message': '当前文件完成后停止 (stopped after current file).', 'stage': LogEvent.CANCELLED.value})
                        break

                # Summary
                summary = {'total_files': len(matched_files), 'processed_files': processed_files, 'skipped_files': skipped_files, 'error_files': error_files}
                if not is_cancelled(session_id):
                    ingest_state.cursor_updated_at = start_time
                    _enqueue(session_id, {'level': 'info', 'message': 'All files processed.', 'stage': LogEvent.DONE.value, 'summary': summary})
                else:
                    _enqueue(session_id, {'level': 'warning', 'message': 'Processing stopped before completion.', 'stage': LogEvent.DONE.value, 'summary': summary})
            except Exception as e:
                error_msg = f"A critical error occurred: {e}\n{traceback.format_exc()}"
                logger.critical(error_msg)
                ingest_state.last_error_message = error_msg
                db.session.commit()
                _enqueue(session_id, {'level': 'critical', 'message': f'A critical error occurred: {str(e)}', 'stage': LogEvent.CRITICAL_ERROR.value})
            finally:
                ingest_state.processed = processed_files
                ingest_state.skipped = skipped_files
                ingest_state.errors = error_files
                ingest_state.last_ended_at = datetime.now(timezone.utc)
                db.session.commit()
                # Mark session done (do not end immediately to allow late consumers)
                sessions[session_id]['done'] = True

    t = threading.Thread(target=worker, name=f"ingest-{session_id}", daemon=True)
    t.start()
    sessions[session_id]['thread'] = t
    return session_id


def stream_async_session(session_id: str):
    """Generator for SSE that streams events from async session queue.

    Continues until session marked done and queue drained OR session gone."""
    heartbeat_interval = 2.0
    last_hb = 0.0
    while True:
        sessions = _get_sessions()
        sess = sessions.get(session_id)
        if not sess:
            break
        q = sess.get('event_queue')
        emitted = False
        while q:
            evt = q.popleft()
            yield evt
            emitted = True
        now = time.time()
        if now - last_hb >= heartbeat_interval:
            last_hb = now
            yield {
                'level': 'info',
                'message': f"Async heartbeat stop={sess.get('stop')} done={sess.get('done')} q={len(q)}",
                'stage': 'debug_state',
                'session_id': session_id
            }
        if sess.get('done') and not q:
            # Grace period done
            break
        if not emitted:
            time.sleep(0.3)


