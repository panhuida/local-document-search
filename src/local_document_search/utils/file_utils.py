import os
import unicodedata
from datetime import datetime, timezone
from flask import current_app

def normalize_path(path):
    """
    规范化路径以存入数据库或进行比较。
    - 转换为绝对路径
    - NFC Unicode 规范化
    - 使用 / 作为路径分隔符
    - 保持盘符原始大小写
    """
    try:
        abs_path = os.path.abspath(path)
        nfc_path = unicodedata.normalize('NFC', abs_path)
        final_path = nfc_path.replace('\\', '/')
        return final_path
    except Exception:
        # 在处理非常规路径或无效路径时，返回一个可预测的、处理过的原始路径
        return unicodedata.normalize('NFC', path).replace('\\', '/')

def get_file_metadata(file_path):
    """获取文件元数据"""
    try:
        # 首先，使用原始路径获取文件状态，避免因路径处理导致找不到文件
        stat = os.stat(file_path)

        # 规范化路径以存入数据库
        final_path = normalize_path(file_path)

        return {
            'file_name': os.path.basename(file_path),
            'file_type': os.path.splitext(file_path)[1].lstrip('.'),
            'file_size': stat.st_size,
            'file_created_at': datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            'file_modified_time': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            'file_path': final_path
        }
    except FileNotFoundError:
        current_app.logger.warning(f"File not found when trying to get metadata: {file_path}")
        return None
