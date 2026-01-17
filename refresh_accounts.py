"""
Gemini Business 账号刷新脚本
用于刷新 accounts.json 中的 Cookie，延长账号有效期

使用方法（本地）：
    python refresh_accounts.py

使用方法（GitHub Actions）：
    自动运行，无需手动操作
"""
import json
import os
import time
import requests
from datetime import datetime, timedelta

# 配置
ACCOUNTS_FILE = "accounts.json"
DUCKMAIL_API = "https://api.duckmail.sbs"

# 可选：代理配置（GitHub Actions 上可能需要）
PROXY_URL = os.environ.get("PROXY_URL", None)

# 数据库配置
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()


def log(msg):
    """打印带时间戳的日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def is_database_enabled():
    """检查是否启用数据库模式"""
    return bool(DATABASE_URL)


def db_load_accounts():
    """从数据库加载账号"""
    if not DATABASE_URL:
        return None
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT value FROM kv_store WHERE key = 'accounts'")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            data = row[0]
            if isinstance(data, str):
                return json.loads(data)
            return data
        return []
    except Exception as e:
        log(f"❌ 数据库读取失败: {e}")
        return None


def db_save_accounts(accounts):
    """保存账号到数据库"""
    if not DATABASE_URL:
        return False
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        # 确保表存在
        cur.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value JSONB NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 插入或更新
        cur.execute("""
            INSERT INTO kv_store (key, value, updated_at)
            VALUES ('accounts', %s, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = CURRENT_TIMESTAMP
        """, (json.dumps(accounts, ensure_ascii=False),))
        conn.commit()
        cur.close()
        conn.close()
        log(f"✅ 已保存 {len(accounts)} 个账号到数据库")
        return True
    except Exception as e:
        log(f"❌ 数据库写入失败: {e}")
        return False


def load_accounts():
    """加载账号（优先数据库，fallback 到文件）"""
    if is_database_enabled():
        accounts = db_load_accounts()
        if accounts is not None:
            # 如果数据库是空的，尝试从文件加载并初始化数据库
            if len(accounts) == 0 and os.path.exists(ACCOUNTS_FILE):
                log("📦 数据库为空，从文件初始化...")
                with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                    file_accounts = json.load(f)
                if file_accounts:
                    log(f"📦 从文件加载了 {len(file_accounts)} 个账号，写入数据库...")
                    db_save_accounts(file_accounts)
                    return file_accounts
            log(f"📦 从数据库加载了 {len(accounts)} 个账号")
            return accounts
    # 文件模式
    if not os.path.exists(ACCOUNTS_FILE):
        log(f"❌ {ACCOUNTS_FILE} 不存在")
        return []
    with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_accounts(accounts):
    """保存账号（同时保存到数据库和文件）"""
    # 保存到文件
    with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)
    log(f"✅ 已保存 {len(accounts)} 个账号到 {ACCOUNTS_FILE}")
    
    # 如果启用数据库，同时保存到数据库
    if is_database_enabled():
        db_save_accounts(accounts)


def get_remaining_hours(expires_at):
    """计算剩余小时数"""
    if not expires_at:
        return None
    try:
        expire_time = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
        remaining = (expire_time - datetime.now()).total_seconds() / 3600
        return remaining
    except:
        return None


def duckmail_login(email, password):
    """登录 DuckMail 获取 Token"""
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    try:
        resp = requests.post(
            f"{DUCKMAIL_API}/token",
            json={"address": email, "password": password},
            proxies=proxies,
            timeout=15,
            verify=False
        )
        if resp.status_code == 200:
            return resp.json().get('token')
        else:
            log(f"   DuckMail 登录失败: {resp.status_code}")
            return None
    except Exception as e:
        log(f"   DuckMail 登录错误: {e}")
        return None


def wait_for_verification_code(email, token, timeout=180):
    """从 DuckMail 等待验证码"""
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    headers = {"Authorization": f"Bearer {token}"}
    start_time = time.time()
    
    log(f"   等待验证码... (最长 {timeout} 秒)")
    
    poll_count = 0
    while (time.time() - start_time) < timeout:
        poll_count += 1
        try:
            resp = requests.get(
                f"{DUCKMAIL_API}/messages",
                headers=headers,
                proxies=proxies,
                timeout=10,
                verify=False
            )
            if resp.status_code == 200:
                msgs = resp.json().get('hydra:member', [])
                if poll_count == 1 or poll_count % 10 == 0:
                    log(f"   [轮询 {poll_count}] 收到 {len(msgs)} 封邮件")
                if msgs:
                    msg_id = msgs[0]['id']
                    detail = requests.get(
                        f"{DUCKMAIL_API}/messages/{msg_id}",
                        headers=headers,
                        proxies=proxies,
                        timeout=10,
                        verify=False
                    )
                    data = detail.json()
                    content = data.get('text') or data.get('html') or ""
                    subject = data.get('subject', '')
                    
                    if poll_count == 1:
                        log(f"   [邮件标题] {subject[:50]}...")
                        log(f"   [邮件内容长度] {len(content)} 字符")
                        # 打印邮件内容的前 200 个字符用于调试
                        if content:
                            log(f"   [邮件内容前200字符] {content[:200]}...")
                    
                    # 提取验证码 - 多种方式尝试
                    import re
                    
                    # 方式1: 严格匹配6位数字
                    digits = re.findall(r'\b\d{6}\b', content)
                    if digits:
                        log(f"   ✅ 找到验证码: {digits[0]}")
                        return digits[0]
                    
                    # 方式2: 匹配任意6位连续数字
                    digits = re.findall(r'(\d{6})', content)
                    if digits:
                        log(f"   ✅ 找到验证码: {digits[0]}")
                        return digits[0]
                    
                    # 方式3: 从标题中提取
                    digits = re.findall(r'(\d{6})', subject)
                    if digits:
                        log(f"   ✅ 从标题找到验证码: {digits[0]}")
                        return digits[0]
                    
                    # 如果是第一次轮询且没找到，打印警告
                    if poll_count == 1:
                        log(f"   [警告] 邮件中未找到6位验证码")
            else:
                if poll_count == 1:
                    log(f"   [轮询失败] HTTP {resp.status_code}")
        except Exception as e:
            if poll_count == 1:
                log(f"   [轮询错误] {e}")
        
        time.sleep(3)
    
    log("   ⚠️ 验证码超时")
    return None


def refresh_single_account(account):
    """
    刷新单个账号的 Cookie
    
    返回: (success: bool, new_account_data: dict or None)
    """
    email = account.get('id')
    mail_password = account.get('mail_password')
    
    if not email or not mail_password:
        log(f"   ❌ 缺少邮箱或密码")
        return False, None
    
    log(f"   尝试登录 DuckMail...")
    token = duckmail_login(email, mail_password)
    if not token:
        return False, None
    
    
    log(f"   ✅ DuckMail 登录成功")
    
    # 使用 DrissionPage 进行浏览器自动化（基于真实 Chrome，更难被检测）
    try:
        from DrissionPage import ChromiumPage, ChromiumOptions
    except ImportError:
        log("   ❌ 需要安装 DrissionPage: pip install DrissionPage")
        return False, None
    
    # 配置浏览器
    co = ChromiumOptions()
    # 不使用 headless 模式，让 Xvfb 虚拟显示器运行真实 GUI
    # co.set_argument('--headless=new')
    co.set_argument('--incognito')
    if PROXY_URL:
        log(f"   使用代理: {PROXY_URL}")
        co.set_argument(f'--proxy-server={PROXY_URL}')
    co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--disable-gpu')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.auto_port()
    
    page = None
    try:
        page = ChromiumPage(co)
        page.run_js("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # 创建截图目录
        os.makedirs("screenshots", exist_ok=True)
        account_id = email.split("@")[0][:10]
        
        max_retries = 3
        for attempt in range(max_retries):
            # 访问 Gemini Business
            log(f"   打开 Gemini Business... (尝试 {attempt + 1}/{max_retries})")
            page.get("https://business.gemini.google/", timeout=30)
            time.sleep(5)  # 增加等待时间，确保页面完全加载
            page.get_screenshot(path=f"screenshots/{account_id}_01_landing.png")
            
            # 输入邮箱
            log("   输入邮箱...")
            email_input = page.ele('#email-input', timeout=5) or \
                          page.ele('css:input[name="loginHint"]', timeout=3) or \
                          page.ele('css:input[type="text"]', timeout=3)
            if not email_input:
                log("   ❌ 找不到邮箱输入框")
                return False, None
            
            # 点击输入框，等待，输入邮箱
            email_input.click()
            time.sleep(0.5)
            email_input.clear()
            time.sleep(0.3)
            email_input.input(email)
            time.sleep(1)  # 等待输入完成
            
            # 触发 JavaScript 事件（关键！模拟真实用户输入）
            try:
                page.run_js('''
                    let el = document.querySelector("#email-input") || document.querySelector("input[type=text]");
                    if(el) {
                        el.dispatchEvent(new Event("input", {bubbles: true}));
                        el.dispatchEvent(new Event("change", {bubbles: true}));
                        el.dispatchEvent(new Event("blur", {bubbles: true}));
                    }
                ''')
            except:
                pass
            time.sleep(1)
            page.get_screenshot(path=f"screenshots/{account_id}_02_email_filled.png")
            
            # 点击继续按钮
            log("   点击'使用邮箱继续'按钮...")
            continue_btn = page.ele('tag:button@text():使用邮箱继续', timeout=3) or \
                           page.ele('tag:button@text():Continue with email', timeout=2) or \
                           page.ele('css:button[jsname]', timeout=2) or \
                           page.ele('css:button', timeout=2)
            
            if continue_btn:
                try:
                    continue_btn.click()
                    log("   ✅ 已点击按钮")
                except:
                    try:
                        continue_btn.click(by_js=True)
                        log("   ✅ JS 点击成功")
                    except:
                        email_input.input('\n')
                        log("   尝试回车提交")
            else:
                email_input.input('\n')
                log("   未找到按钮，回车提交")
            
            time.sleep(6)  # 等待页面加载（关键！不能太短）
            page.get_screenshot(path=f"screenshots/{account_id}_03_after_continue.png")
            
            # 检查是否遇到错误页面
            page_html = page.html or ""
            if "请试试其他方法" in page_html or "Let's try something else" in page_html:
                log(f"   ⚠️ 遇到服务器错误，重试...")
                page.get_screenshot(path=f"screenshots/{account_id}_error_{attempt+1}.png")
                
                if attempt >= max_retries - 1:
                    log(f"   ❌ 重试 {max_retries} 次仍失败，跳过此账号")
                    if page:
                        page.quit()
                    return False, None
                
                # 等待后重试
                time.sleep(3)
                continue
            
            # 等待验证码输入框
            log("   等待验证码输入框... (最长 30 秒)")
            code_input = None
            for _ in range(30):
                code_input = page.ele('css:input[name="pinInput"]', timeout=1) or \
                             page.ele('css:input[type="tel"]', timeout=1)
                if code_input:
                    break
                time.sleep(1)
            
            if code_input:
                break  # 找到验证码输入框，退出重试循环
            else:
                if attempt < max_retries - 1:
                    log(f"   ⚠️ 验证码输入框未出现，重试...")
                    continue
                else:
                    log(f"   ❌ 验证码输入框始终未出现")
                    if page:
                        page.quit()
                    return False, None
        
        # 从 DuckMail 获取验证码
        code = wait_for_verification_code(email, token)
        if not code:
            if page:
                page.quit()
            return False, None
        
        # 输入验证码
        log("   输入验证码...")
        code_input.click()
        code_input.clear()
        code_input.input(code)
        time.sleep(0.5)
        
        # 点击验证按钮
        buttons = page.eles('css:button')
        for btn in buttons:
            btn_text = btn.text or ""
            if "重新" not in btn_text and "发送" not in btn_text:
                btn.click()
                break
        
        # 等待登录完成
        log("   等待登录完成...")
        for _ in range(30):
            time.sleep(1)
            page_text = page.html
            current_url = page.url
            
            if "正在登录" in page_text or "Signing in" in page_text:
                continue
            
            if '/cid/' in current_url or "免费试用" in page_text:
                break
        
        # 提取 Cookie 和 URL 参数
        current_url = page.url
        cookies = page.cookies()
        
        # 从 URL 提取 csesidx 和 config_id
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(current_url)
        query = parse_qs(parsed.query)
        
        csesidx = query.get('csesidx', [''])[0]
        config_id = ""
        path_parts = parsed.path.split('/')
        if 'cid' in path_parts:
            idx = path_parts.index('cid')
            if idx + 1 < len(path_parts):
                config_id = path_parts[idx + 1]
        
        # 从 Cookie 提取 secure_c_ses 和 host_c_oses
        secure_c_ses = ""
        host_c_oses = ""
        for c in cookies:
            name = c.get('name', '')
            value = c.get('value', '')
            if name == '__Secure-C_SES':
                secure_c_ses = value
            elif name == '__Host-C_OSES':
                host_c_oses = value
        
        if not secure_c_ses or not csesidx:
            log("   ❌ 无法提取必要信息")
            if page:
                page.quit()
            return False, None
        
        # 构造新的账号数据
        new_account = {
            "id": email,
            "mail_password": mail_password,
            "csesidx": csesidx,
            "config_id": config_id or account.get('config_id', ''),
            "secure_c_ses": secure_c_ses,
            "host_c_oses": host_c_oses,
            "expires_at": (datetime.now() + timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")
        }
        
        log("   ✅ 刷新成功！")
        if page:
            page.quit()
        return True, new_account
        
    except Exception as e:
        log(f"   ❌ 浏览器操作失败: {e}")
        if page:
            page.quit()
        return False, None


def refresh_all_accounts(force=False):
    """
    刷新所有需要刷新的账号
    
    Args:
        force: 是否强制刷新所有账号（忽略过期时间检查）
    """
    accounts = load_accounts()
    if not accounts:
        log("没有账号需要刷新")
        return
    
    log(f"共有 {len(accounts)} 个账号")
    updated_accounts = []
    
    for i, account in enumerate(accounts, 1):
        email = account.get('id', f'账号{i}')
        remaining = get_remaining_hours(account.get('expires_at'))
        
        log(f"\n[{i}/{len(accounts)}] {email}")
        
        # 检查是否需要刷新
        if not force and remaining and remaining > 2:
            log(f"   跳过（剩余 {remaining:.1f} 小时，无需刷新）")
            updated_accounts.append(account)
            continue
        
        if not account.get('mail_password'):
            log(f"   ⚠️ 无 mail_password，无法刷新")
            updated_accounts.append(account)
            continue
        
        # 尝试刷新
        success, new_account = refresh_single_account(account)
        if success and new_account:
            updated_accounts.append(new_account)
        else:
            log(f"   保留原账号数据")
            updated_accounts.append(account)
        
        # 稍微等待，避免请求过快
        time.sleep(2)
    
    # 保存更新后的账号
    save_accounts(updated_accounts)


def push_to_huggingface(hf_token, space_id):
    """
    推送 accounts.json 到 Hugging Face Space
    
    Args:
        hf_token: HF Access Token
        space_id: Space ID，如 "hmtxj/gemini-business2api"
    """
    try:
        from huggingface_hub import HfApi
        api = HfApi(token=hf_token)
        
        log(f"推送到 HF Space: {space_id}...")
        api.upload_file(
            path_or_fileobj=ACCOUNTS_FILE,
            path_in_repo="data/accounts.json",
            repo_id=space_id,
            repo_type="space"
        )
        log("✅ 推送成功！")
    except Exception as e:
        log(f"❌ 推送失败: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="刷新 Gemini Business 账号 Cookie")
    parser.add_argument("--force", action="store_true", help="强制刷新所有账号")
    parser.add_argument("--push", action="store_true", help="刷新后推送到 HF")
    args = parser.parse_args()
    
    log("=" * 50)
    log("Gemini Business 账号刷新脚本")
    log("=" * 50)
    
    # 刷新账号
    refresh_all_accounts(force=args.force)
    
    # 推送到 HF（如果配置了环境变量）
    if args.push:
        hf_token = os.environ.get("HF_TOKEN")
        space_id = os.environ.get("HF_SPACE_ID")
        if hf_token and space_id:
            push_to_huggingface(hf_token, space_id)
        else:
            log("⚠️ 未配置 HF_TOKEN 或 HF_SPACE_ID 环境变量")
