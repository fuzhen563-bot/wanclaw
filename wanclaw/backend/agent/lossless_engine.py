import asyncio
import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from wanclaw.backend.agent.tokenizer import count_tokens

logger = logging.getLogger(__name__)


class LosslessContextEngine:
    def __init__(self, db_path: str = None, llm_client=None, max_tokens: int = 200000):
        if db_path is None:
            db_path = os.path.expanduser("~/.wanclaw/lossless_context.db")
        self.db_path = db_path
        self.llm = llm_client
        self.max_tokens = max_tokens
        self._compaction_threshold = 0.6
        self._summary_model = "deepseek-chat"
        self._summary_provider = "deepseek"
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._bg_task: Optional[asyncio.Task] = None

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS msg_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_key TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tokens INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                node_type TEXT DEFAULT 'message',
                summary TEXT,
                parent_id INTEGER,
                episode_id TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY,
                session_key TEXT NOT NULL,
                topic TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                summary TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_session ON msg_nodes(session_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_episode ON msg_nodes(episode_id)")
        conn.commit()
        conn.close()

    def _est_tokens(self, text: str) -> int:
        from wanclaw.backend.agent.tokenizer import count_tokens as _ct
        return _ct(text)

    async def bootstrap(self, session_key: str, agent_config: Dict) -> Dict:
        conn = sqlite3.connect(self.db_path)
        recent = conn.execute(
            "SELECT content, summary, node_type FROM msg_nodes WHERE session_key=? ORDER BY id DESC LIMIT 20",
            (session_key,)
        ).fetchall()
        conn.close()
        items = []
        for row in recent:
            if row[2] == "episode":
                items.append({"type": "episode_summary", "content": row[1] or row[0]})
            else:
                items.append({"type": "message", "content": row[0]})
        return {"session_key": session_key, "bootstrap_items": items}

    async def ingest(self, session_key: str, message: Dict) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            content = message.get("content", "")
            role = message.get("role", "user")
            tokens = count_tokens(content)
            episode_id = message.get("episode_id", f"ep_{int(time.time())}")
            parent_id = message.get("parent_id")
            node_type = message.get("node_type", "message")
            conn.execute(
                "INSERT INTO msg_nodes (session_key, role, content, tokens, created_at, node_type, parent_id, episode_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (session_key, role, content, tokens, time.time(), node_type, parent_id, episode_id)
            )
            conn.commit()
            conn.close()
            asyncio.create_task(self._maybe_compact_session(session_key))
            return True
        except Exception as e:
            logger.error(f"Lossless ingest error: {e}")
            return False

    async def _maybe_compact_session(self, session_key: str):
        try:
            conn = sqlite3.connect(self.db_path)
            total = conn.execute(
                "SELECT SUM(tokens) FROM msg_nodes WHERE session_key=?", (session_key,)
            ).fetchone()[0] or 0
            conn.close()
            if total > self.max_tokens * self._compaction_threshold:
                await self._summarize_oldest_episode(session_key)
        except Exception as e:
            logger.error(f"Lossless compact check error: {e}")

    async def _summarize_oldest_episode(self, session_key: str):
        if not self.llm:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            episode_id = conn.execute(
                "SELECT id FROM episodes WHERE session_key=? ORDER BY created_at ASC LIMIT 1",
                (session_key,)
            ).fetchone()
            if not episode_id:
                rows = conn.execute(
                    "SELECT content, role FROM msg_nodes WHERE session_key=? AND node_type='message' ORDER BY id ASC LIMIT 50",
                    (session_key,)
                ).fetchall()
                if rows:
                    summary_text = "\n".join(f"[{r[1]}]: {r[0][:200]}" for r in rows)
                    messages = [{"role": "user", "content": f"请用一句话总结以下对话的核心内容，不超过100字：\n{summary_text}"}]
                    result = await self.llm.chat(messages)
                    summary = result.get("text", "")[:200]
                    episode_id_val = f"ep_s_{int(time.time())}"
                    conn.execute(
                        "INSERT INTO episodes (id, session_key, topic, created_at, updated_at, summary) VALUES (?, ?, ?, ?, ?, ?)",
                        (episode_id_val, session_key, "auto", time.time(), time.time(), summary)
                    )
                    conn.execute(
                        "UPDATE msg_nodes SET episode_id=?, summary=? WHERE session_key=? AND episode_id IS NULL",
                        (episode_id_val, summary, session_key)
                    )
            else:
                ep_id = episode_id[0]
                rows = conn.execute(
                    "SELECT content FROM msg_nodes WHERE episode_id=? ORDER BY id ASC LIMIT 30",
                    (ep_id,)
                ).fetchall()
                if rows:
                    text = "\n".join(r[0][:200] for r in rows)
                    messages = [{"role": "user", "content": f"用一句话总结：\n{text[:1000]}"}]
                    result = await self.llm.chat(messages)
                    summary = result.get("text", "")[:200]
                    conn.execute(
                        "UPDATE episodes SET summary=?, updated_at=? WHERE id=?",
                        (summary, time.time(), ep_id)
                    )
            conn.commit()
            conn.close()
            logger.info(f"Lossless summary complete for {session_key}")
        except Exception as e:
            logger.error(f"Lossless summary error: {e}")

    async def assemble(self, session_key: str, system_prompt: str, recent_messages: List[Dict]) -> List[Dict]:
        return recent_messages

    async def compact(self, messages: List[Dict], budget) -> List[Dict]:
        return messages

    async def afterTurn(self, messages: List[Dict], turn_result: Dict) -> List[Dict]:
        for msg in messages:
            await self.ingest(session_key, msg)
        return messages

    async def prepareSubagentSpawn(self, parent_session: str, subagent_config: Dict) -> Dict:
        conn = sqlite3.connect(self.db_path)
        shared_episodes = conn.execute(
            "SELECT id, summary FROM episodes WHERE session_key=? ORDER BY updated_at DESC LIMIT 5",
            (parent_session,)
        ).fetchall()
        conn.close()
        shared = [{"id": r[0], "summary": r[1]} for r in shared_episodes if r[1]]
        return {"approved": True, "subagent_session": f"{parent_session}:sub", "shared_episodes": shared}

    async def onSubagentEnded(self, parent_session: str, subagent_result: Dict):
        pass

    def get_stats(self) -> Dict:
        try:
            conn = sqlite3.connect(self.db_path)
            total_msgs = conn.execute("SELECT COUNT(*) FROM msg_nodes").fetchone()[0]
            total_episodes = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            summarized = conn.execute("SELECT COUNT(*) FROM episodes WHERE summary IS NOT NULL").fetchone()[0]
            conn.close()
            return {
                "engine": "LosslessContextEngine",
                "total_messages": total_msgs,
                "total_episodes": total_episodes,
                "summarized_episodes": summarized,
            }
        except Exception as e:
            return {"engine": "LosslessContextEngine", "error": str(e)}


class QMDMemoryBackend:
    def __init__(self, workspace_path: str = None):
        if workspace_path is None:
            workspace_path = os.path.expanduser("~/.wanclaw/workspace-qmd")
        self.workspace = Path(workspace_path)
        self.workspace.mkdir(parents=True, exist_ok=True)

    def search(self, query: str, paths: List[str] = None, top_k: int = 10) -> List[Dict]:
        results = []
        query_lower = query.lower()
        search_dirs = paths or [str(self.workspace)]
        for search_dir in search_dirs:
            p = Path(search_dir)
            if not p.exists():
                continue
            for md_file in p.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if query_lower in line.lower():
                            results.append({
                                "file": str(md_file.relative_to(p.parent)),
                                "line": i + 1,
                                "content": line.strip(),
                                "score": 1.0,
                            })
                    if len(results) >= top_k * 2:
                        break
                except Exception:
                    continue
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def index_file(self, file_path: str, content: str) -> bool:
        try:
            p = Path(file_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"QMD index error: {e}")
            return False
