"""只保留在 result.csv 中有正确密码的账号"""
import json
import csv

# 读取 result.csv
email_to_pwd = {}
with open('result.csv', 'r', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        email_to_pwd[row['Account']] = row['Password']

print(f'CSV 中共 {len(email_to_pwd)} 个邮箱')

# 读取 accounts.json
with open('accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

print(f'JSON 中共 {len(accounts)} 个账号')

# 只保留有正确密码的账号
valid_accounts = []
for acc in accounts:
    email = acc.get('id')
    if email in email_to_pwd:
        acc['mail_password'] = email_to_pwd[email]  # 用正确密码
        valid_accounts.append(acc)
        print(f'[保留] {email}')
    else:
        print(f'[删除] {email} - 不在 CSV 中')

print(f'\n结果: {len(accounts)} -> {len(valid_accounts)} 个账号')

# 保存
with open('accounts.json', 'w', encoding='utf-8') as f:
    json.dump(valid_accounts, f, ensure_ascii=False, indent=2)

print('已保存')
