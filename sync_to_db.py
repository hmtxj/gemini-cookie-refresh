"""
直接把 accounts.json 同步到数据库
"""
import json
import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
ACCOUNTS_FILE = "accounts.json"

def main():
    if not DATABASE_URL:
        print("❌ 未设置 DATABASE_URL")
        return
    
    # 读取本地 accounts.json
    if not os.path.exists(ACCOUNTS_FILE):
        print(f"❌ {ACCOUNTS_FILE} 不存在")
        return
    
    with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
        accounts = json.load(f)
    
    print(f"📦 从文件加载了 {len(accounts)} 个账号")
    
    # 写入数据库
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
        
        print(f"✅ 已同步 {len(accounts)} 个账号到数据库")
        
    except Exception as e:
        print(f"❌ 数据库写入失败: {e}")

if __name__ == "__main__":
    main()
