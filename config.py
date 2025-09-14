import os
import logging
from dotenv import load_dotenv

# 加载 .env 文件
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """基础配置类"""
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = logging.DEBUG if os.environ.get('FLASK_DEBUG') == '1' else logging.INFO

    # 文件类型配置
    NATIVE_MARKDOWN_TYPES = os.environ.get('NATIVE_MARKDOWN_TYPES', 'md').split(',')
    PLAIN_TEXT_TO_MARKDOWN_TYPES = os.environ.get('PLAIN_TEXT_TO_MARKDOWN_TYPES', 'txt').split(',')
    CODE_TO_MARKDOWN_TYPES = os.environ.get('CODE_TO_MARKDOWN_TYPES', 'sql,py').split(',')
    LOG_TO_MARKDOWN_TYPES = os.environ.get('LOG_TO_MARKDOWN_TYPES', 'log').split(',')
    STRUCTURED_TO_MARKDOWN_TYPES = os.environ.get('STRUCTURED_TO_MARKDOWN_TYPES', 'html,htm,pdf,docx,xlsx,pptx').split(',')
    SUPPORTED_FILE_TYPES = os.environ.get('SUPPORTED_FILE_TYPES', 'md,html,htm,pdf,docx,xlsx,pptx,sql,py').split(',')

    # Joplin Configuration
    JOPLIN_API_TOKEN = os.environ.get('JOPLIN_API_TOKEN')
    JOPLIN_API_URL = os.environ.get('JOPLIN_API_URL', 'http://localhost:41184')