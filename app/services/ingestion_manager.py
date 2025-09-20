import traceback
import os
import json
from datetime import datetime, timezone
from flask import current_app
from app.extensions import db
from app.models import Document, IngestState
from app.utils.file_utils import get_file_metadata
from app.services.filesystem_scanner import find_files

# Global in-module cancellation flag (simple cooperative cancellation)
_CANCEL_FLAG = { 'stop': False }

def request_cancel_ingestion():
    """Set the global cancellation flag to request stop."""
    _CANCEL_FLAG['stop'] = True

def reset_cancel_flag():
    _CANCEL_FLAG['stop'] = False
from app.services.converters import convert_to_markdown

def run_local_ingestion(folder_path, date_from_str, date_to_str, recursive, file_types_str):
    """
    Orchestrates the ingestion process for a local folder, using the IngestState table.
    """
    logger = current_app.logger
    start_time = datetime.now(timezone.utc)
    # Reset cancel flag at the start of a new ingestion session
    reset_cancel_flag()

    # --- IngestState Management ---
    ingest_state = db.session.query(IngestState).filter_by(source=current_app.config['SOURCE_LOCAL_FS'], scope_key=folder_path).first()
    if not ingest_state:
        ingest_state = IngestState(source=current_app.config['SOURCE_LOCAL_FS'], scope_key=folder_path)
        db.session.add(ingest_state)
    
    ingest_state.last_started_at = start_time
    ingest_state.last_error_message = None
    db.session.commit()

    # Use cursor if date_from is not specified, to allow for overrides
    effective_date_from = date_from_str
    if not date_from_str and ingest_state.cursor_updated_at:
        effective_date_from = ingest_state.cursor_updated_at.isoformat()

    processed_files, skipped_files, error_files = 0, 0, 0

    try:
        yield {'level': 'info', 'message': f"Starting folder scan: {folder_path}", 'stage': 'scan_start'}
        
        matched_files = find_files(folder_path, recursive, file_types_str, effective_date_from, date_to_str)
        
        total_files = len(matched_files)
        ingest_state.total_files = total_files
        db.session.commit()
        yield {'level': 'info', 'message': f"Scan found {total_files} matching files.", 'stage': 'scan_complete', 'total_files': total_files}

        if total_files == 0:
            summary = {'total_files': 0, 'processed_files': 0, 'skipped_files': 0, 'error_files': 0}
            yield {'level': 'info', 'message': "No files to process.", 'stage': 'done', 'summary': summary}
            ingest_state.cursor_updated_at = start_time
            return

        for i, file_path in enumerate(matched_files):
            if _CANCEL_FLAG.get('stop'):
                yield {'level': 'warning', 'message': 'Ingestion cancelled by user request.', 'stage': 'cancelled'}
                break
            progress = int(((i + 1) / total_files) * 100)
            
            metadata = get_file_metadata(file_path)
            if not metadata:
                yield {'level': 'warning', 'message': f"Could not get metadata for {file_path}, skipping.", 'stage': 'file_skip'}
                continue

            yield {'level': 'info', 'message': f"Processing file {i+1}/{total_files}: {metadata['file_name']}", 'stage': 'file_processing', 'progress': progress, 'current_file': metadata['file_name']}

            # --- Read sidecar metadata if it exists ---
            source_url = None
            try:
                meta_path_str = file_path + ".meta.json"
                if os.path.exists(meta_path_str):
                    with open(meta_path_str, 'r', encoding='utf-8') as f:
                        meta_data = json.load(f)
                        source_url = meta_data.get('source_url')
            except Exception as e:
                logger.warning(f"Could not read or parse metadata file for {file_path}: {e}")

            # --- Determine the source based on file path ---
            source = current_app.config['SOURCE_LOCAL_FS'] # Default source
            download_path = current_app.config.get('DOWNLOAD_PATH')
            if download_path:
                try:
                    # Normalize paths to handle different OS separators
                    normalized_download_path = os.path.normpath(download_path)
                    normalized_file_path = os.path.normpath(file_path)

                    # Check if the file is inside a subdirectory of the download path
                    if normalized_file_path.startswith(normalized_download_path + os.sep):
                        relative_path = os.path.relpath(normalized_file_path, normalized_download_path)
                        path_parts = relative_path.split(os.sep)
                        # e.g., 'AccountName/article.html' -> path_parts=['AccountName', 'article.html']
                        if len(path_parts) > 1:
                            account_name = path_parts[0]
                            source = f"公众号_{account_name}"
                except Exception as e:
                    logger.warning(f"Could not determine source for {file_path} from DOWNLOAD_PATH: {e}")

            existing_doc = Document.query.filter(Document.file_path.ilike(metadata['file_path'])).first()
            if existing_doc and existing_doc.file_modified_time == metadata['file_modified_time']:
                skipped_files += 1
                yield {'level': 'info', 'message': f"Skipping unchanged file: {file_path}", 'stage': 'file_skip', 'reason': 'unchanged'}
                continue

            content, conversion_type = convert_to_markdown(file_path, metadata['file_type'])

            if conversion_type is None:
                error_files += 1
                error_message = content
                if existing_doc:
                    existing_doc.status = 'failed'
                    existing_doc.error_message = error_message
                    existing_doc.source = source # Update source even on failure
                else:
                    new_doc = Document(
                        file_name=metadata['file_name'], file_type=metadata['file_type'],
                        file_size=metadata['file_size'], file_created_at=metadata['file_created_at'],
                        file_modified_time=metadata['file_modified_time'], file_path=metadata['file_path'],
                        status='failed', error_message=error_message, source=source,
                        source_url=source_url
                    )
                    db.session.add(new_doc)
                yield {'level': 'error', 'message': f"Failed to convert file: {file_path}. Reason: {error_message}", 'stage': 'file_error'}
            else:
                if existing_doc:
                    existing_doc.file_size = metadata['file_size']
                    existing_doc.file_modified_time = metadata['file_modified_time']
                    existing_doc.markdown_content = content
                    existing_doc.conversion_type = conversion_type
                    existing_doc.status = 'completed'
                    existing_doc.error_message = None
                    existing_doc.source = source
                    existing_doc.source_url = source_url
                else:
                    new_doc = Document(
                        file_name=metadata['file_name'], file_type=metadata['file_type'],
                        file_size=metadata['file_size'], file_created_at=metadata['file_created_at'],
                        file_modified_time=metadata['file_modified_time'], file_path=metadata['file_path'],
                        markdown_content=content, conversion_type=conversion_type, status='completed', source=source,
                        source_url=source_url
                    )
                    db.session.add(new_doc)
                processed_files += 1
                yield {'level': 'info', 'message': f"Successfully processed: {file_path}", 'stage': 'file_success'}
            
            db.session.commit()

        if not _CANCEL_FLAG.get('stop'):
            ingest_state.cursor_updated_at = start_time
            summary = {'total_files': total_files, 'processed_files': processed_files, 'skipped_files': skipped_files, 'error_files': error_files}
            yield {'level': 'info', 'message': "All files processed.", 'stage': 'done', 'summary': summary}
        else:
            summary = {'total_files': total_files, 'processed_files': processed_files, 'skipped_files': skipped_files, 'error_files': error_files}
            yield {'level': 'warning', 'message': "Processing stopped before completion.", 'stage': 'done', 'summary': summary}

    except Exception as e:
        error_msg = f"A critical error occurred: {e}\n{traceback.format_exc()}"
        logger.critical(error_msg)
        ingest_state.last_error_message = error_msg
        db.session.commit() # Commit the error message
        yield {'level': 'critical', 'message': f"A critical error occurred: {str(e)}", 'stage': 'critical_error'}
    finally:
        ingest_state.processed = processed_files
        ingest_state.skipped = skipped_files
        ingest_state.errors = error_files
        ingest_state.last_ended_at = datetime.now(timezone.utc)
        db.session.commit()
