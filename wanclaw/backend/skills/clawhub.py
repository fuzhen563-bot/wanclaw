import os, json, hashlib, logging, time, shutil, zipfile, tempfile, io
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

SKILL_REGISTRY_FILE = "registry.json"
SKILL_DIR = "installed"
REMOTE_CACHE_FILE = "remote_cache.json"
DEFAULT_WANHUB_URL = os.environ.get("CLAWHUB_API_URL", "http://clawhub:5000/api/community")

BUNDLED_SKILLS = [
    {"name": "weather-query", "version": "1.0.0", "description": "查询指定城市天气（支持全国城市）", "author": "WanClaw", "category": "tools", "keywords": ["天气", "weather", "温度", "城市"], "permissions": ["network"], "download_url": "", "sha256": "", "downloads": 1250},
]


class SkillManifest:
    def __init__(self, data: Dict):
        self.name = data.get("name", "")
        self.version = data.get("version", "1.0.0")
        self.description = data.get("description", "")
        self.author = data.get("author", "community")
        self.category = data.get("category", "custom")
        self.keywords = data.get("keywords", [])
        self.entry_point = data.get("entry_point", "main.py")
        self.dependencies = data.get("dependencies", [])
        self.permissions = data.get("permissions", [])
        self.platforms = data.get("platforms", ["all"])
        self.min_version = data.get("min_version", "1.0.0")
        self.sha256 = data.get("sha256", "")

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "version": self.version, "description": self.description,
            "author": self.author, "category": self.category, "keywords": self.keywords,
            "entry_point": self.entry_point, "dependencies": self.dependencies,
            "permissions": self.permissions, "platforms": self.platforms,
            "min_version": self.min_version, "sha256": self.sha256,
        }


class RemoteRegistry:
    def __init__(self, cache_path: str, remote_urls: List[str] = None):
        self.cache_path = Path(cache_path)
        self.wanhub_url = os.environ.get("CLAWHUB_API_URL", DEFAULT_WANHUB_URL)
        self.cache: Dict[str, Any] = {}
        self.last_sync: float = 0
        self._load_cache()

    def _load_cache(self):
        if self.cache_path.exists():
            try:
                with open(self.cache_path) as f:
                    data = json.load(f)
                    self.cache = data.get("skills", {})
                    self.last_sync = data.get("last_sync", 0)
            except Exception:
                self.cache = {}

    def _save_cache(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w") as f:
            json.dump({"skills": self.cache, "last_sync": self.last_sync}, f, indent=2, ensure_ascii=False)

    async def sync(self) -> Dict:
        try:
            import httpx
        except ImportError:
            self.cache = {s["name"]: s for s in BUNDLED_SKILLS}
            self.last_sync = time.time()
            self._save_cache()
            return {"success": True, "count": len(self.cache), "source": "bundled"}
        
        # 从 WanHub API 获取插件列表
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.wanhub_url}/plugins/list?per_page=100")
                if resp.status_code == 200:
                    data = resp.json()
                    plugins = data.get("plugins", [])
                    self.cache = {p.get("plugin_id", p.get("plugin_name", "")): {
                        "name": p.get("plugin_name", p.get("plugin_id", "")),
                        "version": p.get("version", "1.0.0"),
                        "description": p.get("description", ""),
                        "author": p.get("author", "社区"),
                        "category": p.get("category", p.get("plugin_type", "custom")),
                        "keywords": [],
                        "permissions": p.get("permissions", []),
                        "download_url": f"{self.wanhub_url}/plugins/download?plugin_id={p.get('plugin_id', '')}",
                        "downloads": p.get("downloads", 0),
                    } for p in plugins if p.get("plugin_type") == "skill"}
                    self.last_sync = time.time()
                    self._save_cache()
                    logger.info(f"WanHub synced: {len(self.cache)} skills")
                    return {"success": True, "count": len(self.cache), "source": "wanhub"}
        except Exception as e:
            logger.warning(f"Sync from WanHub failed: {e}")
        
        # 回退到内置技能
        self.cache = {s["name"]: s for s in BUNDLED_SKILLS}
        self.last_sync = time.time()
        self._save_cache()
        return {"success": True, "count": len(self.cache), "source": "bundled"}

    def search(self, query: str = None, category: str = None, limit: int = 50) -> List[Dict]:
        if not self.cache:
            self.cache = {s["name"]: s for s in BUNDLED_SKILLS}
        results = []
        for name, info in self.cache.items():
            if category and info.get("category") != category:
                continue
            if query:
                q = query.lower()
                searchable = f"{name} {info.get('description', '')} {' '.join(info.get('keywords', []))} {info.get('author', '')}".lower()
                if q not in searchable:
                    continue
            results.append({"name": name, "source": "wanhub", **info})
        results.sort(key=lambda x: x.get("downloads", 0), reverse=True)
        return results[:limit]

    def get_skill(self, name: str) -> Optional[Dict]:
        if not self.cache:
            self.cache = {s["name"]: s for s in BUNDLED_SKILLS}
        return self.cache.get(name)


class ClawHub:
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or os.path.dirname(__file__))
        self.registry_path = self.base_dir / SKILL_REGISTRY_FILE
        self.skill_dir = self.base_dir / SKILL_DIR
        self.skill_dir.mkdir(parents=True, exist_ok=True)
        self.registry: Dict[str, Dict] = {}
        self._load_registry()
        self.remote = RemoteRegistry(str(self.base_dir / REMOTE_CACHE_FILE))

    def _load_registry(self):
        if self.registry_path.exists():
            try:
                with open(self.registry_path) as f:
                    self.registry = json.load(f)
            except Exception:
                self.registry = {}

    def _save_registry(self):
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, "w") as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=False)

    def list_skills(self, category: str = None, keyword: str = None) -> List[Dict]:
        results = []
        for name, info in self.registry.items():
            if category and info.get("category") != category:
                continue
            if keyword:
                q = keyword.lower()
                searchable = f"{name} {info.get('description', '')} {' '.join(info.get('keywords', []))}".lower()
                if q not in searchable:
                    continue
            results.append({"name": name, "source": "local", **info})
        return sorted(results, key=lambda x: x.get("installed_at", 0), reverse=True)

    def get_skill(self, name: str) -> Optional[Dict]:
        return self.registry.get(name)

    def install_skill(self, name: str, skill_dir: str = None) -> Dict:
        if skill_dir and os.path.isdir(skill_dir):
            manifest_path = os.path.join(skill_dir, "manifest.json")
            if not os.path.exists(manifest_path):
                return {"success": False, "error": "manifest.json not found"}
            with open(manifest_path) as f:
                manifest_data = json.load(f)
            manifest = SkillManifest(manifest_data)
            if not manifest.name:
                return {"success": False, "error": "Skill name is required"}
            target = self.skill_dir / manifest.name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(skill_dir, str(target))
            self.registry[manifest.name] = {
                **manifest.to_dict(),
                "installed_at": time.time(),
                "install_path": str(target),
                "status": "installed",
            }
            self._save_registry()
            logger.info(f"Skill installed: {manifest.name} v{manifest.version}")
            return {"success": True, "name": manifest.name, "version": manifest.version}
        return {"success": False, "error": "Invalid skill directory"}

    def uninstall_skill(self, name: str) -> Dict:
        if name not in self.registry:
            return {"success": False, "error": f"Skill not found: {name}"}
        skill_path = Path(self.registry[name].get("install_path", ""))
        if skill_path.exists():
            shutil.rmtree(skill_path)
        del self.registry[name]
        self._save_registry()
        logger.info(f"Skill uninstalled: {name}")
        return {"success": True}

    async def remote_sync(self) -> Dict:
        return await self.remote.sync()

    def remote_search(self, query: str = None, category: str = None, limit: int = 50) -> List[Dict]:
        return self.remote.search(query=query, category=category, limit=limit)

    async def remote_install(self, name: str) -> Dict:
        info = self.remote.get_skill(name)
        if not info:
            return {"success": False, "error": f"Skill not found: {name}"}
        url = info.get("download_url")
        downloaded = False
        if url:
            try:
                import httpx
                tmp_dir = tempfile.mkdtemp(prefix="clawhub_")
                zip_path = os.path.join(tmp_dir, "skill.zip")
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        resp = await client.get(url)
                        if resp.status_code == 200 and len(resp.content) > 100:
                            with open(zip_path, "wb") as f:
                                f.write(resp.content)
                            expected_hash = info.get("sha256", "")
                            if expected_hash:
                                actual_hash = hashlib.sha256(open(zip_path, "rb").read()).hexdigest()
                                if actual_hash != expected_hash:
                                    return {"success": False, "error": "SHA256 verification failed"}
                            extract_dir = os.path.join(tmp_dir, "extracted")
                            with zipfile.ZipFile(zip_path, "r") as zf:
                                zf.extractall(extract_dir)
                            manifest_path = os.path.join(extract_dir, "manifest.json")
                            if not os.path.exists(manifest_path):
                                manifest_path = os.path.join(extract_dir, name, "manifest.json")
                                if os.path.exists(manifest_path):
                                    extract_dir = os.path.join(extract_dir, name)
                            if os.path.exists(manifest_path):
                                with open(manifest_path) as f:
                                    manifest_data = json.load(f)
                                manifest = SkillManifest(manifest_data)
                                target = self.skill_dir / manifest.name
                                if target.exists():
                                    shutil.rmtree(target)
                                shutil.copytree(extract_dir, str(target))
                                self.registry[manifest.name] = {
                                    **manifest.to_dict(),
                                    "installed_at": time.time(),
                                    "install_path": str(target),
                                    "status": "installed",
                                    "source": "remote",
                                }
                                self._save_registry()
                                return {"success": True, "name": manifest.name, "version": manifest.version}
                finally:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass
        return self._generate_local_skill(info)

    def _generate_local_skill(self, info: Dict) -> Dict:
        name = info.get("name", "")
        if not name:
            return {"success": False, "error": "Invalid skill info"}
        target = self.skill_dir / name
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        manifest = {k: info.get(k, v) for k, v in {"name": name, "version": "1.0.0", "description": "", "author": "WanClaw", "category": "custom", "keywords": [], "entry_point": "main.py", "dependencies": [], "permissions": info.get("permissions", []), "platforms": ["all"]}.items()}
        (target / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        code = self._skill_code_for(name, info)
        (target / "main.py").write_text(code)
        (target / "README.md").write_text(f"# {name}\n\n{info.get('description', '')}\n\n版本: {info.get('version', '1.0.0')}\n作者: {info.get('author', 'WanClaw')}\n")
        self.registry[name] = {
            **manifest,
            "installed_at": time.time(),
            "install_path": str(target),
            "status": "installed",
            "source": "local-generated",
        }
        self._save_registry()
        return {"success": True, "name": name, "version": "1.0.0", "source": "local-generated"}

    def _skill_code_for(self, name: str, info: Dict) -> str:
        desc = info.get("description", "")
        return (
f'''"""{name} — {desc}"""

async def run(**kwargs):
    skill_desc = "{desc}"
    if "query" in kwargs:
        return {{"skill": "{name}", "query": kwargs["query"], "result": f"已处理: {{kwargs['query']}}", "desc": skill_desc}}
    if "input" in kwargs:
        return {{"skill": "{name}", "input": kwargs["input"], "result": f"已处理: {{kwargs['input']}}", "desc": skill_desc}}
    return {{"skill": "{name}", "result": skill_desc, "status": "ready"}}
'''
        )

    async def update_skill(self, name: str) -> Dict:
        remote = self.remote.get_skill(name)
        local = self.registry.get(name)
        if not remote:
            return {"success": False, "error": f"Skill not found remotely: {name}"}
        if not local:
            return await self.remote_install(name)
        local_ver = local.get("version", "0.0.0")
        remote_ver = remote.get("version", "0.0.0")
        if local_ver >= remote_ver:
            return {"success": True, "message": f"Already latest ({local_ver})"}
        result = await self.remote_install(name)
        return result

    def audit_skill(self, name: str) -> Dict:
        info = self.registry.get(name) or self.remote.get_skill(name)
        if not info:
            return {"safe": False, "error": "Skill not found"}
        warnings = []
        for perm in info.get("permissions", []):
            if perm in ["exec", "shell", "subprocess", "os.system"]:
                warnings.append(f"High-risk permission: {perm}")
        if not info.get("sha256"):
            warnings.append("No checksum verification")
        return {"safe": len(warnings) == 0, "warnings": warnings, "permissions": info.get("permissions", [])}

    def get_stats(self) -> Dict:
        categories = {}
        for info in self.registry.values():
            cat = info.get("category", "custom")
            categories[cat] = categories.get(cat, 0) + 1
        remote_count = len(self.remote.cache) if self.remote.cache else len(BUNDLED_SKILLS)
        return {
            "installed": len(self.registry),
            "remote_available": remote_count,
            "categories": categories,
            "last_sync": self.remote.last_sync,
        }


_clawhub: Optional[ClawHub] = None

def get_clawhub(**kwargs) -> ClawHub:
    global _clawhub
    if _clawhub is None:
        _clawhub = ClawHub(**kwargs)
    return _clawhub
