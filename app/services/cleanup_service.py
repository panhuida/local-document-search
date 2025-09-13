import os
from app.models import Document
from app.extensions import db
from app.utils.file_utils import normalize_path

def find_orphan_files(folder_path, file_type_filter=None, path_keyword_filter=None):
    """
    查找指定文件夹路径下，存在于数据库但文件系统中已不存在的“孤儿”文件记录。

    :param folder_path: 用户指定的要检查的文件夹绝对路径。
    :param file_type_filter: (可选) 用于筛选的文件类型。
    :param path_keyword_filter: (可选) 用于筛选文件路径的关键词。
    :return: 孤儿文件记录的查询对象。
    """
    # 1. 标准化输入的文件夹路径
    normalized_folder_path = normalize_path(folder_path)

    # 2. 从数据库中查询所有以该路径开头的记录
    # 使用 startswith 操作符进行前缀匹配，这比 like 更安全、更高效
    query = Document.query.filter(Document.file_path.startswith(normalized_folder_path))
    
    db_file_paths = {doc.file_path: doc for doc in query.all()}

    # 3. 遍历文件系统，获取真实存在的文件路径
    existing_file_paths = set()
    try:
        if not os.path.isdir(folder_path):
            # 如果路径不是一个有效的目录，直接返回空查询
            return Document.query.filter(db.false())

        for root, _, files in os.walk(folder_path):
            for name in files:
                file_path = os.path.join(root, name)
                normalized_file_path = normalize_path(file_path)
                existing_file_paths.add(normalized_file_path)
    except OSError:
        # 处理路径名过长或其他OS级别错误
        return Document.query.filter(db.false())

    # 4. 对比找出孤儿文件
    orphan_doc_ids = []
    for path, doc in db_file_paths.items():
        if path not in existing_file_paths:
            orphan_doc_ids.append(doc.id)
    
    if not orphan_doc_ids:
        return Document.query.filter(db.false()) # 如果没有孤儿，返回一个空查询

    # 5. 基于孤儿ID列表构建最终查询，并应用筛选条件
    final_query = Document.query.filter(Document.id.in_(orphan_doc_ids))

    if file_type_filter:
        final_query = final_query.filter(Document.file_type == file_type_filter)
    
    if path_keyword_filter:
        final_query = final_query.filter(Document.file_path.ilike(f"%{path_keyword_filter}%"))

    return final_query
