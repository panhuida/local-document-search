from flask import Blueprint, jsonify, request, render_template, current_app
from app.services import wechat_service
import traceback

wechat_bp = Blueprint('wechat', __name__, url_prefix='/wechat')

# --- 页面路由 ---

@wechat_bp.route('/management')
def management_page():
    """公众号管理页面"""
    return render_template('wechat_management.html')

@wechat_bp.route('/articles')
def articles_page():
    """文章列表页面"""
    return render_template('wechat_articles.html')

# --- API 路由 ---

# === 公众号管理 API ===

@wechat_bp.route('/api/wechat_list', methods=['GET'])
def get_wechat_list():
    """获取所有公众号列表"""
    try:
        accounts = wechat_service.get_all_wechat_accounts()
        # 扩展to_dict以包含任务状态
        accounts_list = []
        for acc in accounts:
            acc_dict = acc.to_dict()
            task_status = wechat_service.get_collection_task_status(acc.id)
            acc_dict['task_status'] = task_status
            accounts_list.append(acc_dict)
        return jsonify(accounts_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@wechat_bp.route('/api/wechat_list', methods=['POST'])
def create_wechat_account():
    """创建新的公众号"""
    data = request.json
    try:
        new_account = wechat_service.add_wechat_account(data)
        return jsonify(new_account.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': '服务器内部错误'}), 500

@wechat_bp.route('/api/wechat_list/<int:id>', methods=['PUT'])
def update_wechat_account(id):
    """更新指定ID的公众号"""
    data = request.json
    try:
        updated_account = wechat_service.update_wechat_account(id, data)
        if updated_account is None:
            return jsonify({'error': '公众号未找到'}), 404
        return jsonify(updated_account.to_dict())
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': '服务器内部错误'}), 500

@wechat_bp.route('/api/wechat_list/<int:id>', methods=['DELETE'])
def delete_wechat_account(id):
    """删除指定ID的公众号"""
    try:
        if wechat_service.delete_wechat_account(id):
            return jsonify({'message': '删除成功'}), 200
        else:
            return jsonify({'error': '公众号未找到'}), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': '服务器内部错误'}), 500

# === 文章采集 API ===

@wechat_bp.route('/api/accounts/<int:id>/collect', methods=['POST'])
def collect_articles(id):
    """触发指定公众号的单页文章采集"""
    try:
        saved_count = wechat_service.collect_articles_for_account(id)
        return jsonify({
            'message': f'采集成功，新增 {saved_count} 篇文章。'
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'采集失败: {str(e)}'}), 500

@wechat_bp.route('/api/accounts/<int:id>/collect-all', methods=['POST'])
def collect_all_articles(id):
    """触发后台全量采集任务"""
    try:
        app = current_app._get_current_object()
        wechat_service.start_full_collection_task(id, app)
        return jsonify({'message': '后台全量采集任务已启动'}), 202
    except ValueError as e:
        return jsonify({'error': str(e)}), 409 # 409 Conflict for already running task
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'任务启动失败: {str(e)}'}), 500

@wechat_bp.route('/api/accounts/collect-status', methods=['GET'])
def get_all_tasks_status():
    """获取所有采集任务的状态"""
    return jsonify(wechat_service.collection_tasks)


# === 文章展示 API ===

@wechat_bp.route('/api/articles', methods=['GET'])
def get_articles():
    """获取文章列表（支持分页、搜索、筛选）"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', None)
        account_id = request.args.get('account_id', None, type=int)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        is_downloaded = request.args.get('is_downloaded', None)

        articles, total = wechat_service.get_paginated_articles(
            page=page,
            per_page=per_page,
            search=search,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            is_downloaded=is_downloaded
        )

        current_app.logger.info(f"get_articles: Found {total} total articles.")
        # current_app.logger.info(f"get_articles: Articles on this page: {[a.to_dict() for a in articles]}")
        
        return jsonify({
            'articles': [article.to_dict() for article in articles],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': '服务器内部错误'}), 500

# === 文章下载 API ===

@wechat_bp.route('/api/articles/download', methods=['POST'])
def download_articles():
    """触发后台文章下载任务"""
    data = request.json
    article_ids = data.get('article_ids')
    if not article_ids or not isinstance(article_ids, list):
        return jsonify({'error': '缺少或无效的 article_ids 参数'}), 400
    
    try:
        app = current_app._get_current_object()
        task_id = wechat_service.start_download_task(article_ids, app)
        return jsonify({'message': '后台下载任务已启动', 'task_id': task_id}), 202
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'任务启动失败: {str(e)}'}), 500

@wechat_bp.route('/api/articles/download/status', methods=['GET'])
def get_download_status():
    """获取所有下载任务的状态"""
    return jsonify(wechat_service.get_all_download_tasks_status())
