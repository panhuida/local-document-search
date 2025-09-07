import os
import datetime

def scan_folder(folder_path, date_from=None, date_to=None, recursive=True, file_types=None):
    """扫描文件夹，根据条件过滤文件"""
    matched_files = []
    for root, dirs, files in os.walk(folder_path):
        # Exclude .assets folders from scanning
        dirs[:] = [d for d in dirs if not d.endswith('.assets')]
        for file in files:
            if file_types and not file.lower().endswith(tuple(file_types)):
                continue

            file_path = os.path.join(root, file)
            try:
                modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                if date_from and modified_time < date_from:
                    continue
                if date_to and modified_time > date_to:
                    continue
                
                matched_files.append(file_path)
            except FileNotFoundError:
                continue # 文件在扫描过程中被删除

        if not recursive:
            break
            
    return matched_files
