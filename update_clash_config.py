"""
修改 Clash 配置文件
"""
import yaml
import sys
import random

# 强制 UTF-8 输出，防止 Windows 控制台打印 Emoji 报错
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    # Python 3.6+ 支持 reconfigure，旧版本可能不支持，但在 GitHub Actions (Py3.11) 上没问题
    pass

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
    
    # 选择一个可用的代理节点（规避不可用地区）
    selected_proxy = None
    available_proxies = []
    
    # 🔥 无法访问 Google/Gemini 的地区关键词（必须规避）
    blocked_keywords = [
        '中国', 'china', 'cn', '北京', '上海', '广州', '深圳',
        '俄罗斯', 'russia', 'ru', '莫斯科',
        '朝鲜', 'north korea', 'kp',
        '伊朗', 'iran', 'ir',
        '叙利亚', 'syria', 'sy',
        '古巴', 'cuba', 'cu',
        '克里米亚', 'crimea',
    ]
    
    # 🔥 无效节点类型关键词
    skip_keywords = ['自动选择', '故障转移', 'direct', 'reject', '剩余', '到期', '官网', '套餐', '重置', '订阅', '流量', '过期']
    
    if 'proxies' in config and config['proxies']:
        for p in config['proxies']:
            name = p.get('name', '')
            name_lower = name.lower()
            
            # 跳过无效节点类型
            if any(k in name_lower for k in skip_keywords):
                continue
            
            # 跳过不可用地区节点
            is_blocked = any(k.lower() in name_lower for k in blocked_keywords)
            if is_blocked:
                continue
            
            available_proxies.append(name)
        
        print(f"📍 找到 {len(available_proxies)} 个可用节点（已排除不可用地区）")
        
        # 随机选择一个可用节点
        if available_proxies:
            selected_proxy = random.choice(available_proxies)
        else:
            print("⚠️ 未找到可用节点，使用第一个节点")
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
