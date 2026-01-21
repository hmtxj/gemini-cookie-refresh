"""根据邮箱格式推算密码并添加到 accounts.json"""
import json
import re

# 读取 accounts.json
with open('accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

# 根据邮箱格式推算密码
# 邮箱格式: t{timestamp}{rand_str}@domain
# 密码格式: Pwd{rand_str}{timestamp}
for acc in accounts:
    email = acc.get('id', '')
    if '@' in email:
        local_part = email.split('@')[0]  # t68895m3vagfurs
        if local_part.startswith('t'):
            local_part = local_part[1:]  # 68895m3vagfurs
            # 找到数字和字母的分界点
            match = re.match(r'^(\d+)(.+)$', local_part)
            if match:
                timestamp = match.group(1)  # 68895
                rand_str = match.group(2)   # m3vagfurs
                password = f'Pwd{rand_str}{timestamp}'
                acc['mail_password'] = password
                print(f'{email} -> {password}')

# 保存
with open('accounts.json', 'w', encoding='utf-8') as f:
    json.dump(accounts, f, ensure_ascii=False, indent=2)

print(f'\n完成！已为 {len(accounts)} 个账号添加密码')
