#!/usr/bin/env python3
"""
快速检查虚拟环境中包的版本（使用 pip list 批量获取）
"""
import subprocess
import re
import sys

def get_installed_packages():
    """获取所有已安装包的版本"""
    try:
        result = subprocess.run(
            ['pip', 'list'],
            capture_output=True,
            text=True,
            check=True
        )
        packages = {}
        for line in result.stdout.split('\n')[2:]:  # 跳过表头
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    pkg_name = parts[0].lower()
                    pkg_version = parts[1]
                    packages[pkg_name] = pkg_version
        return packages
    except Exception as e:
        print(f"错误: 无法获取已安装包列表: {e}", file=sys.stderr)
        return {}

def parse_requirements_line(line):
    """解析 requirements.txt 中的一行"""
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    
    # 移除注释
    if '#' in line:
        line = line.split('#')[0].strip()
    
    # 移除 extras [standard]
    pkg_part = re.sub(r'\[.*?\]', '', line).strip()
    
    # 提取包名和版本要求
    match = re.match(r'^([a-zA-Z0-9_-]+)\s*(.*)', pkg_part)
    if match:
        pkg_name = match.group(1).lower()
        version_req = match.group(2).strip() if match.group(2) else "any"
        return pkg_name, version_req
    return None

# 获取已安装的包
print("正在获取已安装包列表...")
installed = get_installed_packages()

# 读取 requirements.txt
print("正在读取 requirements.txt...")
print()
print("=" * 90)
print(f"{'包名':<35} {'要求版本':<30} {'已安装版本':<20} {'状态'}")
print("=" * 90)

with open('requirements.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

not_installed = []
mismatch = []
ok_count = 0

for line in lines:
    info = parse_requirements_line(line)
    if not info:
        continue
    
    pkg_name, version_req = info
    installed_ver = installed.get(pkg_name)
    
    if not installed_ver:
        not_installed.append((pkg_name, version_req))
        print(f"{pkg_name:<35} {version_req:<30} {'未安装':<20} ⚠")
    else:
        # 检查版本匹配
        status = "✓"
        if '==' in version_req:
            required = version_req.split('==')[1].strip()
            if installed_ver != required:
                status = f"✗ (需要 {required})"
                mismatch.append((pkg_name, version_req, installed_ver, required))
            else:
                ok_count += 1
        elif version_req != "any":
            # 对于 >=, < 等，简单显示已安装
            ok_count += 1
        else:
            ok_count += 1
        
        print(f"{pkg_name:<35} {version_req:<30} {installed_ver:<20} {status}")

print("=" * 90)
print()
print(f"✓ 版本匹配: {ok_count} 个")
if mismatch:
    print(f"✗ 版本不匹配: {len(mismatch)} 个")
    for pkg, req, inst, need in mismatch:
        print(f"  - {pkg}: 已安装 {inst}, 需要 {need}")
if not_installed:
    print(f"⚠ 未安装: {len(not_installed)} 个")
    for pkg, req in not_installed:
        print(f"  - {pkg} ({req})")

if not mismatch and not not_installed:
    print("\n✓ 所有包版本检查通过！")
else:
    print(f"\n总计: {ok_count} 个通过, {len(mismatch)} 个不匹配, {len(not_installed)} 个未安装")

