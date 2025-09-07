# 本地文档搜索Web应用

一个基于Web的本地文档管理和搜索系统，能够自动扫描指定文件夹内的文档，将其内容统一转换为Markdown格式并存入数据库，提供高效的全文搜索功能。

## 主要功能

- **文件夹扫描**：递归扫描本地指定文件夹，可根据文件修改日期进行筛选。
- **格式转换**：支持多种文件格式（`.pdf`, `.docx`, `.pptx`, `.xlsx`, `.html`, `.md`, `.txt`及各类代码文件）自动转换为Markdown格式。
- **数据库存储**：将转换后的内容及文件元信息（路径、大小、修改时间等）存入PostgreSQL数据库。
- **Web搜索界面**：提供简洁的Web页面，用于输入关键词进行搜索。
- **结果高亮与预览**：搜索结果列表会生成包含关键词的**内容摘要**并**高亮**显示。同时支持点击文件名预览完整的Markdown内容。
- **打开原始文件**：支持从搜索结果中直接调用系统默认程序打开本地的原始文件。
- **日志记录**：拥有详细的日志系统，方便追踪程序的运行和错误情况。

## 技术栈

- **后端**: Python 3, Flask, SQLAlchemy
- **数据库**: PostgreSQL
- **前端**: HTML, Tailwind CSS, JavaScript
- **核心依赖**: 
    - `Flask-Migrate`: 用于数据库结构迁移。
    - `pdfplumber`: 用于处理PDF文件。
    - `markitdown[all]`: 用于处理各类Office文档、HTML等。

## 安装与设置

1.  **环境准备**：
    -   确保您已经安装了 Python 3 和 PostgreSQL 数据库。
    -   建议创建一个Python虚拟环境。

2.  **安装依赖**：
    在项目根目录下，运行以下命令安装所有必需的Python库：
    ```bash
    pip install -r requirements.txt
    ```

3.  **配置数据库**：
    -   在PostgreSQL中创建一个新的数据库（例如，`document_search`）。
    -   在项目根目录下，创建一个名为 `.env` 的文件。复制以下内容并根据您的数据库实际设置（用户名、密码、地址、数据库名）进行修改：
        ```
        # 数据库连接
        DATABASE_URL=postgresql://YourUser:YourPassword@localhost:5432/document_search

        # Flask 环境
        FLASK_ENV=development
        FLASK_SECRET_KEY=a-very-secret-key
        ```

4.  **初始化数据库**：
    如果您是首次运行，需要初始化数据库表结构。在项目根目录下，依次运行以下命令：
    ```bash
    # (仅首次需要) 创建迁移文件夹
    flask db init

    # 生成迁移脚本
    flask db migrate -m "Initial migration."

    # 应用迁移到数据库
    flask db upgrade
    ```
    *注意：如果 `migrations` 文件夹已存在，则无需运行 `flask db init`。*

## 如何使用

1.  **启动应用**：
    在项目根目录下运行：
    ```bash
    python run.py
    ```

2.  **访问应用**：
    打开浏览器，访问 `http://127.0.0.1:5000`。应用默认将显示**搜索页面**。

3.  **处理文档**：
    -   点击页面右上角的“文档处理与导入”链接，跳转到处理页面 (`/process`)。
    -   在输入框中填入您想要扫描的本地文件夹的**绝对路径**。
    -   选择其他选项（如日期范围、文件类型等），点击“开始处理”按钮。
    -   等待处理完成。

4.  **搜索文档**：
    -   处理完成后，可以返回“搜索页面”。
    -   在搜索框中输入关键词，即可查找已处理过的文档。
