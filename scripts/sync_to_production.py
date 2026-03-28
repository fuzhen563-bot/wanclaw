#!/usr/bin/env python3
"""
WanClaw → ClawHub (生产环境) 插件同步脚本
用法: python3 sync_to_production.py

将本地 76 个官方插件同步到 wanhub.vanyue.cn
"""

import json
import sys
import os
from pathlib import Path

# ─── 配置 ───────────────────────────────────────────────────────────────────
PRODUCTION_API = "https://wanhub.vanyue.cn"
SUMMARY_FILE = Path("/data/wanclaw/wanclaw/wanclaw/plugins/official/_all_plugins_summary.json")
WANCLAW_PLUGINS_DIR = Path("/data/wanclaw/wanclaw/wanclaw/plugins/official")
# ───────────────────────────────────────────────────────────────────────────

def load_summary():
    if not SUMMARY_FILE.exists():
        print(f"❌ 找不到汇总文件: {SUMMARY_FILE}")
        sys.exit(1)
    with open(SUMMARY_FILE, encoding="utf-8") as f:
        return json.load(f)

def check_api_health():
    """检查生产 API 是否可达"""
    try:
        import urllib.request
        req = urllib.request.Request(f"{PRODUCTION_API}/api/community/plugins/list?per_page=1")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            print(f"✅ 生产 API 可达，当前插件数: {data.get('total', 0)}")
            return True
    except Exception as e:
        print(f"❌ 无法连接生产 API: {e}")
        return False

def sync_via_api(plugins: dict):
    """通过 API 逐个添加插件（绕过文件系统依赖）"""
    try:
        import urllib.request
        import urllib.error
    except ImportError:
        print("❌ 需要 urllib (Python3 内置)")
        return

    added = 0
    updated = 0
    errors = 0

    # 先获取现有插件列表，避免重复
    try:
        req = urllib.request.Request(f"{PRODUCTION_API}/api/community/plugins/list?per_page=500")
        with urllib.request.urlopen(req, timeout=15) as resp:
            existing = json.loads(resp.read()).get("plugins", [])
        existing_ids = {p["plugin_id"] for p in existing}
        print(f"   现有插件: {len(existing_ids)} 个")
    except Exception as e:
        print(f"   ⚠️  无法获取现有插件列表: {e}")
        existing_ids = set()

    for plugin_id, pj in plugins.items():
        category_map = {
            "ecommerce": "电商自动化",
            "im": "IM智能客服",
            "office": "办公RPA",
            "ai": "AI增强",
            "data": "数据统计",
            "ops": "系统运维",
            "workflow": "工作流",
            "ecosystem": "插件生态",
        }
        db_category = category_map.get(pj.get("category", ""), pj.get("category", ""))

        payload = json.dumps({
            "plugin_id": plugin_id,
            "plugin_name": pj.get("plugin_name", ""),
            "description": pj.get("description", ""),
            "author": pj.get("author", "WanClaw"),
            "version": pj.get("version", "2.0.0"),
            "plugin_type": pj.get("plugin_type", "skill"),
            "category": db_category,
            "compatible_wanclaw_version": pj.get("compatible_wanclaw_version", ">=2.0.0"),
            "entry_file": "main.py",
            "permissions": pj.get("permissions", []),
            "review_status": "approved",
        }).encode("utf-8")

        # 尝试通过 admin API 添加
        # 如果需要 token，这里暂时用公开的 sync endpoint
        url = f"{PRODUCTION_API}/api/community/plugins/upload"

        # 由于 upload 需要文件上传，我们使用一个 workaround：
        # 直接通过 GET 参数 + 内部机制
        # 但更可靠的是直接 DB 操作 → 需要 SSH 到服务器

        # 标记 - 稍后需要手动处理
        if plugin_id not in existing_ids:
            added += 1
        else:
            updated += 1

    print(f"\n📊 统计: 新增 {added}, 更新 {updated}, 错误 {errors}")
    return added, updated, errors


def sync_via_db(plugins: dict):
    """
    直接操作生产数据库（SQLite）
    适合通过 SSH tunnel 或文件挂载访问数据库的场景
    """
    import sqlite3

    # 尝试连接到生产数据库（如果是本地文件）
    db_paths = [
        "/data/clawhub/data/clawhub.db",
        os.path.expanduser("~/.clawhub/clawhub.db"),
    ]

    db_path = None
    for p in db_paths:
        if Path(p).exists():
            db_path = p
            break

    if not db_path:
        print("❌ 未找到 ClawHub 数据库文件")
        print("   请通过以下方式之一同步:")
        print("   1. SSH 到服务器，直接运行本脚本")
        print("   2. 提供数据库文件路径")
        return False

    print(f"   使用数据库: {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 确保表存在
    cur.execute("""
        CREATE TABLE IF NOT EXISTS plugin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plugin_id VARCHAR(100) UNIQUE NOT NULL,
            plugin_name VARCHAR(100) NOT NULL,
            description TEXT,
            author VARCHAR(100),
            author_id INTEGER,
            version VARCHAR(20) DEFAULT '1.0.0',
            plugin_type VARCHAR(20) NOT NULL,
            category VARCHAR(50),
            compatible_wanclaw_version VARCHAR(20) DEFAULT '>=1.0.0',
            entry_file VARCHAR(100),
            permissions JSON,
            downloads INTEGER DEFAULT 0,
            rating REAL DEFAULT 5.0,
            rating_count INTEGER DEFAULT 0,
            review_status VARCHAR(20) DEFAULT 'pending',
            review_message TEXT,
            file_path VARCHAR(200),
            file_signature VARCHAR(200),
            file_hash VARCHAR(64),
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 确保用户表存在
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE,
            password_hash VARCHAR(200),
            role VARCHAR(20) DEFAULT 'user',
            avatar VARCHAR(200),
            bio TEXT,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)

    conn.commit()

    # 确保官方用户存在
    cur.execute("SELECT id FROM user WHERE username='WanClaw'")
    row = cur.fetchone()
    if row:
        author_id = row[0]
    else:
        cur.execute("""
            INSERT INTO user (username, email, password_hash, role)
            VALUES ('WanClaw', 'official@clawhub.com', 'official_dummy_hash', 'admin')
        """)
        author_id = cur.lastrowid
        conn.commit()
        print("   ✅ 创建官方用户 WanClaw")

    category_map = {
        "ecommerce": "电商自动化",
        "im": "IM智能客服",
        "office": "办公RPA",
        "ai": "AI增强",
        "data": "数据统计",
        "ops": "系统运维",
        "workflow": "工作流",
        "ecosystem": "插件生态",
    }

    added = 0
    updated = 0
    skipped = 0

    for plugin_id, pj in plugins.items():
        db_category = category_map.get(pj.get("category", ""), pj.get("category", ""))

        cur.execute("SELECT id FROM plugin WHERE plugin_id=?", (plugin_id,))
        exists = cur.fetchone()

        if exists:
            cur.execute("""
                UPDATE plugin SET
                    plugin_name=?, description=?, author=?, version=?,
                    plugin_type=?, category=?, compatible_wanclaw_version=?,
                    permissions=?, review_status='approved', update_time=CURRENT_TIMESTAMP
                WHERE plugin_id=?
            """, (
                pj.get("plugin_name", ""),
                pj.get("description", ""),
                pj.get("author", "WanClaw"),
                pj.get("version", "2.0.0"),
                pj.get("plugin_type", "skill"),
                db_category,
                pj.get("compatible_wanclaw_version", ">=2.0.0"),
                json.dumps(pj.get("permissions", [])),
                plugin_id,
            ))
            updated += 1
        else:
            plugin_dir = WANCLAW_PLUGINS_DIR / plugin_id.replace("wanclaw.", "")
            cur.execute("""
                INSERT INTO plugin (
                    plugin_id, plugin_name, description, author, author_id,
                    version, plugin_type, category, compatible_wanclaw_version,
                    entry_file, permissions, review_status, review_message,
                    file_path, downloads, rating, rating_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                plugin_id,
                pj.get("plugin_name", ""),
                pj.get("description", ""),
                pj.get("author", "WanClaw"),
                author_id,
                pj.get("version", "2.0.0"),
                pj.get("plugin_type", "skill"),
                db_category,
                pj.get("compatible_wanclaw_version", ">=2.0.0"),
                "main.py",
                json.dumps(pj.get("permissions", [])),
                "approved",
                "官方插件，自动审核通过",
                str(plugin_dir),
                0,
                5.0,
                0,
            ))
            added += 1

    conn.commit()

    # 验证结果
    cur.execute("SELECT COUNT(*) FROM plugin WHERE review_status='approved'")
    total = cur.fetchone()[0]

    conn.close()

    print(f"\n{'='*60}")
    print(f"✅ 同步完成!")
    print(f"   新增: {added} 个插件")
    print(f"   更新: {updated} 个插件")
    print(f"   数据库总计: {total} 个已审核插件")
    print(f"{'='*60}")

    return True


def main():
    print("=" * 60)
    print("WanClaw → ClawHub (生产环境) 插件同步")
    print("=" * 60)

    # 1. 加载汇总
    print(f"\n📦 加载插件汇总: {SUMMARY_FILE}")
    summary = load_summary()
    plugins = summary.get("plugins", {})
    print(f"   本地插件总数: {len(plugins)} 个")

    # 2. 按分类显示
    print(f"\n📂 分类明细:")
    for cat, count in summary.get("by_category", {}).items():
        print(f"   {cat}: {count} 个")

    # 3. 尝试同步
    print(f"\n🔄 开始同步到生产环境...")
    success = sync_via_db(plugins)

    if not success:
        print("\n⚠️  自动同步失败，请手动执行:")
        print("   方法1 - SSH 到服务器:")
        print(f"      scp sync_to_production.py root@wanhub.vanyue.cn:/tmp/")
        print(f"      ssh root@wanhub.vanyue.cn 'cd /data/clawhub && python3 /tmp/sync_to_production.py'")
        print()
        print("   方法2 - 直接调用 API (需要 admin token):")
        print(f"      curl -X POST https://wanhub.vanyue.cn/api/admin/plugins/sync-official")
        print()
        print("   方法3 - 导出 SQL 手动导入:")
        print(f"      # 需要先导出插件数据为 SQL")


if __name__ == "__main__":
    main()
