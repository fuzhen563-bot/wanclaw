import os, json, hashlib, time, uuid, shutil, zipfile, tempfile, secrets
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

MARKETPLACE_DIR = Path.home() / ".wanclaw" / "marketplace"
PLUGINS_DIR = MARKETPLACE_DIR / "plugins"
USERS_DIR = MARKETPLACE_DIR / "users"
UPLOADS_DIR = MARKETPLACE_DIR / "uploads"
INDEX_FILE = MARKETPLACE_DIR / "index.json"
USERS_FILE = MARKETPLACE_DIR / "users.json"


@dataclass
class MarketplaceUser:
    id: str
    username: str
    email: str
    password_hash: str
    token: str
    created_at: float
    is_admin: bool = False


@dataclass
class MarketplacePlugin:
    name: str
    version: str
    description: str
    author: str
    author_id: str
    category: str
    keywords: List[str]
    permissions: List[str]
    download_url: str
    sha256: str
    file_size: int
    created_at: float
    updated_at: float
    downloads: int = 0
    status: str = "pending"  # pending, approved, rejected
    review_comment: str = ""


class MarketplaceManager:
    def __init__(self):
        self.marketplace_dir = MARKETPLACE_DIR
        self.plugins_dir = PLUGINS_DIR
        self.users_dir = USERS_DIR
        self.uploads_dir = UPLOADS_DIR
        self.index_file = INDEX_FILE
        self.users_file = USERS_FILE
        self._init_dirs()
        self._load_users()
        self._load_plugins()

    def _init_dirs(self):
        for d in [self.marketplace_dir, self.plugins_dir, self.users_dir, self.uploads_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _load_users(self):
        self.users: Dict[str, Dict] = {}
        if self.users_file.exists():
            try:
                with open(self.users_file) as f:
                    self.users = json.load(f)
            except:
                self.users = {}

    def _save_users(self):
        with open(self.users_file, "w") as f:
            json.dump(self.users, f, indent=2, ensure_ascii=False)

    def _load_plugins(self):
        self.plugins: Dict[str, Dict] = {}
        if self.index_file.exists():
            try:
                with open(self.index_file) as f:
                    self.plugins = json.load(f)
            except:
                self.plugins = {}

    def _save_plugins(self):
        with open(self.index_file, "w") as f:
            json.dump(self.plugins, f, indent=2, ensure_ascii=False)

    def _hash_password(self, pwd: str) -> str:
        return hashlib.sha256(pwd.encode()).hexdigest()

    def _gen_token(self) -> str:
        return secrets.token_hex(32)

    def register(self, username: str, email: str, password: str) -> Dict:
        if not username or not email or not password:
            return {"success": False, "error": "用户名、邮箱和密码必填"}
        if len(password) < 6:
            return {"success": False, "error": "密码至少6位"}
        if username in self.users:
            return {"success": False, "error": "用户名已存在"}
        for u in self.users.values():
            if u.get("email") == email:
                return {"success": False, "error": "邮箱已被注册"}
        token = self._gen_token()
        user = {
            "id": str(uuid.uuid4())[:8],
            "username": username,
            "email": email,
            "password_hash": self._hash_password(password),
            "token": token,
            "created_at": time.time(),
            "is_admin": len(self.users) == 0,
        }
        self.users[username] = user
        self._save_users()
        logger.info(f"Marketplace user registered: {username}")
        return {"success": True, "username": username, "token": token}

    def login(self, username: str, password: str) -> Dict:
        user = self.users.get(username)
        if not user:
            return {"success": False, "error": "用户不存在"}
        if user["password_hash"] != self._hash_password(password):
            return {"success": False, "error": "密码错误"}
        token = self._gen_token()
        user["token"] = token
        self._save_users()
        return {"success": True, "username": username, "token": token, "is_admin": user.get("is_admin", False)}

    def auth(self, token: str) -> Optional[Dict]:
        if not token:
            return None
        for u in self.users.values():
            if u.get("token") == token:
                return u
        return None

    def upload_plugin(self, token: str, zip_data: bytes) -> Dict:
        user = self.auth(token)
        if not user:
            return {"success": False, "error": "请先登录"}
        tmp_dir = tempfile.mkdtemp(prefix="marketplace_")
        try:
            zip_path = os.path.join(tmp_dir, "plugin.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_data)
            extract_dir = os.path.join(tmp_dir, "extracted")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
            manifest_path = os.path.join(extract_dir, "plugin.json")
            if not os.path.exists(manifest_path):
                manifest_path = os.path.join(extract_dir, "manifest.json")
            if not os.path.exists(manifest_path):
                return {"success": False, "error": "缺少 plugin.json 或 manifest.json"}
            with open(manifest_path) as f:
                manifest = json.load(f)
            name = manifest.get("name", "")
            if not name:
                return {"success": False, "error": "插件名称必填"}
            if not manifest.get("version"):
                return {"success": False, "error": "插件版本必填"}
            if not manifest.get("description"):
                return {"success": False, "error": "插件描述必填"}
            main_py = os.path.join(extract_dir, "main.py")
            if not os.path.exists(main_py):
                return {"success": False, "error": "缺少 main.py 入口文件"}
            plugin_dir = self.plugins_dir / name
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
            shutil.copytree(extract_dir, str(plugin_dir))
            sha = hashlib.sha256(zip_data).hexdigest()
            now = time.time()
            existing = self.plugins.get(name, {})
            plugin = {
                "name": name,
                "version": manifest.get("version", "1.0.0"),
                "description": manifest.get("description", ""),
                "author": user["username"],
                "author_id": user["id"],
                "category": manifest.get("category", "custom"),
                "keywords": manifest.get("keywords", []),
                "permissions": manifest.get("permissions", []),
                "download_url": f"/api/marketplace/download/{name}",
                "sha256": sha,
                "file_size": len(zip_data),
                "created_at": existing.get("created_at", now),
                "updated_at": now,
                "downloads": existing.get("downloads", 0),
                "status": "approved",
                "review_comment": "",
            }
            self.plugins[name] = plugin
            self._save_plugins()
            logger.info(f"Plugin uploaded: {name} by {user['username']}")
            return {"success": True, "plugin": plugin}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def download_plugin(self, name: str) -> Optional[bytes]:
        plugin_dir = self.plugins_dir / name
        if not plugin_dir.exists():
            return None
        tmp_dir = tempfile.mkdtemp(prefix="dl_")
        try:
            zip_path = os.path.join(tmp_dir, f"{name}.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(plugin_dir):
                    for f in files:
                        full = os.path.join(root, f)
                        arc = os.path.relpath(full, plugin_dir)
                        zf.write(full, arc)
            with open(zip_path, "rb") as f:
                data = f.read()
            if name in self.plugins:
                self.plugins[name]["downloads"] = self.plugins[name].get("downloads", 0) + 1
                self._save_plugins()
            return data
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def list_plugins(self, category: str = None, keyword: str = None, author: str = None, limit: int = 50) -> List[Dict]:
        results = []
        for p in self.plugins.values():
            if p.get("status") != "approved":
                continue
            if category and p.get("category") != category:
                continue
            if author and p.get("author") != author:
                continue
            if keyword:
                q = keyword.lower()
                searchable = f"{p['name']} {p.get('description', '')} {' '.join(p.get('keywords', []))} {p.get('author', '')}".lower()
                if q not in searchable:
                    continue
            results.append(p)
        results.sort(key=lambda x: x.get("downloads", 0), reverse=True)
        return results[:limit]

    def get_plugin(self, name: str) -> Optional[Dict]:
        return self.plugins.get(name)

    def delete_plugin(self, name: str, token: str) -> Dict:
        user = self.auth(token)
        if not user:
            return {"success": False, "error": "请先登录"}
        plugin = self.plugins.get(name)
        if not plugin:
            return {"success": False, "error": "插件不存在"}
        if plugin["author_id"] != user["id"] and not user.get("is_admin"):
            return {"success": False, "error": "无权删除"}
        plugin_dir = self.plugins_dir / name
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)
        del self.plugins[name]
        self._save_plugins()
        return {"success": True}

    def get_stats(self) -> Dict:
        categories = {}
        authors = set()
        total_downloads = 0
        for p in self.plugins.values():
            if p.get("status") == "approved":
                cat = p.get("category", "custom")
                categories[cat] = categories.get(cat, 0) + 1
                authors.add(p.get("author", ""))
                total_downloads += p.get("downloads", 0)
        return {
            "total_plugins": len([p for p in self.plugins.values() if p.get("status") == "approved"]),
            "total_authors": len(authors),
            "total_downloads": total_downloads,
            "categories": categories,
            "total_users": len(self.users),
        }

    def get_user_plugins(self, token: str) -> List[Dict]:
        user = self.auth(token)
        if not user:
            return []
        return [p for p in self.plugins.values() if p.get("author_id") == user["id"]]


_marketplace: Optional[MarketplaceManager] = None

def get_marketplace() -> MarketplaceManager:
    global _marketplace
    if _marketplace is None:
        _marketplace = MarketplaceManager()
    return _marketplace
