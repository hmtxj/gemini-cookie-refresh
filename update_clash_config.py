"""
修改 Clash 配置文件
"""
import yaml
import sys
import random

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
    
    # 选择一个可用的代理节点（只使用美国节点）
    selected_proxy = None
    us_proxies = []  # 收集所有美国节点
    
    if 'proxies' in config and config['proxies']:
        all_names = [p.get('name', '') for p in config['proxies']]
        
        # 筛选美国节点
        us_keywords = ['美国', 'us', 'usa', 'america', 'united states', '洛杉矶', 'los angeles', '硅谷', 'silicon', '纽约', 'new york', '西雅图', 'seattle', '芝加哥', 'chicago']
        
        for p in config['proxies']:
            name = p.get('name', '')
            name_lower = name.lower()
            if any(k in name_lower for k in us_keywords):
                us_proxies.append(name)
        
        print(f"📍 找到 {len(us_proxies)} 个美国节点")
        
        # 随机选择一个美国节点
        if us_proxies:
            selected_proxy = random.choice(us_proxies)
        else:
            # 如果没有美国节点，选择第一个可用节点
            print("⚠️ 未找到美国节点，使用第一个可用节点")
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
