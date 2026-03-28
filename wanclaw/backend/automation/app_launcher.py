"""
安全应用启动器 V2.0
纯系统API调用，无subprocess

Windows: ShellExecuteW (Win32 API)
macOS: NSWorkspace (系统框架)
Linux: Gio / g_app_info_launch_default (GLib)

白名单机制：只允许启动预定义的安全软件
"""

import sys
import logging
import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AppInfo:
    name: str
    paths: List[str]
    args: List[str]
    description: str
    category: str


DEFAULT_WHITELIST: Dict[str, AppInfo] = {
    # ===== 浏览器 =====
    "chrome": AppInfo(
        name="Google Chrome",
        paths=[
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/snap/bin/chromium",
        ],
        args=[],
        description="Google Chrome浏览器",
        category="browser"
    ),
    "edge": AppInfo(
        name="Microsoft Edge",
        paths=[
            "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
            "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/usr/bin/microsoft-edge",
        ],
        args=[],
        description="Microsoft Edge浏览器",
        category="browser"
    ),
    "firefox": AppInfo(
        name="Mozilla Firefox",
        paths=[
            "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
            "/Applications/Firefox.app/Contents/MacOS/firefox",
            "/usr/bin/firefox",
            "/snap/bin/firefox",
        ],
        args=[],
        description="Mozilla Firefox浏览器",
        category="browser"
    ),
    "brave": AppInfo(
        name="Brave Browser",
        paths=[
            "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/usr/bin/brave-browser",
        ],
        args=[],
        description="Brave浏览器",
        category="browser"
    ),

    # ===== 办公软件 =====
    "excel": AppInfo(
        name="Microsoft Excel",
        paths=[
            "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
            "C:\\Program Files\\Microsoft Office\\Office16\\EXCEL.EXE",
            "C:\\Program Files (x86)\\Microsoft Office\\Office16\\EXCEL.EXE",
            "/Applications/Microsoft Excel.app/Contents/MacOS/Microsoft Excel",
            "/usr/bin/soffice",
        ],
        args=[],
        description="Microsoft Excel",
        category="office"
    ),
    "word": AppInfo(
        name="Microsoft Word",
        paths=[
            "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
            "C:\\Program Files\\Microsoft Office\\Office16\\WINWORD.EXE",
            "C:\\Program Files (x86)\\Microsoft Office\\Office16\\WINWORD.EXE",
            "/Applications/Microsoft Word.app/Contents/MacOS/Microsoft Word",
            "/usr/bin/soffice",
        ],
        args=[],
        description="Microsoft Word",
        category="office"
    ),
    "outlook": AppInfo(
        name="Microsoft Outlook",
        paths=[
            "C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE",
            "C:\\Program Files\\Microsoft Office\\Office16\\OUTLOOK.EXE",
            "/Applications/Microsoft Outlook.app/Contents/MacOS/Microsoft Outlook",
        ],
        args=[],
        description="Microsoft Outlook",
        category="office"
    ),
    "wps": AppInfo(
        name="WPS Office",
        paths=[
            "C:\\Program Files\\Kingsoft\\WPS Office\\ksolaunch.exe",
            "C:\\Program Files (x86)\\Kingsoft\\WPS Office\\ksolaunch.exe",
            "/Applications/Kingsoft WPS Office.app/Contents/MacOS/kingsoft",
        ],
        args=[],
        description="WPS Office",
        category="office"
    ),

    # ===== 系统工具 =====
    "notepad": AppInfo(
        name="记事本",
        paths=[
            "C:\\Windows\\System32\\notepad.exe",
            "/Applications/TextEdit.app/Contents/MacOS/TextEdit",
            "/usr/bin/gedit",
            "/usr/bin/mousepad",
            "/usr/bin/kwrite",
            "/usr/bin/xed",
        ],
        args=[],
        description="系统记事本",
        category="system"
    ),
    "calculator": AppInfo(
        name="计算器",
        paths=[
            "C:\\Windows\\System32\\calc.exe",
            "/Applications/Calculator.app/Contents/MacOS/Calculator",
            "/usr/bin/gcalctool",
            "/usr/bin/qalculate-gtk",
        ],
        args=[],
        description="系统计算器",
        category="system"
    ),
    "explorer": AppInfo(
        name="文件资源管理器",
        paths=[
            "C:\\Windows\\explorer.exe",
            "/usr/bin/nautilus",
            "/usr/bin/dolphin",
            "/usr/bin/thunar",
            "/usr/bin/nemo",
        ],
        args=[],
        description="文件资源管理器",
        category="system"
    ),
    "terminal": AppInfo(
        name="终端",
        paths=[
            "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
            "/System/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal",
            "/usr/bin/gnome-terminal",
            "/usr/bin/konsole",
            "/usr/bin/xterm",
            "/usr/bin/tilix",
        ],
        args=[],
        description="终端模拟器",
        category="system"
    ),

    # ===== 媒体 =====
    "vlc": AppInfo(
        name="VLC 播放器",
        paths=[
            "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
            "/Applications/VLC.app/Contents/MacOS/VLC",
            "/usr/bin/vlc",
        ],
        args=[],
        description="VLC媒体播放器",
        category="media"
    ),

    # ===== 开发工具 =====
    "vscode": AppInfo(
        name="VS Code",
        paths=[
            "C:\\Users\\{user}\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
            "/Applications/Visual Studio Code.app/Contents/MacOS/Electron",
            "/usr/bin/code",
        ],
        args=[],
        description="Visual Studio Code",
        category="developer"
    ),
    "sublime": AppInfo(
        name="Sublime Text",
        paths=[
            "C:\\Program Files\\Sublime Text\\sublime_text.exe",
            "/Applications/Sublime Text.app/Contents/MacOS/Sublime Text",
            "/usr/bin/subl",
        ],
        args=[],
        description="Sublime Text编辑器",
        category="developer"
    ),
}


class SecureAppLauncher:
    """安全应用启动器"""

    def __init__(self, whitelist: Dict[str, AppInfo] = None, allowed_dirs: List[str] = None):
        self._whitelist = whitelist or dict(DEFAULT_WHITELIST)
        self._allowed_dirs = allowed_dirs or []
        self._platform = sys.platform
        self._running_apps: Dict[str, int] = {}

    def _expand_path(self, path: str) -> str:
        return os.path.expandvars(os.path.expanduser(path))

    def _find_executable(self, app: AppInfo) -> Optional[str]:
        for path_template in app.paths:
            path = self._expand_path(path_template)
            if os.path.isfile(path):
                return path
            basename = os.path.basename(path_template)
            for d in os.environ.get("PATH", "").split(os.pathsep):
                candidate = os.path.join(d, basename)
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
        return None

    def _check_allowed_dir(self, path: str) -> bool:
        if not self._allowed_dirs:
            return True
        abs_path = os.path.abspath(path)
        for allowed in self._allowed_dirs:
            if abs_path.startswith(os.path.abspath(allowed)):
                return True
        return False

    def is_allowed(self, app_id: str) -> bool:
        return app_id.lower() in self._whitelist

    def list_allowed_apps(self, category: str = None) -> List[Dict[str, Any]]:
        results = []
        for app_id, app in self._whitelist.items():
            if category and app.category != category:
                continue
            exe_path = self._find_executable(app)
            results.append({
                "id": app_id,
                "name": app.name,
                "description": app.description,
                "category": app.category,
                "installed": exe_path is not None,
                "path": exe_path,
            })
        return results

    def add_to_whitelist(self, app_id: str, app_info: AppInfo):
        self._whitelist[app_id.lower()] = app_info

    def remove_from_whitelist(self, app_id: str):
        self._whitelist.pop(app_id.lower(), None)

    def _launch_windows(self, exe_path: str, args: List[str]) -> bool:
        import ctypes
        from ctypes import wintypes
        ShellExecuteW = ctypes.windll.Shell32.ShellExecuteW
        ShellExecuteW.argtypes = [
            wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR,
            wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.INT
        ]
        ShellExecuteW.restype = wintypes.HINSTANCE
        cmd = exe_path
        if args:
            cmd = f'"{exe_path}" ' + " ".join(f'"{a}"' for a in args)
        result = ShellExecuteW(None, "open", cmd, None, None, 1)
        return result > 32

    def _launch_macos(self, exe_path: str, args: List[str]) -> bool:
        try:
            import AppKit
            ws = AppKit.NSWorkspace.shared()
            if exe_path.endswith(".app"):
                app_path = exe_path
                config = AppKit.NSWorkspace.OpenConfiguration()
                config.setActivates_(True)
                config.setHides_(False)
                ws.openApplication_atURL_configuration_(
                    AppKit.NSURL.fileURLWithPath_(app_path),
                    config
                )
            else:
                ws.openURL_(AppKit.NSURL.fileURLWithPath_(exe_path))
            return True
        except Exception as e:
            logger.error(f"Failed to launch on macOS: {e}")
            return False

    def _launch_linux(self, exe_path: str, args: List[str]) -> bool:
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gio
            file = Gio.File.new_for_path(exe_path)
            app_info = Gio.AppInfo.create_from_commandline(
                exe_path + (" " + " ".join(args) if args else ""),
                os.path.basename(exe_path),
                Gio.AppInfoCreateFlags.NONE
            )
            launch_context = Gio.AppLaunchContext()
            app_info.launch([file] if os.path.isfile(exe_path) else None, launch_context)
            return True
        except Exception as e:
            logger.error(f"Failed to launch on Linux (Gtk): {e}")
            return False

    def launch(self, app_id: str, args: List[str] = None) -> Dict[str, Any]:
        app_id_lower = app_id.lower()
        if app_id_lower not in self._whitelist:
            return {
                "success": False,
                "error": f"应用不在白名单中: {app_id}",
                "allowed_apps": list(self._whitelist.keys())
            }

        app = self._whitelist[app_id_lower]
        exe_path = self._find_executable(app)

        if not exe_path:
            return {
                "success": False,
                "error": f"应用未安装: {app.name}",
                "searched_paths": app.paths
            }

        if not self._check_allowed_dir(exe_path):
            return {
                "success": False,
                "error": f"路径不在允许目录中: {exe_path}",
                "allowed_dirs": self._allowed_dirs
            }

        args = args or app.args

        try:
            if self._platform == "win32":
                success = self._launch_windows(exe_path, args)
            elif self._platform == "darwin":
                success = self._launch_macos(exe_path, args)
            else:
                success = self._launch_linux(exe_path, args)

            if success:
                self._running_apps[app_id_lower] = self._running_apps.get(app_id_lower, 0) + 1
                logger.info(f"Launched {app.name} from {exe_path}")
                return {
                    "success": True,
                    "app_id": app_id,
                    "app_name": app.name,
                    "path": exe_path,
                    "args": args,
                    "category": app.category,
                    "launch_count": self._running_apps[app_id_lower]
                }
            else:
                return {
                    "success": False,
                    "error": "启动失败"
                }
        except Exception as e:
            logger.error(f"Failed to launch {app.name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def launch_url(self, url: str, browser: str = "chrome") -> Dict[str, Any]:
        if not self.is_allowed(browser):
            return {
                "success": False,
                "error": f"浏览器不在白名单: {browser}"
            }
        return self.launch(browser, [url])


_launcher: Optional[SecureAppLauncher] = None


def get_app_launcher() -> SecureAppLauncher:
    global _launcher
    if _launcher is None:
        _launcher = SecureAppLauncher()
    return _launcher
