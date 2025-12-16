import os
import sys

# 将项目根目录添加到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from local_document_search import create_app

from local_document_search.extensions import db


def init_db():
    """初始化数据库"""
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Database initialized!")

if __name__ == '__main__':
    init_db()

