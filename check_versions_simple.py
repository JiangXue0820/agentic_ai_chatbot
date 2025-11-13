#!/usr/bin/env python3
"""
快速检查 requirements.txt 中的包版本
"""
import subprocess
import re

def get_package_info(pkg_line):
    """从 requirements.txt 行中提取包名和版本要求"""
    line = pkg_line.strip()
    if not line or line.startswith('#'):
        return None
    
    # 移除注释
    if '#' in line:
        line = line.split('#')[0].strip()
    
    # 移除 extras [standard] 等
    pkg_part = re.sub(r'\[.*?\]', '', line).strip()
    
    # 提取包名和版本
    match = re.match(r'^([a-zA-Z0-9_-]+)\s*(.*)', pkg_part)
    if match:
        pkg_name = match.group(1)
        version_req = match.group(2).strip() if match.group(2) else "any"
        return pkg_name, version_req
    return None

def get_installed_version(pkg_name):
    """获取已安装版本"""
    try:
        result = subprocess.run(
            ['pip', 'show', pkg_name],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            return None
        for line in result.stdout.split('\n'):
            if line.startswith('Version:'):
                return line.split(':', 1)[1].strip()
    except:
        pass
    return None

# 读取 requirements.txt
with open('requirements.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("包名".ljust(30), "要求版本".ljust(25), "已安装版本".ljust(15), "状态")
print("=" * 85)

not_found = []
found = []

for line in lines:
    info = get_package_info(line)
    if not info:
        continue
    
    pkg_name, version_req = info
    installed = get_installed_version(pkg_name)
    
    if not installed:
        not_found.append((pkg_name, version_req))
        print(f"{pkg_name:<30} {version_req:<25} {'未安装':<15} ⚠")
    else:
        found.append((pkg_name, version_req, installed))
        # 简单检查版本是否匹配（用于 == 的精确匹配）
        if '==' in version_req:
            required_ver = version_req.split('==')[1].strip()
            status = "✓" if installed == required_ver else f"✗ (需要 {required_ver})"
        else:
            status = "✓ 已安装"
        print(f"{pkg_name:<30} {version_req:<25} {installed:<15} {status}")

print("=" * 85)
if not_found:
    print(f"\n⚠ 未安装的包: {len(not_found)} 个")
    for pkg, ver in not_found:
        print(f"  - {pkg} ({ver})")
else:
    print("\n✓ 所有包都已安装")

