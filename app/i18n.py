from flask import g

_TRANSLATIONS = {
    "zh": {
        "app.brand": "DocSearch",
        "nav.search": "文档检索",
        "nav.import": "文档导入",
        "nav.errors": "错误记录",
        "nav.cleanup": "清理索引",
        "nav.wechat.group": "采集公众号文章",
        "nav.wechat.management": "公众号管理",
        "nav.wechat.articles": "文章列表",
        "sidebar.collapse": "折叠",
        "page.import.title": "文档导入",
        "import.scan.settings": "扫描设置",
        "import.scan.settings.desc": "配置要处理的目录路径与过滤条件",
        "import.folder_path": "目录路径",
        "import.browse": "浏览",
        "import.recursive": "递归扫描",
        "import.recursive.desc": "扫描所有子目录",
        "import.modified_after": "修改时间不早于",
        "import.modified_before": "修改时间不晚于",
        "import.file_types": "文件类型",
        "import.file_types.select_all": "全选",
        "import.file_types.deselect_all": "全不选",
        "import.file_types.invert": "反选",
        "import.start": "开始导入",
        "import.start.processing": "处理中...",
        "import.stop": "停止",
        "import.stop_all": "全部停止",
        "import.log.title": "处理日志",
        "import.progress.initializing": "初始化...",
        "import.progress.cancel_ack": "取消请求已收到",
        "import.progress.cancelled": "已取消",
        "import.progress.completed": "已完成",
        "import.summary.final": "汇总",
        "import.summary.total": "总文件数",
        "import.summary.processed": "已处理",
        "import.summary.skipped": "已跳过",
        "import.summary.errors": "错误",
        "import.summary.duration": "耗时",
        "import.placeholder.select_folder": "请选择（或输入）需要导入的目录路径",
        "import.alert.no_folder": "请先选择目录。",
    "import.recent.title": "最近使用目录",
    "import.recent.empty": "暂无历史",
    "import.recent.clear": "清空历史",
    "import.recent.remove": "移除",
    "import.input.clear": "清空",
        "events.connection_established": "连接已建立，开始处理...",
        "events.cancel_ack": "收到取消确认。",
        "events.cancelled": "任务已取消。",
        "events.stop_requested": "已发送停止请求，等待当前文件完成...",
        "events.stop_failed": "停止请求失败",
        "events.stop_error": "停止请求出错",
        "events.stop_all_requested": "已发送批量停止请求。会话: ",
        "events.stop_all_failed": "批量停止失败",
        "events.stop_all_error": "批量停止请求出错",
        "events.stream_lost": "与服务器的连接丢失，请检查后端服务。",
        "lang.toggle": "English",
    "import.directory_label": "文件夹：",
        "search.page.title": "文档检索",
        "search.title": "文档检索",
        "search.placeholder.keyword": "输入关键词后回车...",
        "search.button.search": "搜索",
        "search.dropdown.file_types": "文件类型",
        "search.file_types.clear": "清空",
        "search.file_types.apply": "应用",
        "search.filters.all_conversion_types": "全部转换类型",
        "search.filters.all_sources": "全部来源",
        "search.results.enter_query": "输入查询以查看结果。",
        "search.results.searching": "检索中...",
        "search.results.loading": "加载中...",
        "search.results.none": "没有结果。",
        "search.results.none_for": "没有找到匹配结果：{keyword}",
        "search.results.failed": "检索失败。",
        "search.results.error": "检索时发生错误。",
        "search.results.summary": "找到 {count} 条结果，用时 {time}。",
        "search.preview.loading": "预览加载中...",
        "search.preview.error": "获取预览时发生错误。",
        "search.open_file": "打开文件",
        "search.result.source": "来源",
        "search.result.modified": "修改时间",
        "search.result.size": "大小",
        "search.result.type": "类型",
        "search.result.path": "路径",
        "pagination.prev": "上一页",
        "pagination.next": "下一页",
        "errors.title": "错误记录",
        "errors.filter.title": "筛选",
        "errors.filter.file_name": "文件名",
        "errors.filter.from": "开始日期",
        "errors.filter.to": "结束日期",
        "errors.filter.button.filter": "筛选",
        "errors.filter.button.reset": "重置",
        "errors.table.file_name": "文件名",
        "errors.table.file_path": "路径",
        "errors.table.error_message": "错误信息",
        "errors.table.date": "日期",
        "errors.table.actions": "操作",
        "errors.action.retry": "重试",
        "errors.action.retrying": "重试中...",
        "errors.empty.title": "暂无错误",
        "errors.empty.desc": "没有符合条件的错误记录。",
        "errors.date.na": "无",
        "errors.retry.failed_prefix": "重试失败:",
    "errors.unexpected_error": "出现意外错误。"
    ,"import.conv.native_markdown": "Markdown"
    ,"import.conv.plain_text_to_markdown": "文本"
    ,"import.conv.code_to_markdown": "代码"
    ,"import.conv.xmind_to_markdown": "思维导图"
    ,"import.conv.structured_to_markdown": "Office/PDF"
    ,"import.conv.html_to_markdown": "HTML"
    ,"import.conv.image_to_markdown": "图片"
    ,"import.conv.video_to_markdown": "音视频"
    ,"import.conv.drawio_to_markdown": "draw.io"
    ,"import.conv.target_format": "目标格式"
    ,"import.conv.ai_agent_ready": "AI Agent 预处理已启用"
    ,"import.conv.unified_search": "统一搜索支持已启用"
    ,"import.conv.conversion_types": "转换类型"
    ,"cleanup.title": "清理索引"
    ,"cleanup.section.compare": "文件对比"
    ,"cleanup.section.compare.desc": "输入一个文件夹的绝对路径，找出数据库中多余的记录。"
    ,"cleanup.form.folder.label": "要检查的文件夹路径"
    ,"cleanup.form.folder.placeholder": "例如: E:\\documents\\my_project"
    ,"cleanup.button.start": "开始对比"
    ,"cleanup.section.filter": "筛选记录"
    ,"cleanup.filter.file_type": "文件类型"
    ,"cleanup.filter.file_type.all": "所有类型"
    ,"cleanup.filter.path_keyword": "文件路径 (关键词)"
    ,"cleanup.filter.path_keyword.placeholder": "例如: archive 或 test"
    ,"cleanup.button.filter": "筛选"
    ,"cleanup.stats.found": "发现 {count} 个孤儿文件记录。"
    ,"cleanup.button.delete_selected": "删除选中 ( {count} )"
    ,"cleanup.table.path": "文件路径"
    ,"cleanup.table.type": "文件类型"
    ,"cleanup.table.created_at": "入库时间"
    ,"cleanup.empty.ok_title": "太棒了！"
    ,"cleanup.empty.ok_desc": "在此文件夹下未发现任何孤儿文件记录。"
    ,"cleanup.empty.ready_title": "准备开始"
    ,"cleanup.empty.ready_desc": "请输入一个文件夹路径并点击“开始对比”以查找孤儿文件。"
    ,"cleanup.alert.select_none": "请至少选择一个要删除的文件记录。"
    ,"cleanup.confirm.delete": "您确定要从数据库中删除这 {count} 条文件记录吗？此操作不可恢复。"
    ,"cleanup.error.delete_failed_prefix": "删除失败:"
    ,"cleanup.error.network": "删除过程中发生网络或服务器错误。"
    ,"cleanup.flash.delete_success": "成功删除了 {count} 条孤儿文件记录。"
    ,"cleanup.api.no_ids": "没有提供要删除的文档ID。"
    ,"cleanup.api.deleted": "成功删除了 {count} 条记录。"
    ,"cleanup.api.delete_error_prefix": "删除过程中发生错误: "
    },
    "en": {
        "app.brand": "DocSearch",
        "nav.search": "Search",
        "nav.import": "Document Import",
        "nav.errors": "Error Records",
        "nav.cleanup": "Cleanup",
        "nav.wechat.group": "WeChat Articles",
        "nav.wechat.management": "Account Management",
        "nav.wechat.articles": "Article List",
        "sidebar.collapse": "Collapse",
        "page.import.title": "Document Import",
        "import.scan.settings": "Scan Settings",
        "import.scan.settings.desc": "Configure folder path and filters for document processing.",
        "import.folder_path": "Folder Path",
        "import.browse": "Browse",
        "import.recursive": "Recursive Scan",
        "import.recursive.desc": "Scan all subdirectories.",
        "import.modified_after": "Modified After",
        "import.modified_before": "Modified Before",
        "import.file_types": "File Types",
        "import.file_types.select_all": "Select All",
        "import.file_types.deselect_all": "Deselect All",
        "import.file_types.invert": "Invert",
        "import.start": "Start Processing",
        "import.start.processing": "Processing...",
        "import.stop": "Stop",
        "import.stop_all": "Stop All",
        "import.log.title": "Processing Log",
        "import.progress.initializing": "Initializing...",
        "import.progress.cancel_ack": "Cancel request acknowledged",
        "import.progress.cancelled": "Cancelled",
        "import.progress.completed": "Completed",
        "import.summary.final": "Final Summary",
        "import.summary.total": "Total Files",
        "import.summary.processed": "Processed",
        "import.summary.skipped": "Skipped",
        "import.summary.errors": "Errors",
        "import.summary.duration": "Duration",
        "import.placeholder.select_folder": "Select or input a folder path",
        "import.alert.no_folder": "Please select a folder path first.",
    "import.recent.title": "Recent Directories",
    "import.recent.empty": "No history",
    "import.recent.clear": "Clear History",
    "import.recent.remove": "Remove",
    "import.input.clear": "Clear",
        "events.connection_established": "Connection established. Starting process...",
        "events.cancel_ack": "cancel_ack received.",
        "events.cancelled": "cancelled event received.",
        "events.stop_requested": "Stop requested. Waiting for current file to finish...",
        "events.stop_failed": "Stop request failed",
        "events.stop_error": "Stop request error",
        "events.stop_all_requested": "Stop-All requested. Sessions: ",
        "events.stop_all_failed": "Stop-All failed",
        "events.stop_all_error": "Stop-All request error",
        "events.stream_lost": "Connection to server lost. Please check backend.",
        "lang.toggle": "中文",
    "import.directory_label": "Folder:",
        "search.page.title": "Document Search",
        "search.title": "Document Search",
        "search.placeholder.keyword": "Enter keywords and press Enter...",
        "search.button.search": "Search",
        "search.dropdown.file_types": "File Types",
        "search.file_types.clear": "Clear",
        "search.file_types.apply": "Apply",
        "search.filters.all_conversion_types": "All Conversion Types",
        "search.filters.all_sources": "All Sources",
        "search.results.enter_query": "Enter a query to see results.",
        "search.results.searching": "Searching...",
        "search.results.loading": "Loading results...",
        "search.results.none": "No results.",
        "search.results.none_for": "No results found for {keyword}.",
        "search.results.failed": "Search failed.",
        "search.results.error": "An error occurred during search.",
        "search.results.summary": "Found {count} results in {time}.",
        "search.preview.loading": "Loading preview...",
        "search.preview.error": "An error occurred while fetching the preview.",
        "search.open_file": "Open File",
        "search.result.source": "Source",
        "search.result.modified": "Modified",
        "search.result.size": "Size",
        "search.result.type": "Type",
        "search.result.path": "Path",
        "pagination.prev": "Prev",
        "pagination.next": "Next",
        "errors.title": "Conversion Error Records",
        "errors.filter.title": "Filter Errors",
        "errors.filter.file_name": "File Name",
        "errors.filter.from": "From",
        "errors.filter.to": "To",
        "errors.filter.button.filter": "Filter",
        "errors.filter.button.reset": "Reset",
        "errors.table.file_name": "File Name",
        "errors.table.file_path": "File Path",
        "errors.table.error_message": "Error Message",
        "errors.table.date": "Date",
        "errors.table.actions": "Actions",
        "errors.action.retry": "Retry",
        "errors.action.retrying": "Retrying...",
        "errors.empty.title": "No Errors Found",
        "errors.empty.desc": "No errors match your current filter criteria.",
        "errors.date.na": "N/A",
        "errors.retry.failed_prefix": "Retry failed:",
    "errors.unexpected_error": "An unexpected error occurred."
    ,"import.conv.native_markdown": "Native Markdown"
    ,"import.conv.plain_text_to_markdown": "Plain Text"
    ,"import.conv.code_to_markdown": "Code"
    ,"import.conv.xmind_to_markdown": "Xmind"
    ,"import.conv.structured_to_markdown": "Office/PDF"
    ,"import.conv.html_to_markdown": "HTML"
    ,"import.conv.image_to_markdown": "Image"
    ,"import.conv.video_to_markdown": "Video"
    ,"import.conv.drawio_to_markdown": "Draw.io"
    ,"import.conv.target_format": "Target Format"
    ,"import.conv.ai_agent_ready": "AI Agent Preprocessing Enabled"
    ,"import.conv.unified_search": "Unified Search Supported"
    ,"import.conv.conversion_types": "Conversion Types"
    ,"cleanup.title": "Cleanup Orphan Files"
    ,"cleanup.section.compare": "Compare Files"
    ,"cleanup.section.compare.desc": "Enter an absolute folder path to find extra records in the database."
    ,"cleanup.form.folder.label": "Folder Path to Check"
    ,"cleanup.form.folder.placeholder": "e.g. E:\\documents\\my_project"
    ,"cleanup.button.start": "Start Compare"
    ,"cleanup.section.filter": "Filter Records"
    ,"cleanup.filter.file_type": "File Type"
    ,"cleanup.filter.file_type.all": "All Types"
    ,"cleanup.filter.path_keyword": "File Path (Keyword)"
    ,"cleanup.filter.path_keyword.placeholder": "e.g. archive or test"
    ,"cleanup.button.filter": "Filter"
    ,"cleanup.stats.found": "Found {count} orphan file records."
    ,"cleanup.button.delete_selected": "Delete Selected ( {count} )"
    ,"cleanup.table.path": "File Path"
    ,"cleanup.table.type": "File Type"
    ,"cleanup.table.created_at": "Created At"
    ,"cleanup.empty.ok_title": "Great!"
    ,"cleanup.empty.ok_desc": "No orphan file records found under this folder."
    ,"cleanup.empty.ready_title": "Get Ready"
    ,"cleanup.empty.ready_desc": "Input a folder path and click 'Start Compare' to find orphan files."
    ,"cleanup.alert.select_none": "Please select at least one record to delete."
    ,"cleanup.confirm.delete": "Are you sure you want to delete these {count} records from the database? This action cannot be undone."
    ,"cleanup.error.delete_failed_prefix": "Delete failed:"
    ,"cleanup.error.network": "A network or server error occurred during deletion."
    ,"cleanup.flash.delete_success": "Successfully deleted {count} orphan file records."
    ,"cleanup.api.no_ids": "No document IDs provided for deletion."
    ,"cleanup.api.deleted": "Successfully deleted {count} records."
    ,"cleanup.api.delete_error_prefix": "An error occurred during deletion: "
    }
}

def supported_lang(lang: str) -> bool:
    return lang in _TRANSLATIONS

def get_lang() -> str:
    return getattr(g, 'lang', 'zh')

def t(key: str) -> str:
    lang = get_lang()
    return _TRANSLATIONS.get(lang, _TRANSLATIONS['zh']).get(key, key)

__all__ = ['t', 'supported_lang', 'get_lang']
