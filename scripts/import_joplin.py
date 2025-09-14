
import os
import sys
import requests
import json
from datetime import datetime, timezone, timedelta
import traceback

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import io
from markdownify import markdownify as md

from flask import Flask
from app import create_app, db
from app.models import Document, IngestState, ConversionType
from sqlalchemy.exc import SQLAlchemyError

# --- Configuration ---
JOPLIN_SOURCE = "Joplin"
JOPLIN_SCOPE_KEY = "Joplin" # Global scope for all Joplin notes
BATCH_SIZE = 50

class JoplinImporter:
    def __init__(self, app):
        self.app = app
        self.api_url = app.config.get('JOPLIN_API_URL')
        self.api_token = app.config.get('JOPLIN_API_TOKEN')
        self.logger = app.logger
        self.session = requests.Session()
        self.session.params = {'token': self.api_token}
        self.folders_map = {}

    def _api_get(self, endpoint, params=None):
        """Helper for making GET requests to Joplin API."""
        try:
            response = self.session.get(f"{self.api_url}/{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Joplin API request failed for endpoint '{endpoint}': {e}")
            raise

    def _build_folder_map(self):
        """Fetches all folders and builds a map for path construction."""
        self.logger.info("Fetching all folders from Joplin...")
        all_folders = self._api_get('folders', {'fields': 'id,parent_id,title'})['items']
        self.folders_map = {f['id']: {'parent_id': f.get('parent_id', ''), 'title': f['title']} for f in all_folders}
        self.logger.info(f"Built map for {len(self.folders_map)} folders.")

    def _get_folder_path(self, note_parent_id):
        """Recursively builds the folder path for a note."""
        if not self.folders_map:
            self._build_folder_map()
        
        path_parts = []
        current_id = note_parent_id
        while current_id:
            folder = self.folders_map.get(current_id)
            if folder:
                path_parts.append(folder['title'])
                current_id = folder.get('parent_id', '')
            else:
                break # Should not happen in a consistent DB
        return "/".join(reversed(path_parts))

    def _convert_ms_to_datetime(self, ms_timestamp):
        """Converts millisecond timestamp to timezone-aware datetime."""
        if not ms_timestamp:
            return None
        return datetime.fromtimestamp(ms_timestamp / 1000.0, tz=timezone.utc)

    def run(self, full_resync=False, test_note_ids=None):
        """Main method to run the import process."""
        with self.app.app_context():
            self.logger.info("--- Starting Joplin Import ---")
            
            ingest_state = db.session.query(IngestState).filter_by(source=JOPLIN_SOURCE, scope_key=JOPLIN_SCOPE_KEY).first()
            if not ingest_state:
                ingest_state = IngestState(source=JOPLIN_SOURCE, scope_key=JOPLIN_SCOPE_KEY)
                db.session.add(ingest_state)
            
            cursor_time = ingest_state.cursor_updated_at if not full_resync and ingest_state.cursor_updated_at else None
            if cursor_time:
                self.logger.info(f"Performing incremental sync. Fetching notes updated after {cursor_time.isoformat()}")
            else:
                self.logger.info("Performing full sync. Fetching all notes.")

            start_time = datetime.now(timezone.utc)
            ingest_state.last_started_at = start_time
            ingest_state.total_files = 0
            ingest_state.processed = 0
            ingest_state.skipped = 0
            ingest_state.errors = 0
            ingest_state.last_error_message = None
            db.session.commit()

            try:
                # Fetch all folders first for efficiency
                self._build_folder_map()

                # Fetch notes
                page = 1
                processed_count = 0
                while True:
                    self.logger.info(f"Fetching page {page} of notes...")
                    params = {
                        'fields': 'id,parent_id,title,body,created_time,updated_time,source_url,markup_language',
                        'limit': BATCH_SIZE,
                        'page': page,
                        'order_by': 'updated_time',
                        'order_dir': 'ASC'
                    }
                    if test_note_ids:
                        # In test mode, we ignore pagination and fetch specific notes
                        notes = [self._api_get(f'notes/{note_id}', {'fields': params['fields']}) for note_id in test_note_ids]
                    else:
                        notes_page = self._api_get('notes', params)
                        notes = notes_page.get('items', [])

                    if not notes:
                        self.logger.info("No more notes to fetch.")
                        break
                    
                    ingest_state.total_files += len(notes)

                    for note in notes:
                        note_updated_time = self._convert_ms_to_datetime(note['updated_time'])

                        # Incremental sync check
                        if cursor_time and note_updated_time and note_updated_time < cursor_time:
                            ingest_state.skipped += 1
                            continue
                        
                        try:
                            folder_chain = self._get_folder_path(note.get('parent_id'))
                            file_path = f"joplin://{folder_chain}/{note['title']}__{note['id']}"

                            # Check if document exists and is up-to-date
                            existing_doc = db.session.query(Document).filter_by(file_path=file_path).first()
                            if existing_doc and existing_doc.file_modified_time == note_updated_time:
                                self.logger.debug(f"Skipping unchanged note: {note['title']}")
                                ingest_state.skipped += 1
                                continue

                            # --- Field Mapping ---
                            html_content = note.get('body', '')
                            
                            # Convert HTML string to Markdown using markdownify
                            markdown_content = None
                            conversion_type = None
                            if html_content:
                                try:
                                    markdown_content = md(html_content).replace('\x00', '')
                                    conversion_type = ConversionType.STRUCTURED_TO_MD # Treat as a structured conversion
                                except Exception as e:
                                    raise ValueError(f"Markdownify conversion failed: {e}")
                            else:
                                # Handle empty body
                                markdown_content = ""
                                conversion_type = ConversionType.DIRECT

                            doc_data = {
                                'file_name': note['title'],
                                'file_type': 'md' if note['markup_language'] == 2 else 'html',
                                'file_size': len(html_content.encode('utf-8')) if html_content else 0,
                                'file_created_at': self._convert_ms_to_datetime(note['created_time']),
                                'file_modified_time': note_updated_time,
                                'file_path': file_path,
                                'markdown_content': markdown_content,
                                'conversion_type': conversion_type,
                                'status': 'completed',
                                'error_message': None,
                                'source': JOPLIN_SOURCE,
                                'source_url': note.get('source_url', '')
                            }

                            if existing_doc:
                                self.logger.info(f"Updating note: {note['title']}")
                                for key, value in doc_data.items():
                                    setattr(existing_doc, key, value)
                            else:
                                self.logger.info(f"Adding new note: {note['title']}")
                                new_doc = Document(**doc_data)
                                db.session.add(new_doc)
                            
                            ingest_state.processed += 1

                        except Exception as e:
                            self.logger.error(f"Failed to process note ID {note.get('id')}: {e}")
                            ingest_state.errors += 1
                            # Optionally save error to document object if it exists/is created

                        processed_count += 1
                        if processed_count % BATCH_SIZE == 0:
                            self.logger.info(f"Committing batch of {BATCH_SIZE} notes...")
                            db.session.commit()
                    
                    if test_note_ids: # Only run once for test mode
                        break
                    page += 1
                
                # Final commit for the last batch
                self.logger.info("Committing final batch...")
                db.session.commit()

                ingest_state.cursor_updated_at = start_time
                self.logger.info("--- Joplin Import Finished Successfully ---")

            except Exception as e:
                db.session.rollback()
                error_msg = f"A critical error occurred: {e}\n{traceback.format_exc()}"
                self.logger.critical(error_msg)
                ingest_state.last_error_message = error_msg
            finally:
                ingest_state.last_ended_at = datetime.now(timezone.utc)
                db.session.commit()
                self.logger.info(f"Run summary: Total={ingest_state.total_files}, Processed={ingest_state.processed}, Skipped={ingest_state.skipped}, Errors={ingest_state.errors}")


if __name__ == '__main__':
    app = create_app()
    
    # Simple argument parsing
    is_full_resync = '--full' in sys.argv
    test_ids_arg = [arg for arg in sys.argv if arg.startswith('--test-ids=')]
    test_ids = test_ids_arg[0].split('=')[1].split(',') if test_ids_arg else None

    importer = JoplinImporter(app)
    importer.run(full_resync=is_full_resync, test_note_ids=test_ids)
