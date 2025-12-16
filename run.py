import sys
import os

# Add src to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from local_document_search import create_app
from werkzeug.serving import WSGIRequestHandler, run_simple
from datetime import datetime

app = create_app()

class ISORequestHandler(WSGIRequestHandler):
    def log(self, type, message, *args):  # Keep parent behavior for other parts
        super().log(type, message, *args)
    def log_date_time_string(self):
        # Use same timezone assumption as default (localtime)
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

if __name__ == '__main__':
    app.logger.info("Application starting...")
    app.logger.info("Enabling threaded server so that /convert/stop can respond while ingestion stream is active")
    # Use run_simple with threaded=True (Werkzeug) to avoid single-thread blocking SSE + control endpoint
    run_simple('127.0.0.1', 5000, app, use_reloader=True, request_handler=ISORequestHandler, threaded=True)

