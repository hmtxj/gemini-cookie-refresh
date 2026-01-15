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
    
    # 选择一个可用的代理节点
    selected_proxy = None
    if 'proxies' in config and config['proxies']:
        # 优先选择香港/日本/新加坡节点
        good_proxies = []
        for p in config['proxies']:
            name = p.get('name', '')
            name_lower = name.lower()
            if any(k in name_lower for k in ['香港', 'hk', 'hong', '日本', 'jp', 'japan', '新加坡', 'sg', 'singapore']):
                good_proxies.append(name)
        
        if good_proxies:
            selected_proxy = random.choice(good_proxies)
        else:
            # 没有好节点就选第一个
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
