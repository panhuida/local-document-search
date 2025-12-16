"""End-to-end smoke validation script.

Usage (Windows cmd):
  set FLASK_ENV=development
  set LOG_LEVEL=INFO
  python scripts/e2e_smoke.py

This script performs:
 1. App + in-memory SQLite bootstrap.
 2. Creates a temporary directory with mixed file types (.md, .txt, .py, .xyz unsupported).
 3. Runs a full ingestion and validates event sequence + session_id presence.
 4. Verifies documents persisted with correct conversion_type/status.
 5. Executes a retry on the failed (unsupported) document and confirms it remains failed (as expected).
 6. Runs a second ingestion and cancels it mid-way to exercise session cancellation.
 7. Exercises conversion_types filtering search.
 8. Prints a final structured summary.

Exit code 0 on success, non‑zero on failure.
"""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import tempfile

from typing import List, Dict, Any

from local_document_search import create_app
from local_document_search.extensions import db
from local_document_search.models import Document, ConversionType
from local_document_search.services.ingestion_manager import run_local_ingestion, request_cancel_ingestion
from local_document_search.services.search_service import SearchParams, search_documents
from local_document_search.services.converters import convert_to_markdown


def _assert(condition: bool, message: str, errors: List[str]):
    if not condition:
        errors.append(message)


def _collect(generator):
    for item in generator:
        yield item


def run_full_ingestion(tmpdir: str, errors: List[str]) -> Dict[str, Any]:
    events = []
    session_id = None
    for ev in _collect(run_local_ingestion(tmpdir, None, None, True, None)):
        events.append(ev)
        if not session_id and 'session_id' in ev:
            session_id = ev['session_id']
    stages = [e.get('stage') for e in events]
    _assert(session_id is not None, 'No session_id present in first ingestion events', errors)
    for required in ('scan_start', 'scan_complete', 'done'):
        _assert(required in stages, f'Missing stage {required} in full ingestion', errors)
    return {
        'session_id': session_id,
        'events': events,
        'stages': stages
    }


def run_cancel_ingestion(tmpdir: str, errors: List[str]) -> Dict[str, Any]:
    events = []
    gen = run_local_ingestion(tmpdir, None, None, True, None)
    session_id = None
    cancelled_triggered = False
    for ev in gen:
        events.append(ev)
        if not session_id and 'session_id' in ev:
            session_id = ev['session_id']
        # After first file_processing event, issue cancel once
        if (ev.get('stage') == 'file_processing' and not cancelled_triggered and session_id):
            request_cancel_ingestion(session_id)
            cancelled_triggered = True
    stages = [e.get('stage') for e in events]
    _assert('cancelled' in stages, 'Cancellation stage not observed', errors)
    return {
        'session_id': session_id,
        'events': events,
        'stages': stages
    }


def retry_failed_document(errors: List[str]):
    failed = Document.query.filter_by(status='failed').first()
    _assert(failed is not None, 'No failed document found to retry', errors)
    if not failed:
        return
    result = convert_to_markdown(failed.file_path, failed.file_type)
    # Unsupported type will still fail; we just verify stable behavior
    _assert(result.success is False, 'Retry unexpectedly succeeded for unsupported type', errors)


def validate_search_filters(errors: List[str]):
    params = SearchParams(conversion_types=[ConversionType.TEXT_TO_MD])
    pagination = search_documents(params)
    for item in pagination.items:
        doc = item[0] if isinstance(item, tuple) else item
        _assert(doc.conversion_type == ConversionType.TEXT_TO_MD, 'Search filter returned wrong conversion_type', errors)


def main() -> int:
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    # Avoid file logging in test
    with app.app_context():
        db.create_all()
        errors: List[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            # Prepare files
            md_path = os.path.join(tmp, 'note.md')
            txt_path = os.path.join(tmp, 'plain.txt')
            py_path = os.path.join(tmp, 'code.py')
            bad_path = os.path.join(tmp, 'raw.xyz')
            open(md_path, 'w', encoding='utf-8').write('# Title\nContent')
            open(txt_path, 'w', encoding='utf-8').write('hello text')
            open(py_path, 'w', encoding='utf-8').write('print("hi")')
            open(bad_path, 'w', encoding='utf-8').write('unsupported')

            full_result = run_full_ingestion(tmp, errors)
            # Basic DB checks
            docs = Document.query.all()
            _assert(any(d.conversion_type == ConversionType.DIRECT for d in docs), 'DIRECT conversion missing', errors)
            _assert(any(d.conversion_type == ConversionType.TEXT_TO_MD for d in docs), 'TEXT_TO_MD conversion missing', errors)
            _assert(any(d.conversion_type == ConversionType.CODE_TO_MD for d in docs), 'CODE_TO_MD conversion missing', errors)
            _assert(any(d.status == 'failed' and d.file_path.endswith('raw.xyz') for d in docs), 'Failed unsupported doc missing', errors)

            retry_failed_document(errors)

            cancel_result = run_cancel_ingestion(tmp, errors)

            validate_search_filters(errors)

        status = 'SUCCESS' if not errors else 'FAILED'
        print('==== E2E SMOKE RESULT ====' )
        print('Status:', status)
        if errors:
            for e in errors:
                print(' -', e)
            return 1
        # brief summary
        print(f"Full ingestion stages: {full_result['stages']}")
        print(f"Cancel ingestion stages: {cancel_result['stages']}")
        print('Documents in DB:', Document.query.count())
        return 0


if __name__ == '__main__':
    sys.exit(main())

