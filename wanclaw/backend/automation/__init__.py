"""WanClaw 桌面自动化模块 V2.0"""

from .input_controller import (
    InputController,
    Screenshot,
    VisionController,
    AutomationWorkflow,
    ActionCache,
    ActionSequence,
    get_input_controller,
    get_vision_controller,
    MouseButton,
    KeyModifier,
    Point,
    Rectangle,
)

from .window_manager import (
    WindowManager,
    PlatformWindowManager,
    WindowsWindowManager,
    MacOSWindowManager,
    LinuxWindowManager,
    WindowState,
    WindowInfo,
    get_window_manager,
)

from .app_launcher import (
    SecureAppLauncher,
    AppInfo,
    DEFAULT_WHITELIST,
    get_app_launcher,
)

__all__ = [
    # 输入控制
    'InputController',
    'Screenshot',
    'VisionController',
    'AutomationWorkflow',
    'ActionCache',
    'ActionSequence',
    'get_input_controller',
    'get_vision_controller',
    'MouseButton',
    'KeyModifier',
    'Point',
    'Rectangle',
    # 窗口管理
    'WindowManager',
    'PlatformWindowManager',
    'WindowsWindowManager',
    'MacOSWindowManager',
    'LinuxWindowManager',
    'WindowState',
    'WindowInfo',
    'get_window_manager',
    # 安全启动器
    'SecureAppLauncher',
    'AppInfo',
    'DEFAULT_WHITELIST',
    'get_app_launcher',
]