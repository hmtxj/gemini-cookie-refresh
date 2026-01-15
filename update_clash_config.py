"""
修改 Clash 配置文件
"""
import yaml
import sys

config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.yaml'

try:
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    config['mixed-port'] = 7890
    config['allow-lan'] = True
    config['mode'] = 'global'
    config['external-controller'] = '127.0.0.1:9090'
    
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
    
    print("✅ 配置已更新")
except Exception as e:
    print(f"❌ 配置更新失败: {e}")
    sys.exit(1)
