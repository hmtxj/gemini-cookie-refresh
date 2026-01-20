"""
修改 Clash 配置文件
"""
import yaml
import sys
import random
import io

# 修复 Windows 编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.yaml'

try:
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    config['mixed-port'] = 7890
    config['allow-lan'] = True
    config['mode'] = 'global'  # 全局模式
    config['external-controller'] = '127.0.0.1:9090'
    
    # 删除规则，避免干扰
    if 'rules' in config:
        del config['rules']
    
    # 选择一个可用的代理节点（海外节点优先）
    selected_proxy = None
    overseas_proxies = []  # 收集所有海外节点
    
    if 'proxies' in config and config['proxies']:
        all_names = [p.get('name', '') for p in config['proxies']]
        
        # 筛选海外节点（美国、日本、新加坡、韩国、香港、台湾等）
        overseas_keywords = [
            # 美国
            '美国', 'us', 'usa', 'america', '洛杉矶', 'los angeles', '硅谷', 'silicon', '纽约', 'new york', '西雅图', 'seattle', '芝加哥', 'chicago',
            # 日本
            '日本', 'japan', 'jp', '东京', 'tokyo', '大阪', 'osaka',
            # 新加坡
            '新加坡', 'singapore', 'sg',
            # 韩国
            '韩国', 'korea', 'kr', '首尔', 'seoul',
            # 香港
            '香港', 'hong kong', 'hk',
            # 台湾
            '台湾', 'taiwan', 'tw',
            # 其他
            '德国', 'germany', '英国', 'uk', '法国', 'france', '加拿大', 'canada', '澳大利亚', 'australia'
        ]
        
        # 排除关键词（直连、广告等）
        exclude_keywords = ['直连', 'reject', '广告', '拦截', 'block', 'direct']
        
        for p in config['proxies']:
            name = p.get('name', '')
            name_lower = name.lower()
            # 排除特殊节点
            if any(k in name_lower for k in exclude_keywords):
                continue
            # 包含海外关键词
            if any(k in name_lower for k in overseas_keywords):
                overseas_proxies.append(name)
        
        print(f"📍 找到 {len(overseas_proxies)} 个海外节点")
        
        # 随机选择一个海外节点
        if overseas_proxies:
            selected_proxy = random.choice(overseas_proxies)
        else:
            # 如果没有找到海外节点，随机选择任意节点（排除特殊节点）
            print("⚠️ 未找到海外节点，随机选择任意节点")
            valid_proxies = [p.get('name', '') for p in config['proxies'] 
                           if not any(k in p.get('name', '').lower() for k in exclude_keywords)]
            if valid_proxies:
                selected_proxy = random.choice(valid_proxies)
            else:
                selected_proxy = config['proxies'][0]['name']
        
        print(f"✅ 选择代理节点: {selected_proxy}")
    
    # 创建 GLOBAL 代理组（global 模式必须有这个组）
    all_proxy_names = [p['name'] for p in config.get('proxies', [])]
    
    global_group = {
        'name': 'GLOBAL',
        'type': 'select',
        'proxies': [selected_proxy] + [n for n in all_proxy_names if n != selected_proxy] if selected_proxy else all_proxy_names
    }
    
    # 替换或添加 GLOBAL 组
    if 'proxy-groups' not in config:
        config['proxy-groups'] = []
    
    # 移除旧的 GLOBAL 组
    config['proxy-groups'] = [g for g in config['proxy-groups'] if g.get('name') != 'GLOBAL']
    # 添加新的 GLOBAL 组到最前面
    config['proxy-groups'].insert(0, global_group)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
    
    print("✅ 配置已更新")
    print(f"   mode: global")
    print(f"   GLOBAL 组首选: {selected_proxy}")
    
except Exception as e:
    print(f"❌ 配置更新失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
