import os
from datetime import datetime, timezone
from flask import current_app
from app.utils.file_utils import get_file_metadata

def find_files(root_path, recursive, file_types_str, date_from_str=None, date_to_str=None):
    """
    Scans a directory for files matching the given criteria.

    Returns a list of absolute file paths.
    """
    logger = current_app.logger
    matched_files = []

    # --- Timezone-aware date parsing ---
    date_from, date_to = None, None
    try:
        if date_from_str:
            date_from = datetime.fromisoformat(date_from_str).replace(tzinfo=timezone.utc)
        if date_to_str:
            date_to = datetime.fromisoformat(date_to_str + 'T23:59:59.999999').replace(tzinfo=timezone.utc)
    except ValueError as e:
        logger.error(f"Invalid date format provided to scanner: {e}")
        # Or raise the error to be handled by the manager
        raise

    # --- File type parsing ---
    file_types = [ft.strip().lower() for ft in file_types_str.split(',')] if file_types_str else None

    logger.debug(f"os.walk starting with root_path: '{root_path}'")
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if not d.endswith('.assets')]
        
        for file in files:
            file_path = os.path.join(root, file)
            
            if file_types and not file.lower().endswith(tuple(f".{ft}" for ft in file_types)):
                continue

            metadata = get_file_metadata(file_path)
            if not metadata:
                continue

            file_modified_time_utc = metadata['file_modified_time']
            if date_from and file_modified_time_utc < date_from:
                continue
            if date_to and file_modified_time_utc > date_to:
                continue
            
            matched_files.append(metadata['file_path']) # Use the normalized path from metadata

        if not recursive:
            break
            
    return matched_files
