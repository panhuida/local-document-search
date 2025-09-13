from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.services.cleanup_service import find_orphan_files
from app.models import Document
from app.extensions import db

cleanup_bp = Blueprint('cleanup', __name__)

@cleanup_bp.route('/cleanup', methods=['GET'])
def cleanup_page():
    folder_path = request.args.get('folder_path', '')
    file_type = request.args.get('file_type', '')
    path_keyword = request.args.get('path_keyword', '')
    page = request.args.get('page', 1, type=int)
    
    orphan_docs_query = None
    if folder_path:
        orphan_docs_query = find_orphan_files(folder_path, file_type, path_keyword)
    
    if orphan_docs_query:
        pagination = orphan_docs_query.order_by(Document.file_path.asc()).paginate(page=page, per_page=20, error_out=False)
        orphan_docs = pagination.items
    else:
        pagination = None
        orphan_docs = []

    # 获取所有存在于数据库中的文件类型，用于筛选下拉菜单
    distinct_file_types = [item[0] for item in db.session.query(Document.file_type).distinct().all() if item[0]]

    return render_template(
        'cleanup.html',
        orphan_docs=orphan_docs,
        pagination=pagination,
        folder_path=folder_path,
        file_type=file_type,
        path_keyword=path_keyword,
        distinct_file_types=distinct_file_types
    )

@cleanup_bp.route('/cleanup/delete', methods=['POST'])
def delete_orphans():
    data = request.get_json()
    doc_ids_to_delete = data.get('ids')

    if not doc_ids_to_delete:
        return jsonify({'status': 'error', 'message': '没有提供要删除的文档ID。'}), 400

    try:
        num_deleted = db.session.query(Document).filter(Document.id.in_(doc_ids_to_delete)).delete(synchronize_session=False)
        db.session.commit()
        flash(f'成功删除了 {num_deleted} 条孤儿文件记录。', 'success')
        return jsonify({'status': 'success', 'message': f'成功删除了 {num_deleted} 条记录。'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'删除过程中发生错误: {str(e)}'}), 500
