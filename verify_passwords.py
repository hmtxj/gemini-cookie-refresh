"""验证 accounts.json 中的密码是否与 result.csv 一致"""
import json
import csv

# 读取 result.csv
email_to_pwd = {}
with open('result.csv', 'r', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        email_to_pwd[row['Account']] = row['Password']

# 读取 accounts.json
with open('accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

# 验证
correct = 0
wrong = 0
not_found = 0

for acc in accounts:
    email = acc.get('id')
    my_pwd = acc.get('mail_password', '')
    
    if email in email_to_pwd:
        real_pwd = email_to_pwd[email]
        if my_pwd == real_pwd:
            correct += 1
            print(f'[✓] {email}')
        else:
            wrong += 1
            print(f'[✗] {email}')
            print(f'    推算: {my_pwd}')
            print(f'    实际: {real_pwd}')
    else:
        not_found += 1
        print(f'[?] {email} - 不在 result.csv 中，无法验证')

print(f'\n结果: 共 {len(accounts)} 个账号')
print(f'  ✓ 正确: {correct}')
print(f'  ✗ 错误: {wrong}')
print(f'  ? 无法验证: {not_found}')
