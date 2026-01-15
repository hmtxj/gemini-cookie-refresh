import requests
import time
import re
import random
import string

BASE_URL = "https://api.duckmail.sbs"
PROXY_URL = "http://127.0.0.1:7890"

class DuckMailClient:
    def __init__(self):
        self.proxies = {"http": PROXY_URL, "https": PROXY_URL}
        self.email = None
        self.password = None
        self.account_id = None
        self.token = None

    def register(self):

        domain = "duckmail.sbs" # 更新默认域名
        try:
            # 尝试获取域名，支持代理失败降级
            try:
                resp = requests.get(f"{BASE_URL}/domains", proxies=self.proxies, timeout=10, verify=False)
            except:
                print("[Mail] Fetching domains via proxy failed, trying direct...")
                resp = requests.get(f"{BASE_URL}/domains", timeout=10, verify=False)

            if resp.status_code == 200:
                data = resp.json()
                if 'hydra:member' in data and len(data['hydra:member']) > 0:
                    domain = data['hydra:member'][0]['domain']
                    print(f"[Mail] Using domain: {domain}")
        except Exception as e:
            print(f"[Mail] Domain fetch error: {e}, using default: {domain}")

        rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        timestamp = str(int(time.time()))[-4:]
        self.email = f"t{timestamp}{rand_str}@{domain}"
        self.password = f"Pwd{rand_str}{timestamp}"

        print(f"[Mail] Register: {self.email}")

        def _do_register(use_proxy=True):
            p = self.proxies if use_proxy else None
            return requests.post(f"{BASE_URL}/accounts",
                               json={"address": self.email, "password": self.password},
                               proxies=p, timeout=15, verify=False)

        try:
            try:
                reg = _do_register(True)
            except Exception as e:
                print(f"[Mail] Proxy failed ({str(e)}), trying direct connection...")
                reg = _do_register(False)

            if reg.status_code in [200, 201]:
                self.account_id = reg.json().get('id')
                return True
            print(f"[Mail] Register Failed: {reg.status_code} - {reg.text}")
            return False
        except Exception as e:
            print(f"[Mail] Register Error: {str(e)}")
            return False

    def login(self):
        if not self.email: return False
        
        def _do_login(use_proxy=True):
            p = self.proxies if use_proxy else None
            return requests.post(f"{BASE_URL}/token",
                               json={"address": self.email, "password": self.password},
                               proxies=p, timeout=15, verify=False)

        try:
            try:
                login = _do_login(True)
            except:
                login = _do_login(False)

            if login.status_code == 200:
                self.token = login.json().get('token')
                return True
            return False
        except Exception as e:
            print(f"[Mail] Login Error: {str(e)}")
            return False

    def wait_for_code(self, timeout=300):
        if not self.token:
            if not self.login(): return None

        print(f"[Mail] Waiting for code ({timeout}s)...")
        headers = {"Authorization": f"Bearer {self.token}"}
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            try:
                resp = requests.get(f"{BASE_URL}/messages", headers=headers, proxies=self.proxies, timeout=10)
                if resp.status_code == 200:
                    msgs = resp.json().get('hydra:member', [])
                    if msgs:
                        msg_id = msgs[0]['id']
                        detail = requests.get(f"{BASE_URL}/messages/{msg_id}", headers=headers, proxies=self.proxies, timeout=10)
                        data = detail.json()
                        content = data.get('text') or data.get('html') or ""

                        code = self._extract_code(content)
                        if code:
                            print(f"[Mail] Code: {code}")
                            return code
            except:
                pass

            time.sleep(3)

        return None

    def _extract_code(self, text):
        pattern_context = r'(?:验证码|code|verification|passcode|pin).*?[:：]\s*([A-Za-z0-9]{4,8})\b'
        match = re.search(pattern_context, text, re.IGNORECASE | re.DOTALL)
        if match: return match.group(1)

        digits = re.findall(r'\b\d{6}\b', text)
        if digits: return digits[0]

        return None

    def delete(self):
        if not self.account_id or not self.token: return
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            requests.delete(f"{BASE_URL}/accounts/{self.account_id}", headers=headers, proxies=self.proxies)
        except:
            pass
