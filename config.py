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
    IMAGE = 'image'
    VIDEO = 'video'
    DIAGRAM = 'diagram'
    HTML = 'html'

class Config:
    """基础配置类"""
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Logging Configuration ---
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper() # Default to INFO
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 3)) # For TimedRotatingFileHandler
    LOG_TIME_FORMAT = os.environ.get('LOG_TIME_FORMAT', '%Y-%m-%d %H:%M:%S')

    FILE_TYPE_CONFIG = {
        # ext: {'category', 'description'}
        'md':   {'category': ConversionCategory.NATIVE,     'description': 'Markdown'},
        'txt':  {'category': ConversionCategory.PLAIN_TEXT,  'description': 'Plain Text'},
        'sql':  {'category': ConversionCategory.CODE,        'description': 'SQL Script'},
        'py':   {'category': ConversionCategory.CODE,        'description': 'Python Script'},
        'sh':   {'category': ConversionCategory.CODE,        'description': 'Shell Script'},
    # HTML 独立分类，便于在导入界面与结构化文档（Office/PDF）区分
    'html': {'category': ConversionCategory.HTML,        'description': 'HTML File'},
    'htm':  {'category': ConversionCategory.HTML,        'description': 'HTML File'},
        'pdf':  {'category': ConversionCategory.STRUCTURED,  'description': 'PDF Document'},
        'docx': {'category': ConversionCategory.STRUCTURED,  'description': 'Word Document'},
        'xlsx': {'category': ConversionCategory.STRUCTURED,  'description': 'Excel Spreadsheet'},
        'pptx': {'category': ConversionCategory.STRUCTURED,  'description': 'PowerPoint Presentation'},
        'doc':  {'category': ConversionCategory.STRUCTURED,  'description': 'Legacy Word Document'},
        'xls':  {'category': ConversionCategory.STRUCTURED,  'description': 'Legacy Excel Spreadsheet'},
        'ppt':  {'category': ConversionCategory.STRUCTURED,  'description': 'Legacy PowerPoint Presentation'},
        'xmind':{'category': ConversionCategory.XMIND,      'description': 'Xmind'},
        'png':  {'category': ConversionCategory.IMAGE,       'description': 'PNG Image'},
        'jpg':  {'category': ConversionCategory.IMAGE,       'description': 'JPEG Image'},
        'jpeg': {'category': ConversionCategory.IMAGE,       'description': 'JPEG Image'},
        'bmp':  {'category': ConversionCategory.IMAGE,       'description': 'Bitmap Image'},
        'gif':  {'category': ConversionCategory.IMAGE,       'description': 'GIF Image'},
        # Video
        'mp4':  {'category': ConversionCategory.VIDEO,       'description': 'MP4 Video'},
        'mkv':  {'category': ConversionCategory.VIDEO,       'description': 'Matroska Video'},
        'mov':  {'category': ConversionCategory.VIDEO,       'description': 'QuickTime Video'},
        'webm': {'category': ConversionCategory.VIDEO,       'description': 'WebM Video'},
        # Diagram
        'drawio': {'category': ConversionCategory.DIAGRAM,    'description': 'Draw.io Diagram'},
    }

    # Dynamically generate file type lists from the single source of truth
    NATIVE_MARKDOWN_TYPES = [ext for ext, props in FILE_TYPE_CONFIG.items() if props['category'] == ConversionCategory.NATIVE]
    PLAIN_TEXT_TO_MARKDOWN_TYPES = [ext for ext, props in FILE_TYPE_CONFIG.items() if props['category'] == ConversionCategory.PLAIN_TEXT]
    CODE_TO_MARKDOWN_TYPES = [ext for ext, props in FILE_TYPE_CONFIG.items() if props['category'] == ConversionCategory.CODE]
    STRUCTURED_TO_MARKDOWN_TYPES = [ext for ext, props in FILE_TYPE_CONFIG.items() if props['category'] == ConversionCategory.STRUCTURED]
    HTML_TO_MARKDOWN_TYPES = [ext for ext, props in FILE_TYPE_CONFIG.items() if props['category'] == ConversionCategory.HTML]
    XMIND_TO_MARKDOWN_TYPES = [ext for ext, props in FILE_TYPE_CONFIG.items() if props['category'] == ConversionCategory.XMIND]
    IMAGE_TO_MARKDOWN_TYPES = [ext for ext, props in FILE_TYPE_CONFIG.items() if props['category'] == ConversionCategory.IMAGE]
    VIDEO_TO_MARKDOWN_TYPES = [ext for ext, props in FILE_TYPE_CONFIG.items() if props['category'] == ConversionCategory.VIDEO]
    DRAWIO_TO_MARKDOWN_TYPES = [ext for ext, props in FILE_TYPE_CONFIG.items() if props['category'] == ConversionCategory.DIAGRAM]
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

    # --- Image Caption Provider Configuration ---
    # Options: local | openai | google-genai
    IMAGE_CAPTION_PROVIDER = os.environ.get('IMAGE_CAPTION_PROVIDER', 'google-genai').lower()
    # Local OCR language (for pytesseract); can be overridden by env TESSERACT_LANG
    TESSERACT_LANG = os.environ.get('TESSERACT_LANG', 'chi_sim+eng')
    # OpenAI model override
    OPENAI_IMAGE_MODEL = os.environ.get('OPENAI_IMAGE_MODEL', 'gpt-5-mini')
    # Gemini model override
    GEMINI_IMAGE_MODEL = os.environ.get('GEMINI_IMAGE_MODEL', os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash'))
    # Whether to include YAML front matter for image conversions (local OCR now, future: all providers)
    ENABLE_IMAGE_FRONT_MATTER = os.environ.get('ENABLE_IMAGE_FRONT_MATTER', 'true').lower() in ('1', 'true', 'yes', 'on')
    # Provider fallback chain (e.g. "openai,google-genai,local"). If empty -> use IMAGE_CAPTION_PROVIDER only
    RAW_IMAGE_PROVIDER_CHAIN = os.environ.get('IMAGE_PROVIDER_CHAIN', '').strip()
    IMAGE_PROVIDER_CHAIN = [p.strip().lower() for p in RAW_IMAGE_PROVIDER_CHAIN.split(',') if p.strip()] if RAW_IMAGE_PROVIDER_CHAIN else []
