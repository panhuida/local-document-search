# 本地文档智能搜索系统

一个基于 Flask 和 PostgreSQL 的本地文档智能搜索 Web 应用。它能自动扫描您指定的本地文件夹或同步 Joplin 笔记，将多种格式的文档（如 Office 全家桶、PDF、代码、日志等）统一转换为 Markdown 格式，并利用 PostgreSQL 的高级索引（PGroonga 全文搜索、Trigram 模糊搜索）为您提供毫秒级的精准、高效的搜索体验。

## ✨ 主要功能

- **📁 智能文件夹扫描**：递归扫描本地文件夹，可根据文件修改日期、文件类型进行增量或全量索引。
- **✍️ Joplin 笔记同步**：通过脚本从本地 Joplin 应用的 API 同步笔记，实现对知识库的全文搜索。
- **📄 强大的格式转换**：内置 `markitdown`，支持将 `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.html`, `.md`, `.txt` 及各类代码和日志文件自动转换为结构化的 Markdown。
- **🚀 高性能全文搜索**：集成 **PGroonga** 扩展，为文档内容和文件名提供高速、精准的全文搜索能力。
- **✍️ 模糊与相似度搜索**：利用 **pg_trgm** 扩展，支持文件名和内容的 trigram 模糊匹配，即使有拼写错误也能找到相关结果。
- **🖥️ 简洁易用的 Web 界面**：
    - 提供清晰的搜索页面，支持关键词搜索。
    - 搜索结果列表会生成包含关键词的**内容摘要**并**高亮**显示。
    - 支持点击文件名预览完整的 Markdown 内容。
    - 支持从搜索结果中直接调用系统默认程序打开本地的原始文件。
 - **🧠 多模态增强**：图片可本地 OCR 或调用 LLM（OpenAI / Gemini）生成语义描述，自动（可配置）插入元数据 Front Matter。
 - **🎬 视频文件占位转换**：提取结构化元数据（时长、分辨率、编码等）为后续字幕/摘要奠定基础。
 - **🗺️ 思维导图与图表**：支持 XMind 与 Draw.io (`.drawio`) 解析为可检索的 Markdown 列表结构。

## 🛠️ 技术栈

- **后端**: Python 3, Flask, SQLAlchemy
- **数据库**: PostgreSQL
- **数据库扩展**: PGroonga (全文搜索), pg_trgm (模糊搜索)
- **前端**: 原生 HTML, CSS, JavaScript (无复杂框架)
- **核心依赖**: 
    - `Flask-Migrate`: 用于数据库结构迁移。
    - `psycopg2-binary`: PostgreSQL 驱动。
    - `markitdown[all]`: 强大的多格式文件转 Markdown 工具。
    - `python-dotenv`: 用于管理环境变量。
    - `requests`: 用于 API 请求。

## ⚙️ 安装与设置

#### 1. 环境准备
- 确保您已经安装了 Python 3.10+ 和 Git。
- 安装并运行 **PostgreSQL** (建议版本 12+)。

#### 2. 克隆与安装依赖
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

#### 3. 配置环境变量
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

#### 4. 配置数据库
- 在 PostgreSQL 中创建一个新的数据库（例如，`document_search`）。
- 连接到您刚创建的数据库，并启用 `pg_trgm` 和 `pgroonga` 扩展。您可以使用 `psql` 或任何图形化工具执行以下 SQL 命令：
  ```sql
  CREATE EXTENSION IF NOT EXISTS pg_trgm;
  CREATE EXTENSION IF NOT EXISTS pgroonga;
  ```
  > **重要**: PGroonga 可能需要单独安装。请参考 [PGroonga 官方安装文档](https://pgroonga.github.io/install/) 完成在您操作系统上的安装。

#### 5. 初始化数据库
首次运行或代码更新后，需要初始化或更新数据库表结构。
```bash
# 设置 Flask 应用入口 (仅在当前终端会话中有效)
# Windows (CMD): set FLASK_APP=run.py
# Windows (PowerShell): $env:FLASK_APP="run.py"
# macOS/Linux: export FLASK_APP=run.py

# 应用数据库迁移 (将创建或更新所有表和索引)
flask db upgrade
```

## 🚀 如何使用

### 1. 启动 Web 应用
在项目根目录下运行：
```bash
python run.py
```
打开浏览器，访问 `http://127.0.0.1:5000`。

### 2. 导入本地文件夹文档
-   点击页面上的“文档转换”链接，或直接访问 `/convert`。
-   在输入框中填入您想要扫描的本地文件夹的**绝对路径**。
-   点击“开始转换”按钮，程序将开始在后台扫描和处理文件。

### 3. 同步 Joplin 笔记
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

### 4. 搜索文档
处理完成后，访问主页 (`/`) 或搜索页 (`/search`)，即可查找已处理过的所有文档。

### 5. 图片 OCR 与 EXIF Front Matter

当环境变量 `IMAGE_CAPTION_PROVIDER=local` 时，系统使用 `pytesseract` 对图片执行本地 OCR，并在生成的 Markdown 顶部插入一个 YAML Front Matter 区块，包含：

```
---
source_file: 原始文件名
provider: local-ocr
hash_sha256: 文件内容 SHA256
file_size: 字节大小
modified_time: 文件修改时间 (ISO8601)
exif: 可能包含 DateTimeOriginal / Model / Make / LensModel / FNumber / ExposureTime / ISOSpeedRatings / FocalLength / Orientation / Software / GPSInfo / Width / Height / Mode / Format 等字段
ocr_lang: OCR 使用的语言 (由 TESSERACT_LANG 指定, 默认 eng)
---
# 文件名
<OCR 识别出的正文>
```

说明：
- 若图片无 EXIF 或部分字段缺失，对应键会被省略或 `exif: {}`。
- 该 Front Matter 旨在支持后续扩展（如缓存、溯源、检索过滤）。
- 切换到 `IMAGE_CAPTION_PROVIDER=openai` 或 `google-genai` 时，将使用 LLM 生成更语义化的图像描述；此模式下暂不添加上述 Front Matter（后续可统一）。
- 设置 `TESSERACT_LANG=chi_sim` 可提高中文图片识别质量（前提：系统已安装对应语言包）。

未来计划：加入可选配置以关闭 front matter，及图片 caption 缓存机制。

### 6. 视频文件元数据占位转换 (实验性)

当前已对常见视频格式 (`.mp4`, `.mkv`, `.mov`, `.webm`) 支持“元数据 -> Markdown 占位”模式：

```
---
source_file: demo.mp4
provider: video-metadata
hash_sha256: ...
file_size_bytes: 1234567
modified_time: 2025-09-20T12:34:56.789012
video:
  format_name: mov,mp4,m4a,3gp,3g2,mj2
  duration_seconds: 734.2
  duration_human: 12:14.200
  bit_rate: 1234567
  video_codec: h264
  audio_codec: aac
  width: 1920
  height: 1080
  avg_frame_rate: 30/1
  nb_streams: 2
file_size_human: 1.18 MB
---
# demo.mp4

(视频元数据占位，尚未生成转录内容)
```

实现方式：调用系统 `ffprobe`（来自 FFmpeg）。如果未安装，转换会返回错误信息。后续计划：
- 集成本地/云端 ASR 生成字幕与章节
- 场景分割与关键帧 OCR
- 多模态摘要（可选 LLM）
- 缓存与增量更新（基于 hash）

可配置项预留（未来）：
`VIDEO_TRANSCRIPT_PROVIDER`, `VIDEO_ASR_MODEL`, `VIDEO_SCENE_DETECT`, `VIDEO_KEYFRAME_OCR` 等。

### 7. Draw.io 图表转换 (新增)

现已支持将 `.drawio` 文件转换为结构化 Markdown，提取每个页面 (diagram) 中的节点文本。输出格式示例：

```
# example.drawio

总共 2 个页面，5 个文本项目
---

## Page-1
- 开始
- 处理步骤
- 结束

## Page-2
- 另一页节点
```

说明：
- 标题行使用原始文件名。
- 第二行统计页面数量与节点（文本）总数。
- `---` 作为结构分隔（非 YAML Front Matter）。
- 每个页面以二级标题 `## 页面名` 开头，节点以无序列表 `- 文本` 形式列出。
- 文本内容会去除 HTML 标签并反转常见实体（`&lt;`, `&gt;`, `&amp;` 等）。
- 若页面没有可提取文本，输出 `*此页面没有找到文本内容*`。

支持的解析策略：
1. 直接内嵌 `<mxGraphModel>` → 直接遍历 `root` 下 `mxCell` 的 `value` 属性。
2. 压缩/编码数据：若 diagram 文本节点为压缩 + base64（或仅 base64 / URL 编码）存储，会自动尝试多级解码（含 `zlib` raw/标准、base64、`unquote`）。

局限与后续计划：
- 目前仅抽取节点文本，不包含连线语义、布局或样式。
- 后续可选：生成关系表 / Mermaid 流程图 / 语义摘要。
- 可扩展 Front Matter（例如 diagram 节点计数 / 页面名称列表）用于更细粒度检索。

## 🏗️ 项目结构

```
local_document_search/
├── app/                      # Flask 应用核心代码
│   ├── routes/               # 路由蓝图 (视图函数)
│   ├── services/             # 核心业务逻辑 (文件扫描, 转换, 搜索)
│   ├── templates/            # HTML 模板
│   ├── utils/                # 辅助工具函数
│   ├── __init__.py           # 应用工厂函数
│   └── models.py             # SQLAlchemy 数据模型
├── migrations/               # Flask-Migrate 数据库迁移脚本
├── scripts/                  # 辅助脚本 (如 Joplin 导入)
├── tests/                    # 单元测试
├── .env                      # 环境变量 (需从 .env.example 复制创建)
├── .env.example              # 环境变量模板
├── config.py                 # 配置文件
├── requirements.txt          # Python 依赖
└── run.py                    # 应用启动入口
```

## 🏗️ 开发

### 数据库迁移
当您修改了 `app/models.py` 中的数据模型后，需要执行以下命令来生成并应用数据库迁移：

```bash
# 1. 生成迁移脚本 (会自动检测模型变更)
flask db migrate -m "A short description of the changes"

# 2. 应用迁移到数据库
flask db upgrade
```

## 📄 许可证

本项目采用 MIT 许可证。
