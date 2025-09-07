import os
import time
from flask import Blueprint, request, jsonify, current_app
from app.services.file_scanner import scan_folder
from app.services.converter import convert_to_markdown
from app.utils.file_utils import get_file_metadata
from app.models import Document, ConversionError
from app.extensions import db
from sqlalchemy import func

bp = Blueprint('convert', __name__, url_prefix='/api')

@bp.route('/scan-folder', methods=['POST'])
def scan_folder_route():
    logger = current_app.logger
    data = request.get_json()
    folder_path = data.get('folder_path')
    date_from = data.get('date_from')
    date_to = data.get('date_to')
    recursive = data.get('recursive', True)
    file_types = data.get('file_types')

    logger.info(f"Starting folder scan with parameters: path={folder_path}, from={date_from}, to={date_to}, recursive={recursive}, types={file_types}")

    if not folder_path or not os.path.isdir(folder_path):
        logger.warning(f"Invalid folder path received: {folder_path}")
        return jsonify({'status': 'error', 'message': '无效的文件夹路径'}), 400

    start_time = time.time()
    matched_files = scan_folder(folder_path, date_from, date_to, recursive, file_types)
    logger.info(f"Scan found {len(matched_files)} matching files.")
    
    processed_files = 0
    skipped_files = 0
    error_files = 0

    TSVECTOR_LIMIT = 1000000 # Set a safe limit just under 1MB

    for file_path in matched_files:
        logger.debug(f"Processing file: {file_path}")
        metadata = get_file_metadata(file_path)
        if not metadata:
            logger.debug(f"Could not get metadata for {file_path}, skipping.")
            continue

        existing_doc = Document.query.filter_by(file_path=metadata['file_path']).first()
        if existing_doc and existing_doc.file_modified_time == metadata['file_modified_time']:
            logger.info(f"Skipping unchanged file: {file_path}")
            skipped_files += 1
            continue

        markdown_content, is_converted = convert_to_markdown(file_path, metadata['file_type'])

        if is_converted == 4:
            logger.error(f"Failed to convert file: {file_path}. Reason: {markdown_content}")
            error_files += 1
            error = ConversionError(
                file_name=metadata['file_name'],
                file_path=metadata['file_path'],
                error_message=markdown_content
            )
            db.session.add(error)
            continue

        # Truncate content for tsvector, but save full content
        content_for_vector = markdown_content[:TSVECTOR_LIMIT]

        if existing_doc:
            logger.debug(f"Updating existing document in DB: {file_path}")
            existing_doc.file_size = metadata['file_size']
            existing_doc.file_modified_time = metadata['file_modified_time']
            existing_doc.markdown_content = markdown_content
            existing_doc.is_converted = is_converted
            existing_doc.search_vector = func.to_tsvector('simple', content_for_vector)
        else:
            logger.debug(f"Adding new document to DB: {file_path}")
            new_doc = Document(
                file_name=metadata['file_name'],
                file_type=metadata['file_type'],
                file_size=metadata['file_size'],
                file_created_at=metadata['file_created_at'],
                file_modified_time=metadata['file_modified_time'],
                file_path=metadata['file_path'],
                markdown_content=markdown_content,
                is_converted=is_converted,
                search_vector=func.to_tsvector('simple', content_for_vector)
            )
            db.session.add(new_doc)
        
        processed_files += 1

    db.session.commit()

    end_time = time.time()
    processing_time = f'{end_time - start_time:.2f}s'
    logger.info(f"Scan completed in {processing_time}. Processed: {processed_files}, Skipped: {skipped_files}, Errors: {error_files}")

    return jsonify({
        'status': 'success',
        'message': '文件扫描完成',
        'data': {
            'scan_summary': {
                'total_files': len(matched_files),
                'processed_files': processed_files,
                'skipped_files': skipped_files,
                'error_files': error_files
            },
            'processing_time': processing_time,
            'start_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(start_time)),
            'end_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(end_time))
        }
    })