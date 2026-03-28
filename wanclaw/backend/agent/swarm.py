import asyncio
import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class SwarmMemory:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.expanduser("~/.wanclaw/swarm_memory.db")
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS swarm_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                agent_id TEXT,
                timestamp REAL NOT NULL,
                ttl_seconds INTEGER,
                FOREIGN KEY(key) REFERENCES swarm_keys(key)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS swarm_keys (
                key TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                agent_id TEXT,
                permissions TEXT
            )
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS swarm_fts USING fts5(
                key, value, content='swarm_memory', content_rowid='rowid'
            )
        """)
        conn.commit()
        conn.close()

    def write(self, key: str, value: Any, agent_id: str = "global", ttl_seconds: int = None) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            val_str = json.dumps(value, ensure_ascii=False)
            now = time.time()
            conn.execute(
                "INSERT OR REPLACE INTO swarm_memory (key, value, agent_id, timestamp, ttl_seconds) VALUES (?, ?, ?, ?, ?)",
                (key, val_str, agent_id, now, ttl_seconds)
            )
            conn.execute(
                "INSERT OR IGNORE INTO swarm_keys (key, created_at, agent_id) VALUES (?, ?, ?)",
                (key, now, agent_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"SwarmMemory write error: {e}")
            return False

    def read(self, key: str, agent_id: str = None) -> Optional[Any]:
        try:
            conn = sqlite3.connect(self.db_path)
            now = time.time()
            if agent_id:
                rows = conn.execute(
                    "SELECT value FROM swarm_memory WHERE key=? AND (agent_id=? OR agent_id='global') AND (ttl_seconds IS NULL OR timestamp+ttl_seconds>?) ORDER BY timestamp DESC LIMIT 1",
                    (key, agent_id, now)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT value FROM swarm_memory WHERE key=? AND (ttl_seconds IS NULL OR timestamp+ttl_seconds>?) ORDER BY timestamp DESC LIMIT 1",
                    (key, now)
                ).fetchall()
            conn.close()
            if rows:
                return json.loads(rows[0][0])
        except Exception as e:
            logger.error(f"SwarmMemory read error: {e}")
        return None

    def search(self, query: str, agent_id: str = None, top_k: int = 10) -> List[Dict]:
        try:
            conn = sqlite3.connect(self.db_path)
            now = time.time()
            base_sql = """
                SELECT m.key, m.value, m.agent_id, m.timestamp
                FROM swarm_memory m
                WHERE m.ttl_seconds IS NULL OR m.timestamp + m.ttl_seconds > ?
            """
            params = [now]
            if agent_id:
                base_sql += " AND (m.agent_id=? OR m.agent_id='global')"
                params.append(agent_id)
            base_sql += " ORDER BY m.timestamp DESC LIMIT 50"
            rows = conn.execute(base_sql, params).fetchall()
            conn.close()
            results = []
            query_lower = query.lower()
            for row in rows:
                key, val_str, ag_id, ts = row
                val_lower = val_str.lower()
                if query_lower in key.lower() or query_lower in val_lower:
                    results.append({
                        "key": key,
                        "value": json.loads(val_str),
                        "agent_id": ag_id,
                        "timestamp": ts,
                    })
            return results[:top_k]
        except Exception as e:
            logger.error(f"SwarmMemory search error: {e}")
            return []

    def list_keys(self, agent_id: str = None) -> List[str]:
        try:
            conn = sqlite3.connect(self.db_path)
            if agent_id:
                rows = conn.execute(
                    "SELECT DISTINCT key FROM swarm_keys WHERE agent_id=? OR agent_id='global'",
                    (agent_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT DISTINCT key FROM swarm_keys").fetchall()
            conn.close()
            return [r[0] for r in rows]
        except Exception as e:
            logger.error(f"SwarmMemory list_keys error: {e}")
            return []

    def delete(self, key: str, agent_id: str = None) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            if agent_id:
                conn.execute("DELETE FROM swarm_memory WHERE key=? AND agent_id=?", (key, agent_id))
            else:
                conn.execute("DELETE FROM swarm_memory WHERE key=?", (key,))
            conn.execute("DELETE FROM swarm_keys WHERE key=?", (key,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"SwarmMemory delete error: {e}")
            return False

    def get_stats(self) -> Dict:
        try:
            conn = sqlite3.connect(self.db_path)
            total = conn.execute("SELECT COUNT(*) FROM swarm_memory").fetchone()[0]
            keys = conn.execute("SELECT COUNT(*) FROM swarm_keys").fetchone()[0]
            agents = conn.execute("SELECT COUNT(DISTINCT agent_id) FROM swarm_keys").fetchone()[0]
            conn.close()
            return {
                "db_path": self.db_path,
                "total_entries": total,
                "unique_keys": keys,
                "participating_agents": agents,
            }
        except Exception as e:
            return {"error": str(e)}


class DAGStore:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.expanduser("~/.wanclaw/dag_store.db")
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dag_nodes (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dag_edges (
                parent_id TEXT NOT NULL,
                child_id TEXT NOT NULL,
                rel TEXT DEFAULT 'depends_on',
                PRIMARY KEY (parent_id, child_id),
                FOREIGN KEY(parent_id) REFERENCES dag_nodes(id),
                FOREIGN KEY(child_id) REFERENCES dag_nodes(id)
            )
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS dag_fts USING fts5(
                id, data, content='dag_nodes', content_rowid='rowid'
            )
        """)
        conn.commit()
        conn.close()

    def put(self, node_id: str, data: Any, parents: List[str] = None) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            now = time.time()
            data_str = json.dumps(data, ensure_ascii=False)
            existing = conn.execute(
                "SELECT created_at FROM dag_nodes WHERE id=?", (node_id,)
            ).fetchone()
            created_at = existing[0] if existing else now
            conn.execute(
                "INSERT OR REPLACE INTO dag_nodes (id, data, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (node_id, data_str, created_at, now)
            )
            conn.execute("DELETE FROM dag_edges WHERE child_id=?", (node_id,))
            if parents:
                for p in parents:
                    conn.execute(
                        "INSERT OR IGNORE INTO dag_edges (parent_id, child_id) VALUES (?, ?)",
                        (p, node_id)
                    )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"DAGStore put error: {e}")
            return False

    def get(self, node_id: str) -> Optional[Any]:
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute("SELECT data FROM dag_nodes WHERE id=?", (node_id,)).fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
        except Exception as e:
            logger.error(f"DAGStore get error: {e}")
        return None

    def get_parents(self, node_id: str) -> List[str]:
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute(
                "SELECT parent_id FROM dag_edges WHERE child_id=?", (node_id,)
            ).fetchall()
            conn.close()
            return [r[0] for r in rows]
        except Exception:
            return []

    def get_children(self, node_id: str) -> List[str]:
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute(
                "SELECT child_id FROM dag_edges WHERE parent_id=?", (node_id,)
            ).fetchall()
            conn.close()
            return [r[0] for r in rows]
        except Exception:
            return []

    def topological_order(self) -> List[str]:
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute("""
                SELECT id FROM dag_nodes
                WHERE id NOT IN (SELECT child_id FROM dag_edges)
                ORDER BY created_at
            """).fetchall()
            ordered = [r[0] for r in rows]
            conn.close()
            return ordered
        except Exception as e:
            logger.error(f"DAGStore topological_order error: {e}")
            return []

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute(
                "SELECT id, data FROM dag_nodes WHERE id LIKE ? OR data LIKE ? LIMIT ?",
                (f"%{query}%", f"%{query}%", top_k)
            ).fetchall()
            conn.close()
            return [{"id": r[0], "data": json.loads(r[1])} for r in rows]
        except Exception as e:
            logger.error(f"DAGStore search error: {e}")
            return []


_swarm: Optional[SwarmMemory] = None
_dag: Optional[DAGStore] = None


def get_swarm_memory() -> SwarmMemory:
    global _swarm
    if _swarm is None:
        _swarm = SwarmMemory()
    return _swarm


def get_dag_store() -> DAGStore:
    global _dag
    if _dag is None:
        _dag = DAGStore()
    return _dag
