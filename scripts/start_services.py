#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
服务启动辅助脚本 - 启动必要的系统服务

运行方式:
    python scripts/start_services.py              # 启动所有服务
    python scripts/start_services.py --postgresql  # 仅启动 PostgreSQL
    python scripts/start_services.py --check       # 仅检查状态
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 颜色输出
class Colors:
    if sys.platform == 'win32':
        os.system('')
    
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def is_windows():
    return platform.system() == 'Windows'

def is_linux():
    return platform.system() == 'Linux'

def check_postgresql_service_windows():
    """检查 Windows 上的 PostgreSQL 服务状态"""
    try:
        # 查找 PostgreSQL 服务
        result = subprocess.run(
            ['powershell', '-Command', 
             "Get-Service | Where-Object {$_.Name -like '*postgres*'} | Select-Object Name, Status, StartType | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            import json
            services = json.loads(result.stdout) if result.stdout.strip() != '{}' else []
            if isinstance(services, dict):
                services = [services]
            
            if services:
                return services[0]['Name'], services[0]['Status'], services[0]['StartType']
        
        return None, None, None
        
    except Exception as e:
        print(f"{Colors.RED}检查服务状态出错: {e}{Colors.RESET}")
        return None, None, None

def start_postgresql_windows(service_name):
    """启动 Windows 上的 PostgreSQL 服务"""
    print(f"{Colors.CYAN}正在启动 PostgreSQL 服务 '{service_name}'...{Colors.RESET}")
    
    try:
        # 尝试使用管理员权限启动
        result = subprocess.run(
            ['powershell', '-Command', f'Start-Service -Name "{service_name}"'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"{Colors.GREEN}✓ PostgreSQL 服务启动成功{Colors.RESET}")
            return True
        else:
            error = result.stderr.strip()
            if 'UnauthorizedAccessException' in error or 'PermissionDenied' in error:
                print(f"{Colors.YELLOW}⚠️  需要管理员权限{Colors.RESET}")
                print(f"{Colors.YELLOW}请以管理员身份运行 PowerShell 并执行:{Colors.RESET}")
                print(f"  Start-Service -Name {service_name}")
            else:
                print(f"{Colors.RED}✗ 启动失败: {error}{Colors.RESET}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}启动服务出错: {e}{Colors.RESET}")
        return False

def set_postgresql_autostart_windows(service_name):
    """设置 PostgreSQL 服务为自动启动"""
    print(f"{Colors.CYAN}正在设置服务为自动启动...{Colors.RESET}")
    
    try:
        result = subprocess.run(
            ['powershell', '-Command', f'Set-Service -Name "{service_name}" -StartupType Automatic'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"{Colors.GREEN}✓ 已设置为自动启动{Colors.RESET}")
            return True
        else:
            print(f"{Colors.YELLOW}⚠️  需要管理员权限设置自动启动{Colors.RESET}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}设置自动启动出错: {e}{Colors.RESET}")
        return False

def check_postgresql_service_linux():
    """检查 Linux 上的 PostgreSQL 服务状态"""
    try:
        # 尝试 systemctl
        result = subprocess.run(
            ['systemctl', 'is-active', 'postgresql'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        status = result.stdout.strip()
        return 'postgresql', status, 'systemd'
        
    except FileNotFoundError:
        # 尝试 service 命令
        try:
            result = subprocess.run(
                ['service', 'postgresql', 'status'],
                capture_output=True,
                text=True,
                timeout=5
            )
            status = 'active' if result.returncode == 0 else 'inactive'
            return 'postgresql', status, 'service'
        except:
            return None, None, None
    except Exception as e:
        print(f"{Colors.RED}检查服务状态出错: {e}{Colors.RESET}")
        return None, None, None

def start_postgresql_linux():
    """启动 Linux 上的 PostgreSQL 服务"""
    print(f"{Colors.CYAN}正在启动 PostgreSQL 服务...{Colors.RESET}")
    
    try:
        # 尝试 systemctl
        result = subprocess.run(
            ['sudo', 'systemctl', 'start', 'postgresql'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"{Colors.GREEN}✓ PostgreSQL 服务启动成功{Colors.RESET}")
            return True
        else:
            print(f"{Colors.RED}✗ 启动失败，尝试使用 service 命令...{Colors.RESET}")
            result = subprocess.run(
                ['sudo', 'service', 'postgresql', 'start'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print(f"{Colors.GREEN}✓ PostgreSQL 服务启动成功{Colors.RESET}")
                return True
            else:
                print(f"{Colors.RED}✗ 启动失败: {result.stderr.strip()}{Colors.RESET}")
                return False
                
    except Exception as e:
        print(f"{Colors.RED}启动服务出错: {e}{Colors.RESET}")
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description='启动必要的系统服务')
    parser.add_argument('--postgresql', action='store_true', help='仅操作 PostgreSQL 服务')
    parser.add_argument('--check', action='store_true', help='仅检查服务状态')
    parser.add_argument('--autostart', action='store_true', help='设置 PostgreSQL 为自动启动（仅 Windows）')
    args = parser.parse_args()
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║               本地文档搜索系统 - 服务启动工具                     ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")
    
    # 检查 PostgreSQL 服务
    print(f"{Colors.BOLD}检查 PostgreSQL 服务状态...{Colors.RESET}\n")
    
    if is_windows():
        service_name, status, start_type = check_postgresql_service_windows()
        
        if service_name:
            print(f"服务名称: {Colors.CYAN}{service_name}{Colors.RESET}")
            
            if status == 4:  # Running
                print(f"运行状态: {Colors.GREEN}运行中 ✓{Colors.RESET}")
            elif status == 1:  # Stopped
                print(f"运行状态: {Colors.RED}已停止 ✗{Colors.RESET}")
            else:
                print(f"运行状态: {Colors.YELLOW}未知 ({status}){Colors.RESET}")
            
            start_type_str = {1: '自动', 2: '手动', 3: '禁用', 4: '自动(延迟启动)'}.get(start_type, f'未知({start_type})')
            print(f"启动类型: {Colors.CYAN}{start_type_str}{Colors.RESET}")
            print()
            
            if args.check:
                return 0
            
            # 启动服务
            if status != 4:  # Not Running
                if not args.check:
                    choice = input(f"{Colors.YELLOW}是否启动 PostgreSQL 服务? (y/N): {Colors.RESET}").strip().lower()
                    if choice == 'y':
                        start_postgresql_windows(service_name)
                        
                        # 设置自动启动
                        if args.autostart or start_type != 1:
                            choice = input(f"{Colors.YELLOW}是否设置为自动启动? (y/N): {Colors.RESET}").strip().lower()
                            if choice == 'y':
                                set_postgresql_autostart_windows(service_name)
            else:
                print(f"{Colors.GREEN}PostgreSQL 服务正在运行，无需启动{Colors.RESET}")
                
                if args.autostart and start_type != 1:
                    choice = input(f"{Colors.YELLOW}是否设置为自动启动? (y/N): {Colors.RESET}").strip().lower()
                    if choice == 'y':
                        set_postgresql_autostart_windows(service_name)
        else:
            print(f"{Colors.RED}✗ 未找到 PostgreSQL 服务{Colors.RESET}")
            print(f"{Colors.YELLOW}请确保已安装 PostgreSQL{Colors.RESET}\n")
            return 1
            
    elif is_linux():
        service_name, status, method = check_postgresql_service_linux()
        
        if service_name:
            print(f"服务名称: {Colors.CYAN}{service_name}{Colors.RESET}")
            print(f"管理方式: {Colors.CYAN}{method}{Colors.RESET}")
            
            if status == 'active':
                print(f"运行状态: {Colors.GREEN}运行中 ✓{Colors.RESET}\n")
            else:
                print(f"运行状态: {Colors.RED}{status} ✗{Colors.RESET}\n")
                
                if not args.check:
                    choice = input(f"{Colors.YELLOW}是否启动 PostgreSQL 服务? (y/N): {Colors.RESET}").strip().lower()
                    if choice == 'y':
                        start_postgresql_linux()
        else:
            print(f"{Colors.RED}✗ 未找到 PostgreSQL 服务{Colors.RESET}")
            print(f"{Colors.YELLOW}请确保已安装 PostgreSQL{Colors.RESET}\n")
            return 1
    else:
        print(f"{Colors.YELLOW}不支持的操作系统: {platform.system()}{Colors.RESET}\n")
        return 1
    
    # 提示下一步
    print(f"\n{Colors.BOLD}下一步:{Colors.RESET}")
    print(f"1. 运行环境检查: {Colors.CYAN}python scripts/check_environment.py{Colors.RESET}")
    print(f"2. 应用数据库迁移: {Colors.CYAN}flask db upgrade{Colors.RESET}")
    print(f"3. 启动应用: {Colors.CYAN}python run.py{Colors.RESET}\n")
    
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}操作已取消{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}发生错误: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
