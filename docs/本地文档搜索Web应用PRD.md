# 本地文档搜索Web应用 - 产品需求文档 (PRD)

## 1. 产品概述

### 1.1 产品名称

本地文档搜索Web应用 (Local Document Search Web Application)

### 1.2 产品描述

一个基于Web的本地文档管理和搜索系统，能够自动将指定时间范围内变化的文档转换为Markdown格式并存储到数据库中，提供高效的全文搜索功能。

### 1.3 目标

提供一个本地运行的 Web 应用：

1. 递归扫描指定文件夹，根据文件变化时间筛选文件；
2. 将所有符合条件的文件统一转换为Markdown格式并存入PostgreSQL数据库；
3. 通过统一的Markdown格式实现高效的全文搜索，并为AI Agent提供结构化的上下文信息；
4. 在 Web 页面中通过关键词搜索 Markdown 全文，并展示搜索结果及原始文件链接。





## 2. 功能需求

### 2.1 文件处理模块

**目标：**

提供一个Web页面，用户可以通过该页面选择一个本地文件夹并指定一个日期范围。应用将扫描该文件夹及其子文件夹，找到在指定日期范围内修改过的文件以及指定的文件类型的文件，将其内容转换为Markdown格式，并存储到数据库中。

**详细需求：**

| 功能点        | 描述                                                         |
| ------------- | ------------------------------------------------------------ |
| 递归扫描      | 选择文件夹后，自动递归扫描所有子文件夹中的文件。             |
| 文件时间过滤  | 支持根据文件的“修改时间”过滤，仅处理在指定日期范围内修改的文件。 |
| 文件类型过滤  | 1. 文件类型的获取遵循优先级：**前端传参 > 后端默认配置**。<br />2. 前端扫描接口可通过 `file_types` 参数传递文件类型，逗号分隔；<br />3. 如果前端未传递，后端将使用 `.env` 文件中的 `SUPPORTED_FILE_TYPES` 作为默认值。 |
| 扫描触发      | 提供一个按钮（例如：“开始扫描”），用户点击后手动触发文件扫描和转换过程。 |
| Markdown 转换 | 1. **Markdown文件**：原生Markdown文件（.md）直接读取内容存储；<br />2. **纯文本转Markdown**：对于TXT文件，添加文件信息头后保持原始文本格式，便于自然语言搜索和AI理解；<br />3. **代码文件转Markdown**：对于代码文件（.py、.js、.sql等），包装为相应语言的Markdown代码块；<br />4. **结构化文档转Markdown**：对于HTML、Office文档、PDF等，使用`markitdown`库转换为标准Markdown格式；<br />5. 对无法转换的文件记录错误信息到`conversion_errors`表。 |
| 数据库存储    | 将 Markdown 内容及文件元信息存入 PostgreSQL：文件名、文件类型、文件大小（字节为单位）、文件创建时间、文件最后修改时间、原始文件绝对路径（跨平台兼容）、转换后的 Markdown 内容、是否转换。 |
| 增量更新      | 如果数据库中已存在该文件且修改时间未变，则不重复转换和存储。 |

**用户流程：**

1. 用户在 Web 页面选择文件夹路径（支持手动输入）。
2. 选择文件修改时间范围（起始日期、结束日期）。
3. 系统扫描文件夹，过滤符合条件的文件并显示扫描统计。
4. 对每个文件执行 Markdown 转换并存储到数据库。
5. 页面展示本次处理的文件数量和耗时统计。



### 2.2 搜索与展示模块

**目标：**

提供一个Web页面，用户可以通过关键词搜索数据库中已转换的Markdown内容。搜索结果应分页显示，并提供预览功能和原始文件链接。

**详细需求：**

| 功能点       | 描述                                                         |
| ------------ | ------------------------------------------------------------ |
| 搜索框       | 用户输入关键词后，系统进行模糊匹配与全文检索。               |
| 检索方式     | 使用 PostgreSQL `tsvector` 实现全文检索，并结合 `ILIKE` 实现模糊匹配。 |
| 结果列表     | 1.以列表形式展示搜索到的结果；<br />2.每个结果条目需包含以下信息：**文件名**、**文件类型**、**修改日期**、**文件大小**、**原始文件路径**；<br />3.显示匹配关键词的**内容摘要**，并高亮关键词。 |
| Markdown预览 | 当用户点击某个搜索结果时，在同一页面的弹出Modal中显示完整的、渲染后的Markdown内容预览。 |
| 原始文件打开 | 1.点击文件链接后，直接在浏览器中打开该文件；<br />2.如果浏览器不支持该文件格式，使用系统中的应用打开该文件；<br />3.如果本地路径无法直接访问，则通过 Flask 提供文件下载接口。 |
| 分页展示     | 每页默认显示 20 条结果，可在前端自定义切换为 20/50/100 条。  |

**用户流程：**

1. 用户在搜索框中输入关键词。
2. 系统执行数据库查询，返回结果列表。
3. 用户点击文件名，，在弹出框中打开Markdown预览。
4. 用户点击原始文件链接，即可打开原始文件。





## 3. 技术架构

### 3.1 技术栈

- **后端**：Flask (Python 3.12+)
- **前端**：原生JavaScript, HTML5 , Tailwind CSS (CDN)
- **数据库**：PostgreSQL 17
- **ORM**：SQLAlchemy
- **文件转换**：markitdown
- **配置管理**：python-dotenv



### 3.2 系统架构

```
用户界面层 (Frontend)
┌─────────────────────────────────────┐
│  HTML5 + JavaScript + Tailwind CSS │
└─────────────────┬───────────────────┘
                  │ HTTP/AJAX
应用服务层 (Backend)
┌─────────────────┴───────────────────┐
│         Flask Application           │
│  ┌─────────────┬─────────────────┐  │
│  │   Routes    │    Services     │  │
│  │ (API层)     │   (业务逻辑层)    │  │
│  └─────────────┴─────────────────┘  │
└─────────────────┬───────────────────┘
                  │ SQLAlchemy ORM
数据存储层 (Database)
┌─────────────────┴───────────────────┐
│         PostgreSQL Database        │
│   (文档内容 + 全文搜索索引)          │
└─────────────────────────────────────┘
```





## 4. 数据库设计

### 4.1 文档表 (documents)

| 字段名                 | 数据类型     | 约束/默认值               | 描述                                                         |
| ---------------------- | ------------ | ------------------------- | ------------------------------------------------------------ |
| **id**                 | SERIAL       | PRIMARY KEY               | 主键，自增                                                   |
| **file_name**          | VARCHAR(200) | NOT NULL                  | 文件名                                                       |
| **file_type**          | VARCHAR(50)  | NULL                      | 文件类型扩展名                                               |
| **file_size**          | BIGINT       | NULL                      | 文件大小，单位：字节                                         |
| **file_created_at**    | TIMESTAMP    | NULL                      | 文件创建时间                                                 |
| **file_modified_time** | TIMESTAMP    | NULL                      | 文件最后修改时间                                             |
| **file_path**          | TEXT         | NOT NULL                  | 文件绝对路径（跨平台存储统一为/分隔符）                      |
| **markdown_content**   | TEXT         | NULL                      | 转换后的 Markdown 内容                                       |
| **is_converted**       | INTEGER      | NULL                      | 文件处理方式：0-直接存储，1-文本转Markdown，2-代码转Markdown，3-结构化转Markdown，4-转换失败 |
| **search_vector**      | TSVECTOR     | NULL                      | 全文搜索向量                                                 |
| **created_at**         | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP | 记录创建时间                                                 |
| **updated_at**         | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP | 记录最后更新时间                                             |

**索引设计：**

- 在filepath字段上创建唯一索引 idx_documents_file_path，用于判断文件是否重复。
- 在content_markdown字段上创建全文搜索索引 idx_documents_search_vector (使用PostgreSQL的GIN索引)，用于加速全文检索。

**索引语句：**

```sql
CREATE UNIQUE INDEX idx_documents_file_path ON documents(file_path);
CREATE INDEX idx_documents_search_vector ON documents USING gin(search_vector);
```



### 4.2 转换失败记录表 (conversion_errors)

| 字段名            | 数据类型     | 约束/默认值               | 描述                                    |
| ----------------- | ------------ | ------------------------- | --------------------------------------- |
| **id**            | SERIAL       | PRIMARY KEY               | 主键，自增                              |
| **file_name**     | VARCHAR(200) | NOT NULL                  | 文件名                                  |
| **file_path**     | TEXT         | NOT NULL                  | 文件绝对路径（跨平台存储统一为/分隔符） |
| **error_message** | TEXT         | NULL                      | 全文搜索向量                            |
| **created_at**    | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP | 记录创建时间                            |
| **updated_at**    | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP | 记录最后更新时间                        |





## 5. API设计

### 5.1 文档处理API

#### POST /api/scan-folder

**功能：** 扫描指定文件夹并处理文件

**请求参数：**

```json
{
  "folder_path": "/path/to/folder",
  "date_from": "2024-01-01",
  "date_to": "2024-12-31",
  "recursive": true,
  "file_types": "pdf,docx,xlsx,pptx,html"
}
```

> `file_types` 通过逗号分隔字符串传参，后端解析为数组。



**响应示例**：

```json
{
  "status": "success",
  "message": "文件扫描完成",
  "data": {
    "scan_summary": {
      "total_files": 150,
      "filtered_files": 120,
      "processed_files": 115,
      "skipped_files": 5,
      "error_files": 0
    },
    "processing_time": "2.3s",
    "start_time": "2024-01-15T10:00:00Z",
    "end_time": "2024-01-15T10:00:02Z"
  }
}
```



### 5.2 搜索API

#### GET /api/search

**功能**：搜索文档内容
**请求参数**：

| 参数名      | 类型    | 必需 | 默认值      | 描述                                       |
| ----------- | ------- | ---- | ----------- | ------------------------------------------ |
| keyword     | string  | 是   | -           | 搜索关键词（支持布尔操作符）               |
| search_type | string  | 否   | "simple"    | 搜索类型: simple/advanced/fuzzy            |
| sort_by     | string  | 否   | "relevance" | 排序方式: relevance/modified_time/filename |
| sort_order  | string  | 否   | "desc"      | 排序顺序: asc/desc                         |
| page        | integer | 否   | 1           | 页码                                       |
| per_page    | integer | 否   | 20          | 每页结果数                                 |
| file_types  | string  | 否   | []          | 文件类型筛选，多个类型逗号分隔             |
| date_from   | string  | 否   | -           | 开始日期 (YYYY-MM-DD)                      |
| date_to     | string  | 否   | -           | 结束日期 (YYYY-MM-DD)                      |

**响应示例**：

```json
{
  "status": "success",
  "data": {
    "search_info": {
      "keyword": "项目报告",
      "search_type": "advanced",
      "sort_by": "relevance",
      "total_results": 25,
      "search_time": "0.15s"
    },
    "results": [
      {
        "id": 1,
        "filename": "2024年度项目报告.docx",
        "filepath": "/home/user/documents/2024年度项目报告.docx",
        "filetype": "docx",
        "filesize": 102400,
        "file_modified_time": "2024-01-15T10:30:00Z",
        "snippet": "这是包含<mark>项目报告</mark>的文档片段，介绍了本年度的主要工作成果...",
        "relevance_score": 0.85
      }
    ],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total_pages": 2,
      "has_next": true,
      "has_prev": false
    }
  }
}
```





### 5.3 获取文件类型配置API

#### GET /api/config/file-types

**功能**：返回当前系统支持的文件类型分类信息。

**响应示例**：
```json
{
  "status": "success",
  "data": {
    "native_markdown_types": [
      {"ext": "md", "name": "Markdown文件", "process": "直接存储"}
    ],
    "code_to_markdown_types": [
      {"ext": "py", "name": "Python脚本", "process": "转为代码块"},
      {"ext": "js", "name": "JavaScript", "process": "转为代码块"},
      {"ext": "sql", "name": "SQL脚本", "process": "转为代码块"},
      {"ext": "css", "name": "CSS样式", "process": "转为代码块"},
      {"ext": "json", "name": "JSON配置", "process": "转为代码块"}
    ],
    "structured_to_markdown_types": [
      {"ext": "html", "name": "HTML网页", "process": "markitdown转换"},
      {"ext": "pdf", "name": "PDF文档", "process": "markitdown转换"},
      {"ext": "docx", "name": "Word文档", "process": "markitdown转换"},
      {"ext": "pptx", "name": "PowerPoint演示", "process": "markitdown转换"},
      {"ext": "xlsx", "name": "Excel表格", "process": "markitdown转换"}        
    ],
    "conversion_info": {
      "target_format": "Markdown",
      "ai_agent_ready": true,
      "unified_search": true
    }
  }
}
```





### **5.5 Markdown预览API**

#### GET /api/preview/markdown/<document_id>

**功能：** 从数据库中获取指定文档的Markdown内容，供前端Modal中展示。

**请求参数：**`document_id`：文档ID（URL路径参数）

**响应示例**：

```
{
  "status": "success",
  "data": {
    "id": 1,
    "file_name": "2024年度项目报告.docx",
    "file_type": "docx",
    "file_size": 102400,
    "file_modified_time": "2024-01-15T10:30:00Z",
    "markdown_content": "# 2024年度项目报告\n这是文档的Markdown内容...",
    "rendered_html": "<h1>2024年度项目报告</h1><p>这是文档的Markdown内容...</p>"
  }
}
```

**错误响应**：

```
{
  "status": "error",
  "message": "文档不存在或已被删除"
}
```







## 6. 用户界面设计

### 6.1 文档处理页面 (/process)

**目标：** 简洁直观的文档处理界面

**页面标题**：文档处理与导入

**主要元素**：

- 文件夹路径输入框
- 递归扫描选项
- 日期范围选择器
- 文件类型设置（文件类型复选框，根据 `/api/config/file-types` 接口动态生成）
- 开始处理按钮
- 处理进度显示区域
- 处理结果统计

**页面布局示例：**

```
┌─────────────────────────────────────────────────┐
│                    导航栏                         │
├─────────────────────────────────────────────────┤
│                  文档处理与导入                    │
├─────────────────────────────────────────────────┤
│  文件夹设置                                      │
│  ┌─────────────────────────────────────────┐     │
│  │ 文件夹路径: [/path/to/folder       ] [浏览]│     │
│  │ □ 递归扫描子文件夹                       	│     │
│  └─────────────────────────────────────────┘     │
│                                                 │
│  时间范围设置                                    │
│  ┌─────────────────────────────────────────┐     │
│  │ 开始日期: [2024-01-01] 结束日期: [2024-12-31] │  │
│  └─────────────────────────────────────────┘     │
│                                                 │
│  文件类型设置                                    │
│  ┌─────────────────────────────────────────┐     │
│  │                                        │     │
│  │ 结构化文档：（markitdown转换）           │     │
│  │ ☑ HTML  ☑ PDF  ☑ Word  ☑ Excel       │     │
│  │ ☑ PowerPoint  ☑ RTF                   │     │
│  │                                        │     │
│  │ 代码文件：（转为Markdown代码块）           │     │
│  │ ☑ Python  ☑ JavaScript  ☑ SQL  ☑ CSS   │     │
│  │ ☑ JSON  ☑ XML  ☑ YAML                 │     │
│  │                                        │     │
│  └─────────────────────────────────────────┘     │
│                                                 │
│  ┌─────────────┐                               │
│  │ 开始处理    │                               │
│  └─────────────┘                               │
│                                                 │
│  处理进度                                        │
│  ┌─────────────────────────────────────────┐     │
│  │ ████████████████░░░░ 80% (96/120)        │     │
│  │ 当前文件: /path/to/current/file.pdf        │     │
│  │ 已处理: 96  跳过: 2  错误: 0              │     │
│  └─────────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```



### 6.2 文档搜索页面 (/search)

**目标：** 强大而友好的搜索体验

**页面标题**：文档搜索

**主要元素**：

- 搜索输入框
- 高级搜索选项（可折叠）
- 搜索结果列表
- Markdown 预览（Markdown 预览在同一页面通过 Modal 弹出框展示）
- 分页导航
- 搜索统计信息

**页面布局示例：**

```
┌─────────────────────────────────────────────────┐
│                    导航栏                         │
├─────────────────────────────────────────────────┤
│                    文档搜索                       │
├─────────────────────────────────────────────────┤
│  搜索框                                          │
│  ┌─────────────────────────────────────────┐     │
│  │ 🔍 [搜索关键词...              ] [搜索]   │     │
│  └─────────────────────────────────────────┘     │
│                                                 │
│  高级选项 ▼                                     │
│  ┌─────────────────────────────────────────┐     │
│  │ 排序: [相关度▼] 每页: [20▼] 文件类型: [全部▼] │    │
│  │ 时间范围: [2024-01-01] 至 [2024-12-31]    │    │
│  └─────────────────────────────────────────┘     │
│                                                 │
│  搜索结果 (共25条，用时0.15秒)                   │
│  ┌─────────────────────────────────────────┐     │
│  │ 📄 2024年度项目报告.docx  相关度: 85%    │     │
│  │    /home/user/documents/2024年度项目报告.docx │    │
│  │    这是包含项目报告的文档片段，介绍了...     │     │
│  │    修改时间: 2024-01-15 10:30  大小: 1MB   │    │
│  │    [打开文件]                  │     │
│  ├─────────────────────────────────────────┤     │
│  │ 📊 数据分析报告.xlsx  相关度: 72%        │     │
│  │    /home/user/reports/数据分析报告.xlsx     │     │
│  │    包含详细的数据分析和项目统计信息...     │     │
│  │    修改时间: 2024-01-10 14:20  大小: 1MB   │    │
│  │    [打开文件]                   │     │
│  └─────────────────────────────────────────┘     │
│                                                 │
│  分页控制                                        │
│  ┌─────────────────────────────────────────┐     │
│  │    ◀ 上一页  [1] 2  下一页 ▶             │     │
│  └─────────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```





## 7. 非功能性需求

### 7.1 可维护性需求

- 代码结构清晰，遵循Flask最佳实践
- 详细的错误日志记录
- 配置项通过环境变量管理



### 7.2 兼容性需求

- 支持 Windows 和 Linux 操作系统，路径存储统一使用 `/` 分隔符。



### 7.3 安全性需求

- 输入验证：对用户输入的文件路径进行安全验证
- SQL注入防护（通过ORM实现）





## 8. 部署和配置

### 8.1 环境配置文件 (.env)

```
# 数据库连接
DATABASE_URL=postgresql://demo:demo@localhost:5432/document_search


# Flask 环境
FLASK_ENV=development
FLASK_SECRET_KEY=your-secret-key


# 文件类型配置（逗号分隔，不区分大小写）
# 原生Markdown文件（直接存储）
NATIVE_MARKDOWN_TYPES=md

# 纯文本文档（直接转为Markdown格式）
PLAIN_TEXT_TO_MARKDOWN_TYPES=txt

# 代码文件类型（转换为Markdown代码块）
CODE_TO_MARKDOWN_TYPES=sql,py

# 日志文件（转换为代码块，便于格式化显示）
LOG_TO_MARKDOWN_TYPES=log

# 结构化文档类型（使用markitdown转换为Markdown）
STRUCTURED_TO_MARKDOWN_TYPES=html,htm,pdf,docx,xlsx,pptx

# 所有支持的文件类型
SUPPORTED_FILE_TYPES=md,html,htm,pdf,docx,xlsx,pptx,sql,py
```





## 9. 项目结构

```
local_document_search/
│
├── app/                        # 应用主目录
│   ├── __init__.py              # Flask 应用工厂
│   ├── extensions.py            # 第三方扩展初始化（db, migrate, etc.）
│   ├── models.py                # 数据模型（SQLAlchemy ORM）
│   ├── config.py                # 配置文件（从 .env 读取）
│   ├── routes/                  # 路由层（蓝图）
│   │   ├── __init__.py
│   │   ├── convert.py           # 文件夹选择与转换 API
│   │   └── search.py            # 搜索 API
│   ├── services/                # 业务逻辑层（与视图解耦）
│   │   ├── __init__.py
│   │   ├── file_scanner.py      # 扫描文件夹、过滤日期范围
│   │   ├── converter.py         # markitdown 转换逻辑
│   │   └── search_service.py    # 全文搜索逻辑
│   ├── templates/               # Jinja2 模板（前端页面）
│   │   ├── base.html
│   │   ├── convert.html		 # 文档处理页面
│   │   └── search.html			 # 文档搜索页面
│   ├── static/                  # 静态文件（JS、CSS、图片）
│   │   ├── js/
│   │   └── css/
│   └── utils/                   # 工具函数
│       ├── __init__.py
│       └── file_utils.py        # 文件路径、时间戳处理
├── migrations/                  # 数据库迁移文件（Flask-Migrate 自动生成）
├── tests/                       # 单元测试
│   ├── __init__.py
│   ├── test_convert.py
│   └── test_search.py
├── scripts/                    # 项目管理脚本
│   └── init_db.py              # 数据库初始化脚本
├── logs/                         # 日志文件目录
├── .env                          # 环境变量（数据库连接等）
├── .gitignore                    # Git忽略文件
├── requirements.txt              # Python 依赖
├── run.py                        # 开发启动入口
└── README.md
```





## 10. 后续优化方向

- 支持定时任务自动扫描文件夹。
- 实现搜索结果导出（支持CSV、JSON格式）。
- 扩展专业格式支持：
  - .drawio (Draw.io图表) - 提取文本和结构信息
  - .xmind (XMind思维导图) - 转换为Markdown层级结构
  - .vsd/.vsdx (Visio图表)
- 使用PostgreSQL的扩展pg_search进行更大规模的全文检索。
