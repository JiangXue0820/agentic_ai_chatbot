#!/usr/bin/env python3
"""
检查虚拟环境中已安装包的版本是否与 requirements.txt 一致
"""
import re
import subprocess
import sys

def compare_version(installed_ver, operator, required_ver):
    """简单的版本比较函数"""
    try:
        installed_parts = [int(x) for x in installed_ver.split('.')]
        required_parts = [int(x) for x in required_ver.split('.')]
        
        # 补齐到相同长度
        max_len = max(len(installed_parts), len(required_parts))
        installed_parts += [0] * (max_len - len(installed_parts))
        required_parts += [0] * (max_len - len(required_parts))
        
        for i, j in zip(installed_parts, required_parts):
            if i < j:
                return -1
            elif i > j:
                return 1
        return 0
    except:
        # 如果解析失败，进行字符串比较
        return 0 if installed_ver == required_ver else (1 if installed_ver > required_ver else -1)

def check_specifier(installed_ver, spec):
    """检查版本是否满足规范"""
    if not spec:
        return True
    
    # 处理多个条件，如 ">=1.24.0,<2.0.0"
    conditions = [c.strip() for c in spec.split(',')]
    
    for condition in conditions:
        # 匹配操作符和版本号
        match = re.match(r'(==|>=|<=|>|<|!=|~=)\s*(.+)', condition)
        if not match:
            continue
        
        operator = match.group(1)
        required_ver = match.group(2).strip()
        
        cmp_result = compare_version(installed_ver, operator, required_ver)
        
        if operator == '==':
            if cmp_result != 0:
                return False
        elif operator == '>=':
            if cmp_result < 0:
                return False
        elif operator == '<=':
            if cmp_result > 0:
                return False
        elif operator == '>':
            if cmp_result <= 0:
                return False
        elif operator == '<':
            if cmp_result >= 0:
                return False
        elif operator == '!=':
            if cmp_result == 0:
                return False
    
    return True

def parse_requirements_line(line):
    """解析 requirements.txt 中的一行，返回包名和版本要求"""
    line = line.strip()
    # 跳过注释和空行
    if not line or line.startswith('#'):
        return None
    
    # 移除行内注释
    if '#' in line:
        line = line.split('#')[0].strip()
    
    # 处理带 [extras] 的情况，如 uvicorn[standard]
    if '[' in line:
        package_part = line.split('[')[0].strip()
    else:
        package_part = line
    
    # 提取包名和版本要求
    # 格式: package==1.0.0 或 package>=1.0.0,<2.0.0
    match = re.match(r'([a-zA-Z0-9_-]+(?:\[.*?\])?)\s*(.*)', package_part)
    if match:
        package_with_extras = match.group(1)
        # 提取包名（去掉 [extras]）
        package_name = re.sub(r'\[.*?\]', '', package_with_extras)
        version_spec = match.group(2).strip() if match.group(2) else None
        return package_name, version_spec
    
    # 如果没有版本要求，只有包名
    match = re.match(r'^([a-zA-Z0-9_-]+)', line)
    if match:
        return match.group(1), None
    
    return None

def get_installed_version(package_name):
    """获取已安装包的版本"""
    try:
        result = subprocess.run(
            ['pip', 'show', package_name],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            return None
        
        for line in result.stdout.split('\n'):
            if line.startswith('Version:'):
                return line.split(':', 1)[1].strip()
        return None
    except Exception:
        return None

def check_version_satisfies(installed_ver, version_spec):
    """检查已安装版本是否满足要求"""
    if not version_spec:
        return True, "无版本要求"
    
    if not installed_ver:
        return False, "未安装"
    
    try:
        satisfies = check_specifier(installed_ver, version_spec)
        status = "✓ 符合" if satisfies else "✗ 不符合"
        return satisfies, status
    except Exception as e:
        return None, f"版本要求解析错误: {e}"

def main():
    requirements_file = 'requirements.txt'
    
    print("=" * 80)
    print("检查 requirements.txt 与已安装包版本一致性")
    print("=" * 80)
    print()
    
    with open(requirements_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    results = []
    not_installed = []
    
    for line_num, line in enumerate(lines, 1):
        parsed = parse_requirements_line(line)
        if not parsed:
            continue
        
        package_name, version_spec = parsed
        installed_ver = get_installed_version(package_name)
        
        if not installed_ver:
            not_installed.append((package_name, version_spec, line_num))
            continue
        
        satisfies, status = check_version_satisfies(installed_ver, version_spec)
        results.append({
            'package': package_name,
            'required': version_spec or 'any',
            'installed': installed_ver,
            'satisfies': satisfies,
            'status': status,
            'line': line_num
        })
    
    # 显示结果
    print(f"{'包名':<30} {'要求版本':<25} {'已安装版本':<15} {'状态'}")
    print("-" * 80)
    
    all_ok = True
    for r in results:
        if r['satisfies'] is False:
            all_ok = False
            print(f"{r['package']:<30} {r['required']:<25} {r['installed']:<15} {r['status']}")
    
    # 显示符合要求的（可选，注释掉以简化输出）
    for r in results:
        if r['satisfies']:
            print(f"{r['package']:<30} {r['required']:<25} {r['installed']:<15} {r['status']}")
    
    # 显示未安装的包
    if not_installed:
        print()
        print("-" * 80)
        print("⚠ 未安装的包:")
        for pkg, ver_spec, line_num in not_installed:
            print(f"  - {pkg:<30} 要求: {ver_spec or 'any':<25} (line {line_num})")
        all_ok = False
    
    print()
    print("=" * 80)
    if all_ok and not not_installed:
        print("✓ 所有包版本检查通过！")
    else:
        print("⚠ 发现版本不一致或未安装的包")
    print("=" * 80)
    
    return 0 if all_ok and not not_installed else 1

if __name__ == '__main__':
    sys.exit(main())

