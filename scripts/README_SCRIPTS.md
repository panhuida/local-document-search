# 环境检查和服务管理脚本使用指南

本目录包含用于检查和管理本地文档搜索系统运行环境的辅助脚本。

## 📋 脚本列表

### 1. `check_environment.py` - 环境检查工具

全面检查系统运行环境是否就绪，包括：
- Python 版本
- 配置文件 (.env)
- Python 依赖包
- 目录结构
- PostgreSQL 数据库连接和扩展
- 外部工具（FFmpeg、Tesseract）
- API 密钥配置

#### 使用方法

```bash
# 基本检查
python scripts/check_environment.py

# 自动修复部分问题（创建 .env、创建日志目录等）
python scripts/check_environment.py --fix
```

#### 输出示例

```
╔════════════════════════════════════════════════════════════════════╗
║        本地文档搜索系统 - 环境检查工具                            ║
╚════════════════════════════════════════════════════════════════════╝

======================================================================
                             1. Python 环境                             
======================================================================

✓ Python 版本
  └─ Python 3.12.10

======================================================================
                          5. PostgreSQL 数据库                           
======================================================================

✗ PostgreSQL 服务
  └─ psql (PostgreSQL) 17.6
  ✗ 无法连接: Connection refused
  💡 修复建议: 1. 安装 PostgreSQL
  2. 启动服务
  3. 配置 .env 中的 DATABASE_URL
```

### 2. `start_services.py` - 服务启动工具

用于启动和管理 PostgreSQL 等必要服务。

#### 使用方法

```bash
# 检查服务状态
python scripts/start_services.py --check

# 启动 PostgreSQL 服务（交互式）
python scripts/start_services.py

# 设置 PostgreSQL 为自动启动（仅 Windows）
python scripts/start_services.py --autostart
```

#### Windows 系统

脚本会自动检测 PostgreSQL 服务（如 `postgresql-x64-17`）并提示是否启动。

**注意**：启动服务可能需要管理员权限。如果脚本提示权限不足，请：

1. 以管理员身份打开 PowerShell
2. 运行命令：
   ```powershell
   Start-Service -Name postgresql-x64-17
   Set-Service -Name postgresql-x64-17 -StartupType Automatic
   ```

#### Linux 系统

脚本会使用 `systemctl` 或 `service` 命令管理服务：

```bash
# 需要 sudo 权限
sudo python scripts/start_services.py
```

或手动启动：
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql  # 设置开机自启
```

## 🚀 完整启动流程

### 首次部署

1. **克隆项目并安装依赖**
   ```bash
   git clone <repository-url>
   cd local_document_search
   pip install -r requirements.txt
   ```

2. **运行环境检查**
   ```bash
   python scripts/check_environment.py --fix
   ```
   
   按照提示修复问题：
   - 编辑 `.env` 配置数据库连接
   - 安装缺失的 Python 包
   - 安装外部工具（FFmpeg、Tesseract）

3. **启动 PostgreSQL 服务**
   ```bash
   python scripts/start_services.py
   ```

4. **配置数据库扩展**
   
   连接到数据库并执行：
   ```sql
   CREATE EXTENSION IF NOT EXISTS pg_trgm;
   CREATE EXTENSION IF NOT EXISTS pgroonga;
   ```
   
   或使用 psql：
   ```bash
   psql -U postgres -d document_search -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
   psql -U postgres -d document_search -c "CREATE EXTENSION IF NOT EXISTS pgroonga;"
   ```

5. **应用数据库迁移**
   ```bash
   flask db upgrade
   ```

6. **再次检查环境**
   ```bash
   python scripts/check_environment.py
   ```
   
   应该看到：
   ```
   ✓ 所有检查通过！系统已就绪。
   ```

7. **启动应用**
   ```bash
   python run.py
   ```

### 日常使用

每次重启电脑后（如果 PostgreSQL 未设置自动启动）：

```bash
# 1. 启动服务
python scripts/start_services.py

# 2. 启动应用
python run.py
```

## 🔍 故障排查

### 问题：PostgreSQL 连接失败

**检查步骤**：

1. 确认服务正在运行
   ```bash
   python scripts/start_services.py --check
   ```

2. 检查端口配置
   - 查看 `.env` 中的 `DATABASE_URL`
   - 确认端口与实际服务端口一致（默认 5432，有些安装可能是 5433 或其他）

3. 测试连接
   ```bash
   psql -U <username> -h localhost -p <port> -d <database>
   ```

4. 查看服务日志
   - Windows: 事件查看器 → Windows 日志 → 应用程序
   - Linux: `sudo journalctl -u postgresql`

### 问题：缺少数据库扩展

**错误信息**：
```
relation "documents" does not exist
或
function pgroonga_score does not exist
```

**解决方法**：

1. 连接到数据库
   ```bash
   psql -U postgres -d document_search
   ```

2. 创建扩展
   ```sql
   CREATE EXTENSION IF NOT EXISTS pg_trgm;
   CREATE EXTENSION IF NOT EXISTS pgroonga;
   ```

3. 验证
   ```sql
   SELECT extname FROM pg_extension;
   ```

### 问题：权限不足

**Windows**：
- 以管理员身份运行 PowerShell 或 CMD
- 或修改服务权限设置

**Linux**：
- 使用 `sudo` 运行命令
- 或将当前用户添加到 postgresql 组

### 问题：Python 包缺失

运行以下命令重新安装：
```bash
pip install -r requirements.txt --upgrade
```

特定包安装：
```bash
# 图片处理
pip install Pillow pytesseract

# LLM 图片描述
pip install google-genai openai dashscope

# 视频转录
pip install faster-whisper
```

## 📝 环境变量配置

`.env` 文件关键配置项：

```bash
# 数据库连接（必需）
DATABASE_URL=postgresql://user:password@localhost:5432/document_search

# API 密钥（可选，用于图片描述）
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
DASHSCOPE_API_KEY=your_dashscope_api_key

# 功能开关
ENABLE_IMAGE_DESCRIPTION=true          # 启用图片描述
ENABLE_VIDEO_TRANSCRIPTION=false       # 启用视频转录（需要 faster-whisper）

# OCR 配置
TESSERACT_LANG=chi_sim+eng            # Tesseract 语言包
IMAGE_CAPTION_PROVIDER=google-genai   # 图片描述提供商
IMAGE_PROVIDER_CHAIN=google-genai,local  # 降级链

# 视频转录配置
WHISPER_MODEL=base                    # Whisper 模型大小
WHISPER_DEVICE=cpu                    # 使用设备（cpu/cuda）
```

## 🛠️ 开发者工具

### 手动检查数据库连接

```python
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    result = conn.execute("SELECT 1")
    print("数据库连接成功!")
```

### 查看已安装的 Python 包

```bash
pip list | grep -E "(Flask|SQLAlchemy|psycopg2|markitdown)"
```

### 重置数据库（危险操作！）

```bash
# 删除所有表
flask db downgrade base

# 重新应用迁移
flask db upgrade
```

## 📞 获取帮助

如果遇到脚本无法解决的问题：

1. 查看主 README.md 中的详细文档
2. 运行 `python scripts/check_environment.py` 查看详细错误信息
3. 查看应用日志：`logs/app.log` 和 `logs/errors.log`
4. 提交 Issue 时附上环境检查输出

## 🔄 更新日志

- **2025-01** - 初始版本
  - 添加环境检查脚本
  - 添加服务启动脚本
  - 支持 Windows 和 Linux 系统
