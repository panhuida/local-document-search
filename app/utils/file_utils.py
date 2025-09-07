import os
import datetime

def get_file_metadata(file_path):
    """获取文件元数据"""
    try:
        stat = os.stat(file_path)
        return {
            'file_name': os.path.basename(file_path),
            'file_type': os.path.splitext(file_path)[1].lstrip('.'),
            'file_size': stat.st_size,
            'file_created_at': datetime.datetime.fromtimestamp(stat.st_ctime),
            'file_modified_time': datetime.datetime.fromtimestamp(stat.st_mtime),
            'file_path': os.path.abspath(file_path).replace('\\', '/')
        }
    except FileNotFoundError:
        return None
