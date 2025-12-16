#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
环境检查脚本 - 检查本地文档搜索系统运行环境是否就绪

运行方式:
    python scripts/check_environment.py
    python scripts/check_environment.py --fix  # 尝试自动修复部分问题
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, List, Optional
import importlib.util

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 颜色输出 (Windows/Unix兼容)
class Colors:
    if sys.platform == 'win32':
        # Windows 10+ 支持 ANSI
        os.system('')
    
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_header(text: str):
    """打印章节标题"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def print_check(name: str, status: bool, message: str = "", fix_hint: str = ""):
    """打印检查结果"""
    status_symbol = f"{Colors.GREEN}✓{Colors.RESET}" if status else f"{Colors.RED}✗{Colors.RESET}"
    print(f"{status_symbol} {Colors.BOLD}{name}{Colors.RESET}")
    if message:
        print(f"  {Colors.CYAN}└─{Colors.RESET} {message}")
    if not status and fix_hint:
        print(f"  {Colors.YELLOW}💡 修复建议:{Colors.RESET} {fix_hint}")
    print()

def check_python_version() -> Tuple[bool, str]:
    """检查 Python 版本 (需要 3.10+)"""
    version = sys.version_info
    required = (3, 10)
    
    if version >= required:
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    else:
        return False, f"当前版本 {version.major}.{version.minor}.{version.micro}，需要 3.10+"

def check_env_file() -> Tuple[bool, str]:
    """检查 .env 文件是否存在"""
    env_path = project_root / '.env'
    env_example = project_root / '.env.example'
    
    if env_path.exists():
        return True, f"找到配置文件: {env_path}"
    elif env_example.exists():
        return False, f"缺少 .env 文件，但找到模板: {env_example}"
    else:
        return False, "缺少 .env 和 .env.example 文件"

def check_required_packages() -> Tuple[bool, str, List[str]]:
    """检查必需的 Python 包"""
    required = [
        'flask',
        'sqlalchemy',
        'psycopg2',
        'markitdown',
        'flask_migrate',
        'python-dotenv',
        'requests',
        'beautifulsoup4',
        'tenacity',
    ]
    
    missing = []
    for package in required:
        # 特殊处理包名映射
        module_name = {
            'python-dotenv': 'dotenv',
            'beautifulsoup4': 'bs4',
        }.get(package, package)
        
        if importlib.util.find_spec(module_name) is None:
            missing.append(package)
    
    if not missing:
        return True, f"所有必需包已安装 ({len(required)} 个)", []
    else:
        return False, f"缺少 {len(missing)} 个包", missing

def check_optional_packages() -> Tuple[bool, str, List[str]]:
    """检查可选的 Python 包"""
    optional = {
        'PIL': '图片处理 (Pillow)',
        'pytesseract': '本地 OCR',
        'google.genai': 'Google Gemini API',
        'openai': 'OpenAI API',
        'dashscope': '阿里通义 API',
        'faster_whisper': '视频转录',
    }
    
    missing = []
    for module, desc in optional.items():
        if importlib.util.find_spec(module) is None:
            missing.append(f"{module} ({desc})")
    
    if not missing:
        return True, "所有可选包已安装", []
    else:
        return False, f"缺少 {len(missing)} 个可选包（不影响核心功能）", missing

def check_postgresql() -> Tuple[bool, str]:
    """检查 PostgreSQL 是否安装并运行"""
    # 检查 psql 命令
    psql_path = shutil.which('psql')
    if not psql_path:
        return False, "未找到 psql 命令，PostgreSQL 可能未安装"
    
    # 检查版本
    try:
        result = subprocess.run(
            ['psql', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        version_info = result.stdout.strip()
        
        # 尝试连接数据库
        from dotenv import load_dotenv
        load_dotenv(project_root / '.env')
        db_url = os.getenv('DATABASE_URL', '')
        
        if not db_url:
            return False, f"{version_info}\n  ⚠️  .env 中缺少 DATABASE_URL 配置"
        
        # 解析连接信息
        import re
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
        if not match:
            return False, f"{version_info}\n  ⚠️  DATABASE_URL 格式不正确"
        
        user, password, host, port, dbname = match.groups()
        
        # 尝试连接（简单检查）
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        try:
            result = subprocess.run(
                ['psql', '-U', user, '-h', host, '-p', port, '-d', dbname, '-c', 'SELECT 1;'],
                env=env,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, f"{version_info}\n  ✓ 成功连接到数据库 {dbname} (端口 {port})"
            else:
                error_msg = result.stderr.strip().split('\n')[0] if result.stderr else "未知错误"
                return False, f"{version_info}\n  ✗ 无法连接: {error_msg}"
        except subprocess.TimeoutExpired:
            return False, f"{version_info}\n  ✗ 连接超时，数据库服务可能未启动"
        
    except FileNotFoundError:
        return False, "psql 命令不可用"
    except Exception as e:
        return False, f"检查时出错: {str(e)}"

def check_db_extensions() -> Tuple[bool, str, List[str]]:
    """检查 PostgreSQL 扩展"""
    required_extensions = ['pg_trgm', 'pgroonga']
    
    try:
        from dotenv import load_dotenv
        load_dotenv(project_root / '.env')
        db_url = os.getenv('DATABASE_URL', '')
        
        if not db_url:
            return False, "无法检查（缺少 DATABASE_URL）", required_extensions
        
        # 解析连接
        import re
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
        if not match:
            return False, "无法检查（DATABASE_URL 格式错误）", required_extensions
        
        user, password, host, port, dbname = match.groups()
        
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        result = subprocess.run(
            ['psql', '-U', user, '-h', host, '-p', port, '-d', dbname, 
             '-c', "SELECT extname FROM pg_extension;", '-t'],
            env=env,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return False, "无法查询扩展", required_extensions
        
        installed = [line.strip() for line in result.stdout.split('\n') if line.strip()]
        missing = [ext for ext in required_extensions if ext not in installed]
        
        if not missing:
            return True, f"已安装: {', '.join(required_extensions)}", []
        else:
            return False, f"已安装: {', '.join([e for e in required_extensions if e in installed])}", missing
            
    except Exception as e:
        return False, f"检查时出错: {str(e)}", required_extensions

def check_ffmpeg() -> Tuple[bool, str]:
    """检查 FFmpeg (用于视频处理)"""
    ffmpeg_path = shutil.which('ffmpeg')
    ffprobe_path = shutil.which('ffprobe')
    
    if not ffmpeg_path:
        return False, "未找到 ffmpeg 命令"
    
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        version_line = result.stdout.split('\n')[0]
        
        if ffprobe_path:
            return True, f"{version_line}\n  ✓ ffprobe 也已安装"
        else:
            return False, f"{version_line}\n  ⚠️  缺少 ffprobe"
            
    except Exception as e:
        return False, f"检查版本时出错: {str(e)}"

def check_tesseract() -> Tuple[bool, str]:
    """检查 Tesseract OCR"""
    tesseract_path = shutil.which('tesseract')
    
    if not tesseract_path:
        return False, "未找到 tesseract 命令"
    
    try:
        result = subprocess.run(
            ['tesseract', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        version_lines = result.stdout.split('\n')[:2]
        version_info = '\n  '.join(version_lines)
        
        # 检查语言包
        lang_result = subprocess.run(
            ['tesseract', '--list-langs'],
            capture_output=True,
            text=True,
            timeout=5
        )
        langs = lang_result.stdout.split('\n')[1:]  # 跳过第一行标题
        langs = [l.strip() for l in langs if l.strip()]
        
        from dotenv import load_dotenv
        load_dotenv(project_root / '.env')
        required_lang = os.getenv('TESSERACT_LANG', 'chi_sim+eng')
        required_langs = required_lang.replace('+', ' ').split()
        
        missing_langs = [l for l in required_langs if l not in langs]
        
        if not missing_langs:
            return True, f"{version_info}\n  ✓ 已安装语言包: {', '.join(required_langs)}"
        else:
            return False, f"{version_info}\n  ⚠️  缺少语言包: {', '.join(missing_langs)}"
            
    except Exception as e:
        return False, f"检查版本时出错: {str(e)}"

def check_api_keys() -> Tuple[bool, str, List[str]]:
    """检查 API 密钥配置"""
    from dotenv import load_dotenv
    load_dotenv(project_root / '.env')
    
    api_keys = {
        'GEMINI_API_KEY': 'Google Gemini',
        'OPENAI_API_KEY': 'OpenAI',
        'DASHSCOPE_API_KEY': '阿里通义千问',
    }
    
    configured = []
    missing = []
    
    for key, service in api_keys.items():
        value = os.getenv(key, '').strip()
        if value and value != 'your_api_key_here':
            configured.append(f"{service} (已配置)")
        else:
            missing.append(f"{service} ({key})")
    
    if configured:
        msg = f"已配置 {len(configured)} 个 API: " + ', '.join([s.split('(')[0].strip() for s in configured])
        if missing:
            msg += f"\n  ℹ️  可选配置: {', '.join([s.split('(')[0].strip() for s in missing])}"
        return True, msg, []
    else:
        return False, "未配置任何 API 密钥（图片描述功能将受限）", missing

def check_directories() -> Tuple[bool, str]:
    """检查必要的目录"""
    dirs = {
        'logs': '日志目录',
        'migrations': '数据库迁移',
        'src': '源代码',
        'scripts': '脚本',
    }
    
    missing = []
    for dir_name, desc in dirs.items():
        dir_path = project_root / dir_name
        if not dir_path.exists():
            missing.append(f"{dir_name} ({desc})")
    
    if not missing:
        return True, f"所有必需目录存在 ({len(dirs)} 个)"
    else:
        return False, f"缺少目录: {', '.join(missing)}"

def check_migrations() -> Tuple[bool, str]:
    """检查数据库迁移状态"""
    try:
        # 检查是否有迁移文件
        migrations_dir = project_root / 'migrations' / 'versions'
        if not migrations_dir.exists():
            return False, "迁移目录不存在，需要初始化: flask db init"
        
        migration_files = list(migrations_dir.glob('*.py'))
        if not migration_files:
            return False, "没有迁移文件，需要创建: flask db migrate"
        
        return True, f"找到 {len(migration_files)} 个迁移文件"
        
    except Exception as e:
        return False, f"检查时出错: {str(e)}"

def auto_fix_env_file() -> bool:
    """自动创建 .env 文件（从模板）"""
    env_path = project_root / '.env'
    env_example = project_root / '.env.example'
    
    if env_path.exists():
        print(f"{Colors.YELLOW}  .env 文件已存在，跳过创建{Colors.RESET}")
        return True
    
    if not env_example.exists():
        print(f"{Colors.RED}  缺少 .env.example 模板文件{Colors.RESET}")
        return False
    
    try:
        import shutil
        shutil.copy(env_example, env_path)
        print(f"{Colors.GREEN}  ✓ 已从模板创建 .env 文件{Colors.RESET}")
        print(f"{Colors.YELLOW}  ⚠️  请编辑 .env 文件，配置数据库连接和 API 密钥{Colors.RESET}")
        return True
    except Exception as e:
        print(f"{Colors.RED}  ✗ 创建失败: {e}{Colors.RESET}")
        return False

def auto_fix_directories() -> bool:
    """自动创建缺失目录"""
    dirs = ['logs']
    
    created = []
    for dir_name in dirs:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                created.append(dir_name)
            except Exception as e:
                print(f"{Colors.RED}  ✗ 创建 {dir_name} 失败: {e}{Colors.RESET}")
                return False
    
    if created:
        print(f"{Colors.GREEN}  ✓ 已创建目录: {', '.join(created)}{Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}  所有必需目录已存在{Colors.RESET}")
    
    return True

def main():
    """主检查流程"""
    import argparse
    parser = argparse.ArgumentParser(description='检查本地文档搜索系统运行环境')
    parser.add_argument('--fix', action='store_true', help='尝试自动修复部分问题')
    args = parser.parse_args()
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║        本地文档搜索系统 - 环境检查工具                            ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    
    all_passed = True
    warnings = []
    
    # 1. Python 版本
    print_header("1. Python 环境")
    status, msg = check_python_version()
    print_check("Python 版本", status, msg, 
                "请安装 Python 3.10 或更高版本" if not status else "")
    all_passed &= status
    
    # 2. 配置文件
    print_header("2. 配置文件")
    status, msg = check_env_file()
    fix_hint = "运行: cp .env.example .env 并编辑配置" if not status else ""
    print_check(".env 配置文件", status, msg, fix_hint)
    
    if args.fix and not status:
        print(f"{Colors.YELLOW}🔧 尝试自动修复...{Colors.RESET}")
        auto_fix_env_file()
    
    all_passed &= status
    
    # 3. Python 包
    print_header("3. Python 依赖包")
    status, msg, missing = check_required_packages()
    fix_hint = f"运行: pip install {' '.join(missing)}" if missing else ""
    print_check("必需包", status, msg, fix_hint)
    all_passed &= status
    
    status, msg, missing = check_optional_packages()
    print_check("可选包", status, msg, 
                f"可安装: pip install {' '.join([m.split('(')[0].strip() for m in missing])}" if missing else "")
    if not status:
        warnings.append("部分可选功能不可用")
    
    # 4. 目录结构
    print_header("4. 目录结构")
    status, msg = check_directories()
    print_check("项目目录", status, msg)
    
    if args.fix and not status:
        print(f"{Colors.YELLOW}🔧 尝试自动修复...{Colors.RESET}")
        auto_fix_directories()
    
    all_passed &= status
    
    status, msg = check_migrations()
    print_check("数据库迁移", status, msg,
                "运行: flask db init && flask db migrate && flask db upgrade" if not status else "")
    all_passed &= status
    
    # 5. PostgreSQL
    print_header("5. PostgreSQL 数据库")
    status, msg = check_postgresql()
    print_check("PostgreSQL 服务", status, msg,
                "1. 安装 PostgreSQL\n  2. 启动服务\n  3. 配置 .env 中的 DATABASE_URL" if not status else "")
    all_passed &= status
    
    if status:
        ext_status, ext_msg, missing_exts = check_db_extensions()
        fix_hint = ""
        if missing_exts:
            fix_hint = "连接数据库后执行:\n"
            for ext in missing_exts:
                fix_hint += f"  CREATE EXTENSION IF NOT EXISTS {ext};\n"
        print_check("数据库扩展", ext_status, ext_msg, fix_hint)
        all_passed &= ext_status
    
    # 6. 外部工具
    print_header("6. 外部工具 (可选)")
    
    status, msg = check_ffmpeg()
    print_check("FFmpeg (视频处理)", status, msg,
                "下载: https://ffmpeg.org/download.html" if not status else "")
    if not status:
        warnings.append("视频处理功能不可用")
    
    status, msg = check_tesseract()
    print_check("Tesseract OCR", status, msg,
                "下载: https://github.com/tesseract-ocr/tesseract" if not status else "")
    if not status:
        warnings.append("本地 OCR 功能不可用")
    
    # 7. API 密钥
    print_header("7. API 配置 (可选)")
    status, msg, missing = check_api_keys()
    print_check("API 密钥", status, msg,
                "在 .env 中配置需要使用的 API 密钥" if missing else "")
    if not status:
        warnings.append("LLM 图片描述功能受限")
    
    # 总结
    print_header("检查总结")
    
    if all_passed and not warnings:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ 所有检查通过！系统已就绪。{Colors.RESET}\n")
        print(f"{Colors.CYAN}可以运行以下命令启动系统:{Colors.RESET}")
        print(f"  python run.py\n")
        return 0
    elif all_passed and warnings:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠ 核心检查通过，但有 {len(warnings)} 个警告:{Colors.RESET}")
        for w in warnings:
            print(f"  • {w}")
        print(f"\n{Colors.CYAN}核心功能可以正常使用，建议安装可选组件以获得完整功能。{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ 检查未通过，请修复上述问题后再运行系统。{Colors.RESET}\n")
        if args.fix:
            print(f"{Colors.YELLOW}💡 部分问题已尝试自动修复，请重新运行检查。{Colors.RESET}\n")
        else:
            print(f"{Colors.YELLOW}💡 提示: 使用 --fix 参数可尝试自动修复部分问题{Colors.RESET}")
            print(f"  python scripts/check_environment.py --fix\n")
        return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}检查已取消{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}发生错误: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
