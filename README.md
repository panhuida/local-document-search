<h1 align="center">🔍本地文档搜索助手</h1>

<p align="center">
  <strong>将本地文档、思维导图、Joplin、公众号文章、图片的内容提取转换成 Markdown 并创建索引进行检索</strong>
</p>

<p align="center">
  <img src="docs\assets\ui.png" alt="主界面">
</p>

**注：这个项目的代码由 AI 生成，README 文档也主要由 AI 生成。**





## 主要功能

- **📁 文件夹扫描**：递归扫描本地文件夹，可根据修改时间 / 文件类型做增量或全量索引。
- **📄 支持常见的文档**：PDF、Word (`.docx`, `.doc` ) 、PPT (`.pptx`, `.ppt`)  、Excel (`.xlsx` , `.xls`)  。
- **🗺️ 支持思维导图与流程图**：XMind、draw.io 。
- **✍️ Joplin 笔记同步**：通过脚本从本地 Joplin 应用的 API 同步笔记 。
- **🧠 多模态增强**：图片 → 本地 OCR / LLM 语义描述（可链式降级 Provider），写入 Front Matter；可扩展视频字幕、关键帧解析。
- **🎬 视频元数据提取**：抽取元数据形成 Markdown，后续可接入字幕/章节/摘要。
- **🚀 高性能全文检索**：利用 PostgreSQL **PGroonga** 扩展，为文档内容和文件名提供高速、精准的全文搜索能力。
- **✍️ 模糊检索**：利用PostgreSQL  **pg_trgm** 扩展，支持文件名和内容的 trigram 模糊匹配，即使有拼写错误也能找到相关结果。
- **🖥️ 简洁易用的 Web 界面**：
    - 提供清晰的搜索页面，支持关键词搜索。
    - 搜索结果列表会生成包含关键词的**内容摘要**并**高亮**显示。
    - 支持点击文件名预览完整的 Markdown 内容。
    - 支持从搜索结果中直接调用系统默认程序打开本地的原始文件。





## 技术栈

- **后端**: Python 3, Flask, SQLAlchemy
- **数据库**: PostgreSQL
- **数据库扩展**: PGroonga (全文检索), pg_trgm (模糊检索)
- **前端**: 原生 HTML, CSS, JavaScript 
- **核心依赖**: 
    - `psycopg2-binary`: PostgreSQL 驱动。
    - `markitdown[all]`: 强大的多格式文件转 Markdown 工具。
    - `python-dotenv`: 用于管理环境变量。
    - `requests`: 用于 API 请求。





## 安装与设置

### 1. 环境准备

- Windows 11

- 确保您已经安装了 Python 3.12+ 和 Git
- 安装并运行 **PostgreSQL** (建议版本 16+)



### 2. 克隆与安装依赖

```bash
# 1. 克隆项目
git clone <your-repository-url>
cd local_document_search

# 2. (可选但推荐) 创建并激活 Python 虚拟环境
python -m venv venv
# Windows: .\venv\Scripts\activate | macOS/Linux: source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
```



### 3. 配置环境变量

项目使用 `.env` 文件管理配置。我们提供了一个模板文件 `.env.example`。

```bash
# 1. 从模板复制配置文件
# Windows
copy .env.example .env
# macOS/Linux
cp .env.example .env

# 2. 编辑 .env 文件，至少修改以下两项：
#    - DATABASE_URL: 修改为您自己的数据库用户名、密码和库名。
#    - JOPLIN_API_TOKEN: 填入您从 Joplin 获取的 API 令牌。
```



### 4. 配置数据库

- 在 PostgreSQL 中创建一个新的数据库（例如，`document_search`）。
- 连接到您刚创建的数据库，并启用 `pg_trgm` 和 `pgroonga` 扩展。您可以使用 `psql` 或任何图形化工具执行以下 SQL 命令：
  ```sql
  CREATE EXTENSION IF NOT EXISTS pg_trgm;
  CREATE EXTENSION IF NOT EXISTS pgroonga;
  ```
  > **重要**: PGroonga 可能需要单独安装。请参考 [PGroonga 官方安装文档](https://pgroonga.github.io/install/) 完成在您操作系统上的安装。



### 5. 初始化数据库

在 PostgreSQL 中创建数据表。

#### 文档搜索数据表

**alembic_version  Flask-Migrate 版本表**

```sql
CREATE TABLE public.alembic_version (
	version_num varchar(32) NOT NULL,
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
```

**ingest_state  同步状态表**

```sql
CREATE TABLE public.ingest_state (
	id serial4 NOT NULL,
	"source" varchar(30) NOT NULL,
	scope_key text NOT NULL,
	last_started_at timestamptz NULL,
	last_ended_at timestamptz NULL,
	last_error_message text NULL,
	cursor_updated_at timestamptz NULL,
	total_files int4 NULL,
	processed int4 NULL,
	skipped int4 NULL,
	errors int4 NULL,
	created_at timestamptz DEFAULT now() NULL,
	updated_at timestamptz NULL,
	CONSTRAINT ingest_state_pkey PRIMARY KEY (id)
);
CREATE UNIQUE INDEX idx_ingest_state_source_scope ON public.ingest_state USING btree (source, scope_key);
```

**documents 文档记录表**

```sql
CREATE TABLE public.documents (
	id serial4 NOT NULL,
	file_name varchar(200) NOT NULL,
	file_type varchar(10) NULL,
	file_size int8 NULL,
	file_created_at timestamptz NULL,
	file_modified_time timestamptz NULL,
	file_path text NOT NULL,
	markdown_content text NULL,
	conversion_type int4 NULL,
	status varchar(10) NULL,
	error_message text NULL,
	created_at timestamptz DEFAULT now() NULL,
	updated_at timestamptz NULL,
	"source" varchar(30) NULL,
	source_url text NULL,
	CONSTRAINT documents_file_path_key UNIQUE (file_path),
	CONSTRAINT documents_pkey PRIMARY KEY (id)
);
CREATE UNIQUE INDEX idx_documents_file_path ON public.documents USING btree (file_path);
CREATE INDEX idx_documents_file_name_gin ON public.documents USING gin (file_name gin_trgm_ops);
CREATE INDEX idx_documents_markdown_content_gin ON public.documents USING gin (markdown_content gin_trgm_ops);
CREATE INDEX idx_pgroonga_markdown_content ON public.documents USING pgroonga (markdown_content);
CREATE INDEX ix_documents_source ON public.documents USING btree (source);
```



#### 采集公众号数据表

**wechat_list  公众号清单表**

```sql
CREATE TABLE public.wechat_list (
	id serial4 NOT NULL,
	wechat_account_name varchar(100) NOT NULL,
	memo varchar(200) NULL,
	start_date date NULL,
	end_date date NULL,
	fakeid varchar(100) NULL,
	"token" varchar(100) NULL,
	cookie text NULL,
	"begin" int4 NULL,
	count int4 NULL,
	create_time timestamptz DEFAULT now() NULL,
	update_time timestamptz DEFAULT now() NULL,
	CONSTRAINT wechat_list_pkey PRIMARY KEY (id)
);
```

**wechat_article_list  公众号文章清单表**

```shell
CREATE TABLE public.wechat_article_list (
	id serial4 NOT NULL,
	wechat_list_id int4 NULL,
	wechat_account_name varchar(100) NULL,
	article_id varchar(100) NULL,
	article_title varchar(255) NULL,
	article_cover varchar(500) NULL,
	article_link varchar(500) NULL,
	article_author_name varchar(100) NULL,
	article_is_deleted varchar(10) NULL,
	is_downloaded varchar(10) NULL,
	article_create_time timestamptz NULL,
	article_update_time timestamptz NULL,
	create_time timestamptz DEFAULT now() NULL,
	update_time timestamptz DEFAULT now() NULL,
	CONSTRAINT wechat_article_list_pkey PRIMARY KEY (id)
);
```



### 6. 启动 Web 应用

在项目根目录下运行：

```bash
python run.py
```

打开浏览器，访问 `http://127.0.0.1:5000`。





## 项目结构

```
local_document_search/
├── app/                      # Flask 应用核心代码
│   ├── routes/               # 路由蓝图 (视图函数)
│   ├── services/             # 核心业务逻辑 (文件扫描, 转换, 搜索)
│   ├── static/               # 静态文件
│   ├── templates/            # HTML 模板
│   ├── utils/                # 辅助工具函数
│   ├── __init__.py           # 应用工厂函数
│   ├── config.py            # 配置文件
│   └── models.py             # SQLAlchemy 数据模型
├── logs/               	  # 运行日志
├── migrations/               # Flask-Migrate 数据库迁移脚本
├── scripts/                  # 辅助脚本 (如 Joplin 导入)
├── tests/                    # 单元测试
├── .env                      # 环境变量 (需从 .env.example 复制创建)
├── .env.example              # 环境变量模板
├── requirements.txt          # Python 依赖
└── run.py                    # 应用启动入口
```





## 其它信息

### 1. 同步 Joplin 笔记

此功能通过命令行脚本执行。

**准备工作:**

1.  确保您已在 `.env` 文件中正确配置 `JOPLIN_API_TOKEN`。
2.  确保您的 Joplin 桌面应用正在运行，并且 Web Clipper 服务已开启 (`工具` -> `选项` -> `Web Clipper`)。

**执行同步:**

- **增量同步** (推荐，只同步上次同步后有更新的笔记):

  ```shell
  python scripts/import_joplin.py
  ```

- **全量同步** (强制重新同步所有笔记):

  ```shell
  python scripts/import_joplin.py --full
  ```



### 2. 图片描述 Provider 链式降级

支持为图片语义描述配置多 provider 降级链。例如：

```
IMAGE_CAPTION_PROVIDER=google-genai
IMAGE_PROVIDER_CHAIN=openai,google-genai,local
```

执行顺序：按照 `IMAGE_PROVIDER_CHAIN` 顺序逐个尝试；若链为空，则仅使用 `IMAGE_CAPTION_PROVIDER`。若 `IMAGE_CAPTION_PROVIDER` 不在链中，会被自动插入到链首，确保首选优先。

日志示例：

```
[ProviderFallback] attempt=1 provider=openai mode=llm file=img1.png
[ProviderFallback] failed attempt=1 provider=openai error=...OpenAIError...
[ProviderFallback] attempt=2 provider=google-genai mode=llm file=img1.png
```

全部失败时：

```
[ProviderFallback] all_failed file=img1.png errors=provider=openai error=...; provider=google-genai error=...
```

提示：将 `local` 置于链末可在外部 API 不可用时仍回退到本地 OCR（若安装了 Pillow + pytesseract）。



### 3. 界面多语言 (简体中文 / English)

系统内置一个轻量级自定义 i18n 机制，无第三方依赖：

访问示例：

```
http://127.0.0.1:5000/search?lang=en
http://127.0.0.1:5000/process?lang=zh
```



### 4. 配置项速览（节选）

| 变量                        | 说明                                                | 默认                     |
| --------------------------- | --------------------------------------------------- | ------------------------ |
| `DATABASE_URL`              | PostgreSQL 连接串                                   | -                        |
| `LOG_LEVEL`                 | 日志等级                                            | INFO                     |
| `LOG_TIME_FORMAT`           | 日志时间格式                                        | `%Y-%m-%d %H:%M:%S`      |
| `DOWNLOAD_PATH`             | 微信文章下载根目录                                  | `downloads`              |
| `IMAGE_CAPTION_PROVIDER`    | 图片描述 Provider (`local`/`openai`/`google-genai`) | `google-genai`           |
| `IMAGE_PROVIDER_CHAIN`      | Provider 降级链，逗号分隔                           | 空                       |
| `ENABLE_IMAGE_FRONT_MATTER` | 是否写入图片 Front Matter                           | true                     |
| `TESSERACT_LANG`            | 本地 OCR 语言包                                     | `chi_sim+eng`            |
| `JOPLIN_API_TOKEN`          | Joplin API Token                                    | -                        |
| `JOPLIN_API_URL`            | Joplin API 基础地址                                 | `http://localhost:41184` |

> 更多请查看 `app/config.py`。



### 5. 部署到 Ubuntu 24.04 的注意事项

在 Ubuntu Server 或其他 Linux 环境中部署本项目时，常见问题是某些依赖在 Windows 上可用（例如 `pywin32`、Windows COM 自动化）或者需要 GUI 支持的库（例如 `tkinter`）在无头服务器上不可用。下面是建议的处理方式：

- pywin32
  - `pywin32` 仅在 Windows 平台上可用。本项目在 `requirements.txt` 中将 `pywin32` 标记为仅在 Windows 上安装（环境标记：`pywin32; sys_platform == "win32"`）。在 Ubuntu 上无需安装该包。
  - 在代码中，当在 Windows 平台并且 `pywin32` 可用时，项目会使用 Windows COM（Word/PowerPoint）进行 `.doc` / `.ppt` 等老格式的转换；否则会回退到使用 LibreOffice（soffice）以 headless 模式执行转换。

- tkinter
  - `tkinter` 通常用于打开本地文件选择对话框（仅适合有图形界面的桌面环境）。在无头的 Ubuntu 服务器上，`tkinter` 可能不可用或无法运行。项目中已实现懒加载并在缺少 `tkinter` 时返回友好的错误，建议在服务器部署时通过 API 直接传入目录路径（`folder_path` 参数）而不是依赖浏览对话框。
  - 如果确实需要在 Ubuntu 桌面环境中使用 GUI，可以安装：
    ```bash
    sudo apt update
    sudo apt install -y python3-tk
    ```

- LibreOffice headless（推荐在服务器上进行文件格式转换）
  - 在没有 Windows COM 支持的 Linux 系统上，安装 LibreOffice 并确保 `soffice` 在 PATH 中，项目会使用 `soffice --headless --convert-to ...` 执行格式转换。
  - 在 Ubuntu 24.04 上安装 LibreOffice：
    ```bash
    sudo apt update
    sudo apt install -y libreoffice
    ```

- 运行时建议
  - 在服务器上运行时，优先通过 API 提供 `folder_path` 参数，避免触发任何 GUI 相关代码路径。
  - 确保在部署前用 `pip install -r requirements.txt` 安装依赖（注意 `pywin32` 在 Linux 上不会安装）。
  - 如果需要自动化将大量 Office 老格式转换为现代格式（例如 `.doc` -> `.docx`），建议在服务器上安装 LibreOffice，并根据需要预先测试 `soffice --headless --convert-to docx filename.doc` 的行为。
