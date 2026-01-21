"""合并 result.csv 中的密码到 accounts.json（有则添加，无则跳过）"""
import json
import csv

# 读取 result.csv 构建邮箱->密码映射
email_to_pwd = {}
with open('result.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        email_to_pwd[row['Account']] = row['Password']

print(f'CSV 中共 {len(email_to_pwd)} 个邮箱')

# 读取 accounts.json
with open('accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

# 合并密码（有则添加，无则跳过）
matched = 0
no_match = 0
for acc in accounts:
    email = acc.get('id')
    if email and email in email_to_pwd:
        acc['mail_password'] = email_to_pwd[email]
        matched += 1
        print(f'[OK] {email}')
    else:
        no_match += 1
        print(f'[跳过] {email} - 未找到密码')

print(f'\n结果: 共 {len(accounts)} 个账号')
print(f'  - 匹配成功: {matched}')
print(f'  - 无密码: {no_match}')

# 保存
with open('accounts.json', 'w', encoding='utf-8') as f:
    json.dump(accounts, f, ensure_ascii=False, indent=2)

print('\n已保存更新后的 accounts.json')

