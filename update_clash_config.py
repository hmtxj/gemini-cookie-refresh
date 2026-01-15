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
    config['mode'] = 'rule'  # 使用规则模式
    config['external-controller'] = '127.0.0.1:9090'
    
    # 尝试选择一个可用的代理节点
    if 'proxies' in config and config['proxies']:
        # 优先选择香港或日本节点
        good_proxies = []
        for p in config['proxies']:
            name = p.get('name', '').lower()
            if any(k in name for k in ['香港', 'hk', 'hong', '日本', 'jp', 'japan', '新加坡', 'sg', 'singapore']):
                good_proxies.append(p['name'])
        
        if good_proxies:
            selected = random.choice(good_proxies)
            print(f"✅ 选择代理节点: {selected}")
            
            # 修改 proxy-groups 使用选中的节点
            if 'proxy-groups' in config:
                for group in config['proxy-groups']:
                    if group.get('type') == 'select' and 'proxies' in group:
                        if selected in group['proxies']:
                            # 把选中的节点放到第一位
                            group['proxies'].remove(selected)
                            group['proxies'].insert(0, selected)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
    
    print("✅ 配置已更新")
except Exception as e:
    print(f"❌ 配置更新失败: {e}")
    sys.exit(1)
