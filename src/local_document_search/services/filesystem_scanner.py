import os
from datetime import datetime, timezone
from flask import current_app
from local_document_search.utils.file_utils import get_file_metadata

def find_files(root_path, recursive, file_types_str, date_from_str=None, date_to_str=None):
    """
    Scans a directory for files matching the given criteria, excluding configured paths.
    Returns a list of absolute file paths.
    """
    logger = current_app.logger
    matched_files = []

    # --- Load exclusion configurations ---
    excluded_dirs = current_app.config.get('EXCLUDED_DIRS', [])
    # Support excluding directories by suffix pattern (e.g., knowledge note image folders ending with '.assets')
    excluded_dir_suffixes = current_app.config.get('EXCLUDED_DIR_SUFFIXES', ['.assets'])
    excluded_extensions = tuple(f".{ext.lower()}" for ext in current_app.config.get('EXCLUDED_FILE_EXTENSIONS', []))

    # --- Timezone-aware date parsing ---
    date_from, date_to = None, None
    try:
        if date_from_str:
            date_from = datetime.fromisoformat(date_from_str).replace(tzinfo=timezone.utc)
        if date_to_str:
            date_to = datetime.fromisoformat(date_to_str + 'T23:59:59.999999').replace(tzinfo=timezone.utc)
    except ValueError as e:
        logger.error(f"Invalid date format provided to scanner: {e}")
        raise

    # --- File type parsing for inclusion ---
    file_types = [ft.strip().lower() for ft in file_types_str.split(',')] if file_types_str else None

    logger.debug(f"os.walk starting with root_path: '{root_path}'")
    for root, dirs, files in os.walk(root_path):
        # --- Exclude configured directories ---
        # First, drop exact matches
        filtered = []
        for d in dirs:
            # Exact name exclusion
            if d in excluded_dirs:
                continue
            # Suffix exclusion (case-insensitive)
            lower_d = d.lower()
            if any(lower_d.endswith(suf.lower()) for suf in excluded_dir_suffixes):
                continue
            filtered.append(d)
        dirs[:] = filtered
        
        for file in files:
            # --- Exclude configured file extensions ---
            if file.lower().endswith(excluded_extensions):
                continue

            file_path = os.path.join(root, file)
            
            # --- Include based on specified file types ---
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

