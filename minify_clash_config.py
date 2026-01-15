"""
精简 Clash 配置文件，只保留必要部分
"""
import yaml
import sys

input_file = sys.argv[1] if len(sys.argv) > 1 else 'local.yaml'
output_file = sys.argv[2] if len(sys.argv) > 2 else 'local_mini.yaml'

with open(input_file, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 只保留必要部分
mini_config = {
    'mixed-port': 7890,
    'allow-lan': True,
    'mode': 'global',
    'external-controller': '127.0.0.1:9090',
    'proxies': config.get('proxies', []),
    'proxy-groups': config.get('proxy-groups', []),
    'rules': ['MATCH,DIRECT']  # 简化规则，全局模式下不需要复杂规则
}

with open(output_file, 'w', encoding='utf-8') as f:
    yaml.dump(mini_config, f, allow_unicode=True)

# 检查文件大小
import os
size = os.path.getsize(output_file)
print(f"✅ 精简配置已保存到 {output_file}")
print(f"📊 文件大小: {size} 字节 ({size/1024:.1f} KB)")
print(f"📊 代理节点数: {len(mini_config['proxies'])}")

if size > 64000:
    print("⚠️ 文件仍然超过 64KB，可能需要进一步精简")
else:
    print("✅ 文件大小适合放入 GitHub Secret")
