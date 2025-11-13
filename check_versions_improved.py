#!/usr/bin/env python3
"""
改进版：使用 pip show 逐个检查，更准确
"""
import subprocess
import re
import sys
import json

def get_installed_packages_json():
    """使用 pip list --format=json 获取包列表（更可靠）"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--format=json'],
            capture_output=True,
            text=True,
            check=True
        )
        packages = json.loads(result.stdout)
        # 创建小写包名到版本的映射
        pkg_map = {}
        for pkg in packages:
            name = pkg['name'].lower()
            version = pkg['version']
            pkg_map[name] = version
        return pkg_map
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
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

def check_version_range(installed_ver, version_req):
    """检查版本是否满足要求（支持 >=, <, == 等）"""
    if not version_req or version_req == "any":
        return True, "any"
    
    try:
        # 处理多个条件，如 ">=1.24.0,<2.0.0"
        conditions = [c.strip() for c in version_req.split(',')]
        
        for condition in conditions:
            # 匹配操作符和版本号
            match = re.match(r'(==|>=|<=|>|<|!=|~=)\s*(.+)', condition)
            if not match:
                continue
            
            operator = match.group(1)
            required_ver = match.group(2).strip()
            
            # 简单的版本比较（适用于大多数情况）
            inst_parts = [int(x) for x in installed_ver.split('.')]
            req_parts = [int(x) for x in required_ver.split('.')]
            
            # 补齐到相同长度
            max_len = max(len(inst_parts), len(req_parts))
            inst_parts += [0] * (max_len - len(inst_parts))
            req_parts += [0] * (max_len - len(req_parts))
            
            # 比较版本
            cmp_result = 0
            for i, j in zip(inst_parts, req_parts):
                if i < j:
                    cmp_result = -1
                    break
                elif i > j:
                    cmp_result = 1
                    break
            
            # 检查是否满足条件
            if operator == '==' and cmp_result != 0:
                return False, f"需要 =={required_ver}"
            elif operator == '>=' and cmp_result < 0:
                return False, f"需要 >={required_ver}"
            elif operator == '<' and cmp_result >= 0:
                return False, f"需要 <{required_ver}"
            elif operator == '>' and cmp_result <= 0:
                return False, f"需要 >{required_ver}"
            elif operator == '<=' and cmp_result > 0:
                return False, f"需要 <={required_ver}"
        
        return True, "✓"
    except Exception as e:
        return None, f"解析错误: {e}"

# 获取已安装的包
print("正在获取已安装包列表...")
installed = get_installed_packages_json()

# 读取 requirements.txt
print("正在读取 requirements.txt...")
print()
print("=" * 95)
print(f"{'包名':<35} {'要求版本':<30} {'已安装版本':<20} {'状态'}")
print("=" * 95)

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
        satisfies, status_msg = check_version_range(installed_ver, version_req)
        
        if satisfies is True:
            ok_count += 1
            status = "✓"
        elif satisfies is False:
            mismatch.append((pkg_name, version_req, installed_ver, status_msg))
            status = f"✗ ({status_msg})"
        else:
            status = status_msg
        
        print(f"{pkg_name:<35} {version_req:<30} {installed_ver:<20} {status}")

print("=" * 95)
print()
print(f"✓ 版本匹配: {ok_count} 个")
if mismatch:
    print(f"\n✗ 版本不匹配: {len(mismatch)} 个")
    for pkg, req, inst, msg in mismatch:
        print(f"  - {pkg}: 已安装 {inst}, {msg}")
if not_installed:
    print(f"\n⚠ 未安装: {len(not_installed)} 个")
    for pkg, req in not_installed:
        print(f"  - {pkg} ({req})")

if not mismatch and not not_installed:
    print("\n✓ 所有包版本检查通过！")
else:
    print(f"\n总计: {ok_count} 个通过, {len(mismatch)} 个不匹配, {len(not_installed)} 个未安装")

