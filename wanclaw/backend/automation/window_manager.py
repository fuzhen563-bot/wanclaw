"""
跨平台窗口管理器 V2.0
纯系统API调用，无subprocess

Windows: pywin32 (Win32 API)
macOS: AppKit (NSWindow)
Linux: wnck (GTK window navigator)
"""

import sys
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class WindowState(Enum):
    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    FULLSCREEN = "fullscreen"
    HIDDEN = "hidden"


@dataclass
class WindowInfo:
    hwnd: Any
    title: str
    process_name: str
    bounds: Tuple[int, int, int, int]
    state: WindowState
    is_active: bool
    pid: int


class PlatformWindowManager:
    """平台窗口管理器基类"""

    def __init__(self):
        self._windows: Dict[str, WindowInfo] = {}

    def enumerate_windows(self) -> List[WindowInfo]:
        raise NotImplementedError

    def activate_window(self, window_id: str) -> bool:
        raise NotImplementedError

    def minimize_window(self, window_id: str) -> bool:
        raise NotImplementedError

    def maximize_window(self, window_id: str) -> bool:
        raise NotImplementedError

    def restore_window(self, window_id: str) -> bool:
        raise NotImplementedError

    def close_window(self, window_id: str) -> bool:
        raise NotImplementedError

    def hide_window(self, window_id: str) -> bool:
        raise NotImplementedError

    def set_window_pos(self, window_id: str, x: int, y: int, width: int, height: int) -> bool:
        raise NotImplementedError

    def get_active_window(self) -> Optional[WindowInfo]:
        raise NotImplementedError

    def find_window_by_title(self, title: str) -> Optional[WindowInfo]:
        raise NotImplementedError

    def find_window_by_process(self, process_name: str) -> List[WindowInfo]:
        raise NotImplementedError


class WindowsWindowManager(PlatformWindowManager):
    """Windows 窗口管理器 - pywin32"""

    def __init__(self):
        super().__init__()
        try:
            import win32gui
            import win32con
            import win32process
            import win32api
            self._win32gui = win32gui
            self._win32con = win32con
            self._win32proc = win32process
            self._win32api = win32api
            self._initialized = True
            logger.info("WindowsWindowManager initialized (pywin32)")
        except ImportError:
            logger.warning("pywin32 not installed, Windows window manager unavailable")
            self._initialized = False

    def _get_window_info(self, hwnd: int) -> Optional[WindowInfo]:
        try:
            title = self._win32gui.GetWindowText(hwnd)
            if not title:
                return None
            pid = self._win32proc.GetWindowThreadProcessId(hwnd)[1]
            bounds = self._win32gui.GetWindowRect(hwnd)
            state = self._win32gui.IsWindowVisible(hwnd)
            is_minimized = self._win32gui.IsIconic(hwnd)
            is_maximized = self._win32gui.IsZoomed(hwnd)
            try:
                import psutil
                proc = psutil.Process(pid)
                process_name = proc.name()
            except:
                process_name = "unknown"
            if is_minimized:
                state = WindowState.MINIMIZED
            elif is_maximized:
                state = WindowState.MAXIMIZED
            elif state:
                state = WindowState.NORMAL
            else:
                state = WindowState.HIDDEN
            return WindowInfo(
                hwnd=hwnd,
                title=title,
                process_name=process_name,
                bounds=bounds,
                state=state,
                is_active=self._win32gui.GetForegroundWindow() == hwnd,
                pid=pid
            )
        except Exception:
            return None

    def _window_enum_callback(self, hwnd: int, results: List):
        info = self._get_window_info(hwnd)
        if info:
            results.append(info)

    def enumerate_windows(self) -> List[WindowInfo]:
        if not self._initialized:
            return []
        results: List[WindowInfo] = []
        self._win32gui.EnumWindows(
            lambda h: self._window_enum_callback(h, results), 0
        )
        return results

    def activate_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            hwnd = int(window_id)
            self._win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception as e:
            logger.error(f"Failed to activate window: {e}")
            return False

    def minimize_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            hwnd = int(window_id)
            self._win32gui.ShowWindow(hwnd, self._win32con.SW_MINIMIZE)
            return True
        except Exception as e:
            logger.error(f"Failed to minimize window: {e}")
            return False

    def maximize_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            hwnd = int(window_id)
            self._win32gui.ShowWindow(hwnd, self._win32con.SW_MAXIMIZE)
            return True
        except Exception as e:
            logger.error(f"Failed to maximize window: {e}")
            return False

    def restore_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            hwnd = int(window_id)
            self._win32gui.ShowWindow(hwnd, self._win32con.SW_RESTORE)
            return True
        except Exception as e:
            logger.error(f"Failed to restore window: {e}")
            return False

    def close_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            hwnd = int(window_id)
            self._win32gui.PostMessage(hwnd, self._win32con.WM_CLOSE, 0, 0)
            return True
        except Exception as e:
            logger.error(f"Failed to close window: {e}")
            return False

    def hide_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            hwnd = int(window_id)
            self._win32gui.ShowWindow(hwnd, self._win32con.SW_HIDE)
            return True
        except Exception as e:
            logger.error(f"Failed to hide window: {e}")
            return False

    def set_window_pos(self, window_id: str, x: int, y: int, width: int, height: int) -> bool:
        if not self._initialized:
            return False
        try:
            hwnd = int(window_id)
            self._win32gui.SetWindowPos(
                hwnd, None, x, y, width, height,
                self._win32con.SWP_NOZORDER | self._win32con.SWP_NOACTIVATE
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set window position: {e}")
            return False

    def get_active_window(self) -> Optional[WindowInfo]:
        if not self._initialized:
            return None
        try:
            hwnd = self._win32gui.GetForegroundWindow()
            return self._get_window_info(hwnd)
        except Exception:
            return None

    def find_window_by_title(self, title: str) -> Optional[WindowInfo]:
        if not self._initialized:
            return None
        try:
            hwnd = self._win32gui.FindWindow(None, title)
            if hwnd:
                return self._get_window_info(hwnd)
        except Exception:
            pass
        for win in self.enumerate_windows():
            if title.lower() in win.title.lower():
                return win
        return None

    def find_window_by_process(self, process_name: str) -> List[WindowInfo]:
        return [w for w in self.enumerate_windows()
                if w.process_name.lower() == process_name.lower()]


class MacOSWindowManager(PlatformWindowManager):
    """macOS 窗口管理器 - AppKit"""

    def __init__(self):
        super().__init__()
        try:
            import AppKit
            self._appkit = AppKit
            self._initialized = True
            logger.info("MacOSWindowManager initialized (AppKit)")
        except ImportError:
            logger.warning("AppKit not available, macOS window manager unavailable")
            self._initialized = False

    def enumerate_windows(self) -> List[WindowInfo]:
        if not self._initialized:
            return []
        results = []
        for app in self._appkit.NSRunningApplication.currentApplication().runningApplications():
            if app.activationPolicy() == 0:
                try:
                    windows = app.windows()
                    for win in windows:
                        frame = win.frame()
                        results.append(WindowInfo(
                            hwnd=win.windowNumber(),
                            title=win.title() or app.localizedName(),
                            process_name=app.localizedName(),
                            bounds=(int(frame.origin.x), int(frame.origin.y),
                                    int(frame.size.width), int(frame.size.height)),
                            state=WindowState.NORMAL,
                            is_active=win.isKeyWindow(),
                            pid=app.processIdentifier()
                        ))
                except Exception:
                    pass
        return results

    def activate_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            win_num = int(window_id)
            for app in self._appkit.NSRunningApplication.currentApplication().runningApplications():
                if app.activationPolicy() == 0:
                    for win in app.windows():
                        if win.windowNumber() == win_num:
                            win.makeKeyAndOrderFront_(None)
                            app.activateWithOptions_(self._appkit.NSApplicationActivateIgnoringOtherApps)
                            return True
        except Exception as e:
            logger.error(f"Failed to activate window: {e}")
        return False

    def minimize_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            win_num = int(window_id)
            for app in self._appkit.NSRunningApplication.currentApplication().runningApplications():
                if app.activationPolicy() == 0:
                    for win in app.windows():
                        if win.windowNumber() == win_num:
                            win.miniaturize_(None)
                            return True
        except Exception as e:
            logger.error(f"Failed to minimize window: {e}")
        return False

    def maximize_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            win_num = int(window_id)
            screen = self._appkit.NSScreen.mainScreen().frame()
            for app in self._appkit.NSRunningApplication.currentApplication().runningApplications():
                if app.activationPolicy() == 0:
                    for win in app.windows():
                        if win.windowNumber() == win_num:
                            win.setFrame_display_(screen, True)
                            return True
        except Exception as e:
            logger.error(f"Failed to maximize window: {e}")
        return False

    def restore_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            win_num = int(window_id)
            for app in self._appkit.NSRunningApplication.currentApplication().runningApplications():
                if app.activationPolicy() == 0:
                    for win in app.windows():
                        if win.windowNumber() == win_num:
                            win.deminiaturize_(None)
                            return True
        except Exception as e:
            logger.error(f"Failed to restore window: {e}")
        return False

    def close_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            win_num = int(window_id)
            for app in self._appkit.NSRunningApplication.currentApplication().runningApplications():
                if app.activationPolicy() == 0:
                    for win in app.windows():
                        if win.windowNumber() == win_num:
                            win.close()
                            return True
        except Exception as e:
            logger.error(f"Failed to close window: {e}")
        return False

    def hide_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            win_num = int(window_id)
            for app in self._appkit.NSRunningApplication.currentApplication().runningApplications():
                if app.activationPolicy() == 0:
                    for win in app.windows():
                        if win.windowNumber() == win_num:
                            win.orderOut_(None)
                            return True
        except Exception as e:
            logger.error(f"Failed to hide window: {e}")
        return False

    def set_window_pos(self, window_id: str, x: int, y: int, width: int, height: int) -> bool:
        if not self._initialized:
            return False
        try:
            win_num = int(window_id)
            frame = self._appkit.NSMakeRect(x, y, width, height)
            for app in self._appkit.NSRunningApplication.currentApplication().runningApplications():
                if app.activationPolicy() == 0:
                    for win in app.windows():
                        if win.windowNumber() == win_num:
                            win.setFrame_display_(frame, True)
                            return True
        except Exception as e:
            logger.error(f"Failed to set window position: {e}")
        return False

    def get_active_window(self) -> Optional[WindowInfo]:
        if not self._initialized:
            return None
        try:
            front_app = self._appkit.NSWorkspace.shared().frontmostApplication()
            for win in front_app.windows():
                if win.isKeyWindow():
                    frame = win.frame()
                    return WindowInfo(
                        hwnd=win.windowNumber(),
                        title=win.title() or front_app.localizedName(),
                        process_name=front_app.localizedName(),
                        bounds=(int(frame.origin.x), int(frame.origin.y),
                                int(frame.size.width), int(frame.size.height)),
                        state=WindowState.NORMAL,
                        is_active=True,
                        pid=front_app.processIdentifier()
                    )
        except Exception:
            pass
        return None

    def find_window_by_title(self, title: str) -> Optional[WindowInfo]:
        for win in self.enumerate_windows():
            if title.lower() in win.title.lower():
                return win
        return None

    def find_window_by_process(self, process_name: str) -> List[WindowInfo]:
        return [w for w in self.enumerate_windows()
                if w.process_name.lower() == process_name.lower()]


class LinuxWindowManager(PlatformWindowManager):
    """Linux 窗口管理器 - wnck"""

    def __init__(self):
        super().__init__()
        try:
            import wnck
            self._wnck = wnck
            self._screen = wnck.screen_get_default()
            if self._screen:
                self._screen.force_update()
            self._initialized = True
            logger.info("LinuxWindowManager initialized (wnck)")
        except ImportError:
            logger.warning("wnck not installed, Linux window manager unavailable")
            self._initialized = False

    def _get_window_info_from_wnck(self, win) -> Optional[WindowInfo]:
        try:
            pid = win.get_pid()
            title = win.get_name()
            geometry = win.get_geometry()
            x, y = geometry.x(), geometry.y()
            w, h = geometry.width(), geometry.height()
            state = WindowState.NORMAL
            if win.is_minimized():
                state = WindowState.MINIMIZED
            elif win.is_maximized():
                state = WindowState.MAXIMIZED
            elif not win.is_visible():
                state = WindowState.HIDDEN
            try:
                import psutil
                proc = psutil.Process(pid)
                process_name = proc.name()
            except:
                process_name = "unknown"
            return WindowInfo(
                hwnd=win.xid,
                title=title,
                process_name=process_name,
                bounds=(x, y, x + w, y + h),
                state=state,
                is_active=win.is_active(),
                pid=pid
            )
        except Exception:
            return None

    def enumerate_windows(self) -> List[WindowInfo]:
        if not self._initialized:
            return []
        results = []
        if self._screen:
            self._screen.force_update()
            for win in self._screen.get_windows():
                info = self._get_window_info_from_wnck(win)
                if info:
                    results.append(info)
        return results

    def activate_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            xid = int(window_id)
            if self._screen:
                for win in self._screen.get_windows():
                    if win.xid == xid:
                        win.activate(int(self._screen.get_last_user_time()))
                        return True
        except Exception as e:
            logger.error(f"Failed to activate window: {e}")
        return False

    def minimize_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            xid = int(window_id)
            if self._screen:
                for win in self._screen.get_windows():
                    if win.xid == xid:
                        win.minimize()
                        return True
        except Exception as e:
            logger.error(f"Failed to minimize window: {e}")
        return False

    def maximize_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            xid = int(window_id)
            if self._screen:
                for win in self._screen.get_windows():
                    if win.xid == xid:
                        win.maximize()
                        return True
        except Exception as e:
            logger.error(f"Failed to maximize window: {e}")
        return False

    def restore_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            xid = int(window_id)
            if self._screen:
                for win in self._screen.get_windows():
                    if win.xid == xid:
                        win.unminimize()
                        return True
        except Exception as e:
            logger.error(f"Failed to restore window: {e}")
        return False

    def close_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            xid = int(window_id)
            if self._screen:
                for win in self._screen.get_windows():
                    if win.xid == xid:
                        win.close(int(self._screen.get_last_user_time()))
                        return True
        except Exception as e:
            logger.error(f"Failed to close window: {e}")
        return False

    def hide_window(self, window_id: str) -> bool:
        if not self._initialized:
            return False
        try:
            xid = int(window_id)
            if self._screen:
                for win in self._screen.get_windows():
                    if win.xid == xid:
                        win.minimize()
                        return True
        except Exception as e:
            logger.error(f"Failed to hide window: {e}")
        return False

    def set_window_pos(self, window_id: str, x: int, y: int, width: int, height: int) -> bool:
        if not self._initialized:
            return False
        try:
            xid = int(window_id)
            if self._screen:
                for win in self._screen.get_windows():
                    if win.xid == xid:
                        win.set_geometry(
                            self._wnck.WINDOW_GRAVITY_CURRENT,
                            self._wnck.WINDOW_CHANGE_X | self._wnck.WINDOW_CHANGE_Y |
                            self._wnck.WINDOW_CHANGE_WIDTH | self._wnck.WINDOW_CHANGE_HEIGHT,
                            x, y, width, height
                        )
                        return True
        except Exception as e:
            logger.error(f"Failed to set window position: {e}")
        return False

    def get_active_window(self) -> Optional[WindowInfo]:
        if not self._initialized or not self._screen:
            return None
        try:
            win = self._screen.get_active_window()
            return self._get_window_info_from_wnck(win) if win else None
        except Exception:
            return None

    def find_window_by_title(self, title: str) -> Optional[WindowInfo]:
        if not self._initialized or not self._screen:
            return None
        self._screen.force_update()
        for win in self._screen.get_windows():
            if title.lower() in win.get_name().lower():
                return self._get_window_info_from_wnck(win)
        return None

    def find_window_by_process(self, process_name: str) -> List[WindowInfo]:
        if not self._initialized:
            return []
        self._screen.force_update() if self._screen else None
        results = []
        for win in self._screen.get_windows():
            try:
                pid = win.get_pid()
                import psutil
                proc = psutil.Process(pid)
                if proc.name().lower() == process_name.lower():
                    info = self._get_window_info_from_wnck(win)
                    if info:
                        results.append(info)
            except Exception:
                pass
        return results


_window_manager: Optional[PlatformWindowManager] = None


class WindowManager:
    """
    统一窗口管理器接口
    自动检测平台并委托给对应实现
    """

    def __init__(self):
        self._impl: PlatformWindowManager = get_window_manager()
        self._platform = sys.platform

    def enumerate_windows(self) -> List[WindowInfo]:
        return self._impl.enumerate_windows()

    def get_window(self, window_id: str) -> Optional[WindowInfo]:
        for w in self.enumerate_windows():
            if str(w.hwnd) == window_id:
                return w
        return None

    def activate(self, window_id: str) -> bool:
        return self._impl.activate_window(window_id)

    def activate_by_title(self, title: str) -> bool:
        win = self._impl.find_window_by_title(title)
        if win:
            return self._impl.activate_window(str(win.hwnd))
        return False

    def minimize(self, window_id: str) -> bool:
        return self._impl.minimize_window(window_id)

    def maximize(self, window_id: str) -> bool:
        return self._impl.maximize_window(window_id)

    def restore(self, window_id: str) -> bool:
        return self._impl.restore_window(window_id)

    def close(self, window_id: str) -> bool:
        return self._impl.close_window(window_id)

    def hide(self, window_id: str) -> bool:
        return self._impl.hide_window(window_id)

    def move_resize(self, window_id: str, x: int, y: int, width: int, height: int) -> bool:
        return self._impl.set_window_pos(window_id, x, y, width, height)

    def center(self, window_id: str) -> bool:
        import subprocess
        try:
            if self._platform == "win32":
                user32 = __import__('ctypes').windll.user32
                sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            elif self._platform == "darwin":
                from AppKit import NSScreen
                screen = NSScreen.mainScreen().frame()
                sw, sh = int(screen.size.width), int(screen.size.height)
            else:
                output = subprocess.check_output(['xrandr'], text=True)
                lines = output.strip().split('\n')
                for line in lines:
                    if '*' in line:
                        dims = line.split()[0].split('x')
                        sw, sh = int(dims[0]), int(dims[1])
                        break
                else:
                    sw, sh = 1920, 1080
            for w in self.enumerate_windows():
                if str(w.hwnd) == window_id:
                    x = (sw - w.bounds[2] + w.bounds[0]) // 2
                    y = (sh - w.bounds[3] + w.bounds[1]) // 2
                    return self._impl.set_window_pos(window_id, x, y, w.bounds[2] - w.bounds[0], w.bounds[3] - w.bounds[1])
        except Exception as e:
            logger.error(f"Failed to center window: {e}")
        return False

    def get_active(self) -> Optional[WindowInfo]:
        return self._impl.get_active_window()

    def find_by_title(self, title: str) -> Optional[WindowInfo]:
        return self._impl.find_window_by_title(title)

    def find_by_process(self, process_name: str) -> List[WindowInfo]:
        return self._impl.find_window_by_process(process_name)

    def screenshot_window(self, window_id: str) -> Optional[Any]:
        for w in self.enumerate_windows():
            if str(w.hwnd) == window_id:
                from .input_controller import Screenshot, Rectangle
                sc = Screenshot()
                import asyncio
                asyncio.run(sc.initialize())
                x, y, x2, y2 = w.bounds
                region = Rectangle(x=x, y=y, width=x2 - x, height=y2 - y)
                return asyncio.run(sc.capture(region))
        return None


def get_window_manager() -> PlatformWindowManager:
    global _window_manager
    if _window_manager is None:
        platform = sys.platform
        if platform == "win32":
            _window_manager = WindowsWindowManager()
        elif platform == "darwin":
            _window_manager = MacOSWindowManager()
        else:
            _window_manager = LinuxWindowManager()
        logger.info(f"Window manager initialized: {type(_window_manager).__name__}")
    return _window_manager
