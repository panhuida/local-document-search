#!/bin/bash
# 快速启动脚本 - Linux/macOS 版本
# 用于快速检查环境并启动本地文档搜索系统

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

export PYTHONPATH="src:$PYTHONPATH"

echo -e "\n${BLUE}========================================"
echo -e "  本地文档搜索系统 - 快速启动"
echo -e "========================================${NC}\n"

# 检查 Python 是否可用
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[错误] 未找到 Python，请先安装 Python 3.10+${NC}"
    exit 1
fi

echo -e "${BLUE}[1/4] 检查环境...${NC}"
if ! python3 scripts/check_environment.py --fix; then
    echo -e "\n${RED}[错误] 环境检查未通过，请根据上述提示修复问题${NC}\n"
    echo "常见问题："
    echo "  - PostgreSQL 服务未启动：sudo systemctl start postgresql"
    echo "  - 缺少配置文件：已自动创建 .env，请编辑后重新运行"
    echo "  - 缺少 Python 包：请运行 uv sync 或 pip3 install ."
    echo ""
    exit 1
fi

echo -e "\n${BLUE}[2/4] 检查 PostgreSQL 服务...${NC}"
if ! python3 scripts/start_services.py --check; then
    echo -e "\n${YELLOW}[警告] PostgreSQL 服务检查失败${NC}"
    read -p "是否尝试启动服务？(需要 sudo 权限) [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo python3 scripts/start_services.py
    fi
fi

echo -e "\n${BLUE}[3/4] 最后检查...${NC}"
if ! python3 scripts/check_environment.py; then
    echo -e "\n${RED}[错误] 环境仍有问题，无法启动应用${NC}"
    exit 1
fi

echo -e "\n${BLUE}[4/4] 启动应用...${NC}\n"
echo -e "${GREEN}========================================"
echo -e "  系统正在启动，请稍候..."
echo -e "  访问地址: http://127.0.0.1:5000"
echo -e "  按 Ctrl+C 停止服务"
echo -e "========================================${NC}\n"

python3 run.py
