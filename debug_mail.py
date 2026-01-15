import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://api.duckmail.sbs"
PROXY_URL = "http://127.0.0.1:17890"
PROXIES = {"http": PROXY_URL, "https": PROXY_URL}

def test_domains(use_proxy=True):
    mode = "PROXY" if use_proxy else "DIRECT"
    print(f"\n--- Testing {mode} ---")
    try:
        if use_proxy:
            resp = requests.get(f"{BASE_URL}/domains", proxies=PROXIES, timeout=10, verify=False)
        else:
            resp = requests.get(f"{BASE_URL}/domains", timeout=10, verify=False)
        
        print(f"Status: {resp.status_code}")
        print(f"Content: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

test_domains(use_proxy=True)
test_domains(use_proxy=False)
