import os
import sys

# 将项目根目录添加到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from app import create_app
from app.extensions import db


def init_db():
    """初始化数据库"""
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Database initialized!")

if __name__ == '__main__':
    init_db()
