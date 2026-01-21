import time
import random
import csv
import os
import sys
from datetime import datetime
from DrissionPage import ChromiumPage, ChromiumOptions
from clash_manager import get_manager
from mail_client import DuckMailClient

CSV_FILE = "result.csv"
LOG_FILE = "log.txt"
PROXY_ADDR = "127.0.0.1:7890"

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_line = f"[{timestamp}] [{level}] {msg}"
    print(msg)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
    except:
        pass

def log_step(step_name, start_time, success=True):
    elapsed = (time.time() - start_time) * 1000
    status = "OK" if success else "FAIL"
    log(f"  [{status}] {step_name}: {elapsed:.0f}ms", "PERF")

def get_random_ua():
    versions = ["120.0.0.0", "121.0.0.0", "122.0.0.0", "123.0.0.0", "124.0.0.0"]
    v = random.choice(versions)
    return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{v} Safari/537.36"

def get_next_id():
    if not os.path.exists(CSV_FILE):
        return 1
    try:
        with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
            lines = list(csv.reader(f))
            if len(lines) <= 1: return 1
            last_row = lines[-1]
            if last_row and last_row[0].isdigit():
                return int(last_row[0]) + 1
    except:
        pass
    return 1

def save_account(email, password):
    file_exists = os.path.exists(CSV_FILE)
    next_id = get_next_id()
    date_str = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(CSV_FILE, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['ID', 'Account', 'Password', 'Date'])
            writer.writerow([next_id, email, password, date_str])
        log(f"[Save] {email}")
    except Exception as e:
        log(f"[Error] Save failed: {e}", "ERROR")

def save_account_with_cookies(email, password, cookies, current_url):
    """保存账号和 Cookie 到 accounts.json（gemini-business2api 格式）"""
    import json
    from datetime import timedelta
    from urllib.parse import urlparse, parse_qs
    
    ACCOUNTS_FILE = "accounts.json"
    
    # 1. 从 URL 获取 csesidx（查询参数）
    parsed_url = urlparse(current_url)
    query_params = parse_qs(parsed_url.query)
    csesidx = query_params.get('csesidx', [''])[0]
    
    # 2. 从 URL 路径获取 config_id（/cid/xxx 格式）
    config_id = ""
    path_parts = parsed_url.path.split('/')
    if 'cid' in path_parts:
        cid_index = path_parts.index('cid')
        if cid_index + 1 < len(path_parts):
            config_id = path_parts[cid_index + 1]
    
    # 3. 从 Cookie 获取 secure_c_ses 和 host_c_oses
    secure_c_ses = ""
    host_c_oses = ""
    expires_timestamp = None
    
    for c in cookies:
        name = c.get('name', '')
        value = c.get('value', '')
        if name == '__Secure-C_SES':
            secure_c_ses = value
            expires_timestamp = c.get('expirationDate') or c.get('expiry')
        elif name == '__Host-C_OSES':
            host_c_oses = value
    
    # 4. 计算过期时间
    expires_at = ""
    if expires_timestamp:
        try:
            # download.js: (ts - 43200) * 1000，这里反向计算
            from datetime import datetime as dt
            if isinstance(expires_timestamp, (int, float)):
                exp_dt = dt.fromtimestamp(expires_timestamp - 43200)
                expires_at = exp_dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            expires_at = (datetime.now() + timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")
    else:
        expires_at = (datetime.now() + timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")
    
    # 验证必填字段
    if not secure_c_ses or not csesidx or not config_id:
        log(f"[Warning] Missing required fields: secure_c_ses={bool(secure_c_ses)}, csesidx={bool(csesidx)}, config_id={bool(config_id)}", "WARN")
        log(f"[Debug] URL: {current_url}", "DEBUG")
        log(f"[Debug] Cookies: {[c.get('name') for c in cookies]}", "DEBUG")
    
    # 构造账号数据（与 gemini-business2api 格式一致，增加 mail_password 用于刷新）
    account_data = {
        "id": email,
        "mail_password": password,  # DuckMail 密码，刷新时需要
        "csesidx": csesidx,
        "config_id": config_id,
        "secure_c_ses": secure_c_ses,
        "host_c_oses": host_c_oses,
        "expires_at": expires_at
    }
    
    # 读取现有账号
    accounts = []
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                accounts = json.load(f)
        except:
            accounts = []
    
    accounts.append(account_data)
    
    # 保存
    try:
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(accounts, f, ensure_ascii=False, indent=2)
        log(f"[Save] Account saved to {ACCOUNTS_FILE}")
        log(f"[Info] csesidx: {csesidx[:20]}... | config_id: {config_id} | expires: {expires_at}")
    except Exception as e:
        log(f"[Error] Save account failed: {e}", "ERROR")

def run_browser_cycle():
    clash = get_manager()
    clash.start()

    node = clash.find_healthy_node()
    if not node:
        log("[Clash] No healthy node")
        time.sleep(5)
        return True

    mail = DuckMailClient()
    print("-" * 40)
    if not mail.register():
        log("[Mail] Register failed")
        return True

    log(f"[Mail] {mail.email}")

    co = ChromiumOptions()
    co.set_argument('--headless=new')  # 无头模式（不弹出窗口）
    co.set_argument('--incognito')
    co.set_argument(f'--proxy-server=http://{PROXY_ADDR}')
    co.set_user_agent(get_random_ua())
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--disable-gpu')  # 无头模式推荐
    co.set_argument('--no-sandbox')   # 无头模式推荐
    co.auto_port()

    page = None
    try:
        log("[Browser] Starting...")
        page = ChromiumPage(co)
        page.run_js("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        t = time.time()
        page.get("https://business.gemini.google/", timeout=30)
        time.sleep(3)
        log_step("Load page", t)

        t = time.time()
        email_input = page.ele('#email-input', timeout=3) or \
                      page.ele('css:input[name="loginHint"]', timeout=2) or \
                      page.ele('css:input[type="text"]', timeout=2)
        if not email_input:
            log("[Error] Email input not found", "ERROR")
            return True
        log_step("Find email input", t)

        t = time.time()
        email_input.click()
        time.sleep(0.3)
        email_input.clear()
        time.sleep(0.2)
        email_input.input(mail.email)
        time.sleep(0.3)
        page.run_js('''
            let el = document.querySelector("#email-input");
            if(el) {
                el.dispatchEvent(new Event("input", {bubbles: true}));
                el.dispatchEvent(new Event("change", {bubbles: true}));
                el.dispatchEvent(new Event("blur", {bubbles: true}));
            }
        ''')
        log_step("Input email", t)

        t = time.time()
        time.sleep(0.5)
        continue_btn = page.ele('tag:button@text():使用邮箱继续', timeout=2) or \
                       page.ele('tag:button', timeout=1)
        if continue_btn:
            try:
                continue_btn.click()
            except:
                continue_btn.click(by_js=True)
            log_step("Click continue", t)
        else:
            email_input.input('\n')
            log_step("Press enter", t)

        time.sleep(3)
        
        # 检测 signin-error 页面（被风控）
        curr_url = page.url
        page_text = page.html or ""
        if "signin-error" in curr_url or "请试试其他方法" in page_text or "Try another way" in page_text:
            log("⚠️ [Risk Control] Google rejected this email/IP, switching node...")
            # 强制切换节点
            clash.find_healthy_node()
            return False  # 返回 False 触发更长冷却

        t = time.time()
        code_input = None
        for _ in range(10):
            code_input = page.ele('css:input[name="pinInput"]', timeout=2) or \
                         page.ele('css:input[type="tel"]', timeout=1)
            if code_input:
                break
            time.sleep(0.5)

        if not code_input:
            log("[Error] Code input not found", "ERROR")
            return True
        log_step("Find code input", t)

        t = time.time()
        code = mail.wait_for_code(timeout=180)
        if not code:
            log("[Error] Code timeout", "ERROR")
            return True
        log_step(f"Get code {code}", t)

        t = time.time()
        code_input = page.ele('css:input[name="pinInput"]', timeout=3) or \
                     page.ele('css:input[type="tel"]', timeout=2)
        if not code_input:
            log("[Error] Code input expired", "ERROR")
            return True

        code_input.click()
        time.sleep(0.2)
        code_input.input(code)
        time.sleep(0.3)
        try:
            page.run_js('''
                let el = document.querySelector("input[name=pinInput]") || document.querySelector("input[type=tel]");
                if(el) {
                    el.dispatchEvent(new Event("input", {bubbles: true}));
                    el.dispatchEvent(new Event("change", {bubbles: true}));
                }
            ''')
        except:
            pass
        log_step("Input code", t)

        t = time.time()
        verify_btn = None
        buttons = page.eles('tag:button')
        for btn in buttons:
            btn_text = btn.text.strip() if btn.text else ""
            if btn_text and "重新" not in btn_text and "发送" not in btn_text and "resend" not in btn_text.lower():
                verify_btn = btn
                break

        if verify_btn:
            try:
                verify_btn.click()
            except:
                verify_btn.click(by_js=True)
            log_step("Click verify", t)
        else:
            code_input.input('\n')
            log_step("Press enter", t, success=False)

        # 等待登录完成（"正在登录..."消失）
        log("[Wait] Waiting for login to complete...")
        login_complete = False
        for _ in range(30):  # 最长等待 30 秒
            time.sleep(1)
            page_text = page.html or ""
            curr_url = page.url
            
            # 检查是否还在登录中
            if "正在登录" in page_text or "Signing in" in page_text or "Loading" in page_text:
                continue  # 还在登录，继续等待
            
            # 检查是否登录成功（出现名字输入框、聊天界面或 /cid/ URL）
            if '/cid/' in curr_url:
                log("[OK] Login complete, got /cid/ URL")
                login_complete = True
                break
            if "免费试用" in page_text or "全名" in page_text or "Trial" in page_text:
                log("[OK] Login complete, on setup page")
                login_complete = True
                break
            if page.ele('css:input[type="text"]', timeout=0.5):
                log("[OK] Login complete, found input field")
                login_complete = True
                break
        
        if not login_complete:
            log("[Warn] Login may not be complete, continuing anyway...")

        curr_url = page.url
        fail_keywords = ["verify", "oob", "error", "signin-error"]

        if any(kw in curr_url for kw in fail_keywords):
            log("❌ Failed")
        else:
            log("✅ Verification passed")
            
            # 检测并完成"免费试用商务版"设置页面
            time.sleep(2)
            page_text = page.html or ""
            if "免费试用" in page_text or "全名" in page_text or "/create" in curr_url or "Trial" in page_text:
                log("[Setup] Detected setup page, filling name...")
                try:
                    # 查找名字输入框
                    name_input = page.ele('css:input[type="text"]', timeout=3) or \
                                 page.ele('tag:input', timeout=2)
                    if name_input:
                        # 生成随机名字
                        first_names = ["James", "Michael", "David", "John", "Robert", "William", "Thomas", "Daniel"]
                        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson"]
                        random_name = f"{random.choice(first_names)} {random.choice(last_names)}"
                        
                        name_input.click()
                        time.sleep(0.3)
                        name_input.input(random_name)
                        log(f"[Setup] Entered name: {random_name}")
                        time.sleep(0.5)
                        
                        # 点击"同意并开始使用"按钮
                        agree_btn = page.ele('tag:button@text():同意并开始使用', timeout=3) or \
                                    page.ele('tag:button@text():同意', timeout=2) or \
                                    page.ele('tag:button@text():开始', timeout=2) or \
                                    page.ele('tag:button@text():Agree', timeout=2)
                        if agree_btn:
                            try:
                                agree_btn.click()
                            except:
                                agree_btn.click(by_js=True)
                            log("[Setup] Clicked agree button")
                            time.sleep(5)  # 等待跳转
                        else:
                            log("[Setup] Agree button not found, trying enter key")
                            name_input.input('\n')
                            time.sleep(3)
                except Exception as e:
                    log(f"[Setup] Setup step failed: {e}", "WARN")
            
            save_account(mail.email, mail.password)
            
            # 等待页面完全加载到带有 /cid/ 或 csesidx 的 URL
            log("[Wait] Waiting for session URL with /cid/...")
            got_cid = False
            for _ in range(15):  # 增加等待时间
                curr_url = page.url
                if '/cid/' in curr_url:
                    log(f"[URL] Got config_id URL: {curr_url[:80]}...")
                    got_cid = True
                    break
                time.sleep(1)
            
            # 如果 URL 中没有 /cid/，尝试点击进入工作区
            if not got_cid:
                log("[Retry] Trying to enter workspace...")
                try:
                    # 尝试点击常见的进入按钮
                    enter_btn = page.ele('tag:button@text():开始', timeout=2) or \
                                page.ele('tag:a@text():开始', timeout=1) or \
                                page.ele('tag:button@text():Chat', timeout=1) or \
                                page.ele('tag:a@text():Chat', timeout=1) or \
                                page.ele('css:a[href*="/chat"]', timeout=1) or \
                                page.ele('css:a[href*="/cid/"]', timeout=1)
                    if enter_btn:
                        try:
                            enter_btn.click()
                        except:
                            enter_btn.click(by_js=True)
                        log("[Retry] Clicked enter button")
                        time.sleep(5)
                        curr_url = page.url
                except Exception as e:
                    log(f"[Retry] Enter workspace failed: {e}", "WARN")
            
            # 再次检查是否有 /cid/
            if '/cid/' not in curr_url:
                log("[Retry] Still no /cid/, refreshing page...")
                try:
                    page.refresh()
                    time.sleep(3)
                    curr_url = page.url
                except:
                    pass
            
            # 提取浏览器 Cookie 并保存
            try:
                cookies = page.cookies()
                log(f"[Cookie] Found {len(cookies)} cookies")
                log(f"[URL] Final URL: {curr_url}")
                save_account_with_cookies(mail.email, mail.password, cookies, curr_url)
            except Exception as e:
                log(f"[Error] Cookie extraction failed: {e}", "ERROR")

    except Exception as e:
        log(f"[Exception] {e}", "ERROR")
    finally:
        if page:
            page.quit()
        log("[Browser] Closed")

    return True

if __name__ == "__main__":
    print("Starting... (Ctrl+C to stop)")
    try:
        while True:
            result = run_browser_cycle()
            if result:
                print("\nCooldown 3s...")
                time.sleep(3)
            else:
                # 被风控时增加冷却时间
                cooldown = random.randint(20, 40)
                print(f"\n⚠️ Risk control triggered, cooldown {cooldown}s...")
                time.sleep(cooldown)
    except KeyboardInterrupt:
        pass
