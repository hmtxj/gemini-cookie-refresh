"""
直接把 accounts.json 同步到数据库，并调用 API 刷新 2api 内存
"""
import json
import os
import requests
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
ACCOUNTS_FILE = "accounts.json"
HF_SPACE_URL = os.environ.get("HF_SPACE_URL", "").strip()  # 例如 https://hmtxj-gemini-business3api.hf.space
ADMIN_KEY = os.environ.get("ADMIN_KEY", "").strip()


def sync_to_database(accounts):
    """写入数据库"""
    try:
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
        
        print(f"✅ 已同步 {len(accounts)} 个账号到数据库", flush=True)
        return True
        
    except Exception as e:
        print(f"❌ 数据库写入失败: {e}", flush=True)
        return False


def trigger_reload(accounts):
    """调用 2api 的 API 触发热重载"""
    if not HF_SPACE_URL or not ADMIN_KEY:
        print("⚠️ 未配置 HF_SPACE_URL 或 ADMIN_KEY，跳过热重载", flush=True)
        return False
    
    try:
        # 先登录获取 session
        session = requests.Session()
        login_resp = session.post(
            f"{HF_SPACE_URL}/login",
            data={"admin_key": ADMIN_KEY},
            timeout=30
        )
        
        if login_resp.status_code != 200:
            print(f"❌ 登录失败: {login_resp.status_code}", flush=True)
            return False
        
        print("✅ 登录成功", flush=True)
        
        # 调用 PUT /admin/accounts-config 更新配置并触发热重载
        update_resp = session.put(
            f"{HF_SPACE_URL}/admin/accounts-config",
            json=accounts,
            timeout=30
        )
        
        if update_resp.status_code == 200:
            result = update_resp.json()
            print(f"✅ 热重载成功: {result.get('message', '')}", flush=True)
            return True
        else:
            print(f"❌ 热重载失败: {update_resp.status_code} - {update_resp.text}", flush=True)
            return False
            
    except Exception as e:
        print(f"❌ 热重载请求失败: {e}", flush=True)
        return False


def main():
    if not DATABASE_URL:
        print("❌ 未设置 DATABASE_URL", flush=True)
        return
    
    # 读取本地 accounts.json
    if not os.path.exists(ACCOUNTS_FILE):
        print(f"❌ {ACCOUNTS_FILE} 不存在", flush=True)
        return
    
    with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
        accounts = json.load(f)
    
    print(f"📦 从文件加载了 {len(accounts)} 个账号", flush=True)
    
    # 1. 同步到数据库
    if not sync_to_database(accounts):
        return
    
    # 2. 触发 2api 热重载
    trigger_reload(accounts)


if __name__ == "__main__":
    main()
