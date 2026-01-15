import subprocess
import requests
import yaml
import time
import os
import atexit
import sys
import random
import urllib.parse

class ClashManager:
    def __init__(self, executable="clash.exe", config="local.yaml", runtime_config="config_runtime.yaml", port=7890, api_port=9090):
        self.executable = executable
        self.config = config
        self.runtime_config = runtime_config
        self.port = port
        self.api_port = api_port
        self.api_url = f"http://127.0.0.1:{api_port}"
        self.process = None
        self._prepare_config()

    def _prepare_config(self):
        if not os.path.exists(self.config):
            raise FileNotFoundError(f"Config not found: {self.config}")

        import re
        with open(self.config, 'r', encoding='utf-8') as f:
            content = f.read()

        # 使用正则表达式替换端口和控制器地址，保留原始格式
        content = re.sub(r'mixed-port:\s*\d+', f'mixed-port: {self.port}', content)
        content = re.sub(r'external-controller:\s*[^\n]+', f'external-controller: 127.0.0.1:{self.api_port}', content)

        with open(self.runtime_config, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[Clash] Config ready: {self.runtime_config}")

    def start(self):
        if self.process:
            return

        cmd = [self.executable, "-f", self.runtime_config]
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        for _ in range(10):
            try:
                requests.get(self.api_url, timeout=1)
                print("[Clash] Started")
                return
            except:
                time.sleep(1)

        print("[Clash] Start failed")
        self.stop()

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process = None

    def get_proxies(self):
        try:
            url = f"{self.api_url}/proxies"
            res = requests.get(url, timeout=5).json()
            return res['proxies']
        except:
            return {}

    def test_latency(self, proxy_name, timeout=5000):
        try:
            encoded_name = urllib.parse.quote(proxy_name)
            # 使用更稳定的测试地址
            url = f"{self.api_url}/proxies/{encoded_name}/delay?timeout={timeout}&url=http://www.gstatic.com/generate_204"
            res = requests.get(url, timeout=6)
            if res.status_code == 200:
                return res.json().get('delay', 0)
            return -1
        except:
            return -1

    def select_proxy(self, group_name, proxy_name):
        try:
            encoded_group = urllib.parse.quote(group_name)
            url = f"{self.api_url}/proxies/{encoded_group}"
            requests.put(url, json={"name": proxy_name}, timeout=5)
            print(f"[Clash] Switch: {proxy_name}")
            return True
        except:
            return False

    def find_healthy_node(self, group_name=None):
        print("[Clash] Finding healthy node...")
        proxies = self.get_proxies()

        if not group_name or group_name not in proxies:
            # 优先查找 Selector 类型的组
            for key, val in proxies.items():
                if val['type'] == 'Selector' and len(val.get('all', [])) > 0:
                    group_name = key
                    break

        if not group_name or group_name not in proxies:
            print("[Clash] No proxy group found")
            return None

        all_nodes = proxies[group_name]['all']
        # random.shuffle(all_nodes) # 不打乱，按顺序测

        skip_keywords = ["自动选择", "故障转移", "DIRECT", "REJECT", "剩余", "到期", "官网", "套餐", "重置"]

        for node in all_nodes:
            if any(kw in node for kw in skip_keywords):
                continue

            # 第一步：测延迟
            delay = self.test_latency(node)
            if delay > 0:
                self.select_proxy(group_name, node)
                print(f"   Testing [{node}] (Delay: {delay}ms)... ✅ PASS (Latency check only)")
                return node

                # 第二步：实测连接 (已跳过，仅依赖延迟测试)
                # try:
                #     time.sleep(2) # 等待切换生效
                # ...

        print("[Clash] No healthy node found")
        return None

_manager_instance = None

def get_manager():
    global _manager_instance
    if not _manager_instance:
        _manager_instance = ClashManager()
    return _manager_instance

@atexit.register
def cleanup():
    if _manager_instance:
        _manager_instance.stop()
