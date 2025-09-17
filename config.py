import os
import logging
from dotenv import load_dotenv

# 加载 .env 文件
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


# --- File Type Configuration (Single Source of Truth) ---
class ConversionCategory:
    NATIVE = 'native'
    PLAIN_TEXT = 'plain_text'
    CODE = 'code'
    STRUCTURED = 'structured'
    XMIND = 'xmind'

class Config:
    """基础配置类"""
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Logging Configuration ---
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper() # Default to INFO
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 3)) # For TimedRotatingFileHandler

    FILE_TYPE_CONFIG = {
        # ext: {'category', 'description'}
        'md':   {'category': ConversionCategory.NATIVE,     'description': 'Markdown'},
        'txt':  {'category': ConversionCategory.PLAIN_TEXT,  'description': 'Plain Text'},
        'sql':  {'category': ConversionCategory.CODE,        'description': 'SQL Script'},
        'py':   {'category': ConversionCategory.CODE,        'description': 'Python Script'},
        'sh':   {'category': ConversionCategory.CODE,        'description': 'Shell Script'},
        'html': {'category': ConversionCategory.STRUCTURED,  'description': 'HTML File'},
        'htm':  {'category': ConversionCategory.STRUCTURED,  'description': 'HTML File'},
        'pdf':  {'category': ConversionCategory.STRUCTURED,  'description': 'PDF Document'},
        'docx': {'category': ConversionCategory.STRUCTURED,  'description': 'Word Document'},
        'xlsx': {'category': ConversionCategory.STRUCTURED,  'description': 'Excel Spreadsheet'},
        'pptx': {'category': ConversionCategory.STRUCTURED,  'description': 'PowerPoint Presentation'},
        'doc':  {'category': ConversionCategory.STRUCTURED,  'description': 'Legacy Word Document'},
        'xls':  {'category': ConversionCategory.STRUCTURED,  'description': 'Legacy Excel Spreadsheet'},
        'ppt':  {'category': ConversionCategory.STRUCTURED,  'description': 'Legacy PowerPoint Presentation'},
        'xmind':{'category': ConversionCategory.XMIND,      'description': 'Xmind'},
    }

    # Dynamically generate file type lists from the single source of truth
    NATIVE_MARKDOWN_TYPES = [ext for ext, props in FILE_TYPE_CONFIG.items() if props['category'] == ConversionCategory.NATIVE]
    PLAIN_TEXT_TO_MARKDOWN_TYPES = [ext for ext, props in FILE_TYPE_CONFIG.items() if props['category'] == ConversionCategory.PLAIN_TEXT]
    CODE_TO_MARKDOWN_TYPES = [ext for ext, props in FILE_TYPE_CONFIG.items() if props['category'] == ConversionCategory.CODE]
    STRUCTURED_TO_MARKDOWN_TYPES = [ext for ext, props in FILE_TYPE_CONFIG.items() if props['category'] == ConversionCategory.STRUCTURED]
    XMIND_TO_MARKDOWN_TYPES = [ext for ext, props in FILE_TYPE_CONFIG.items() if props['category'] == ConversionCategory.XMIND]
    SUPPORTED_FILE_TYPES = list(FILE_TYPE_CONFIG.keys())

    # Joplin Configuration
    JOPLIN_API_TOKEN = os.environ.get('JOPLIN_API_TOKEN')
    JOPLIN_API_URL = os.environ.get('JOPLIN_API_URL', 'http://localhost:41184')

    # --- Application Logic Constants ---
    # Data Sources
    SOURCE_LOCAL_FS = 'local_fs'
    SOURCE_JOPLIN = 'Joplin'

    # Search Defaults
    SEARCH_DEFAULT_PER_PAGE = 20
    SEARCH_DEFAULT_SORT_BY = 'relevance'

    # Download path for WeChat articles
    DOWNLOAD_PATH = os.getenv('DOWNLOAD_PATH', 'downloads')

        # Ingestion Configs
    JOPLIN_IMPORT_BATCH_SIZE = 50

    # --- Filesystem Scanner Configuration ---
    EXCLUDED_DIRS = [
        '.git', '.vscode', '__pycache__', 'node_modules', '.assets', 
        'dist', 'build', 'venv'
    ]
    EXCLUDED_FILE_EXTENSIONS = [
        'log', 'tmp', 'bak', 'swo', 'swp', 'pyc'
    ]
