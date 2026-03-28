"""
桌面自动化模块 V2.0
优化算法：视觉定位、智能等待、动作优化
"""

import asyncio
import json
import logging
import time
import uuid
import hashlib
from typing import Dict, Any, Optional, Tuple, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from collections import deque, OrderedDict
import weakref

logger = logging.getLogger(__name__)


class MouseButton(Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class KeyModifier(Enum):
    CTRL = "ctrl"
    SHIFT = "shift"
    ALT = "alt"
    WIN = "win"


@dataclass
class Point:
    x: int
    y: int
    
    def to_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)
    
    def distance_to(self, other: 'Point') -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


@dataclass
class Rectangle:
    x: int
    y: int
    width: int
    height: int
    
    @property
    def center(self) -> Point:
        return Point(
            x=self.x + self.width // 2,
            y=self.y + self.height // 2,
        )
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    def contains(self, point: Point) -> bool:
        return self.x <= point.x < self.x + self.width and self.y <= point.y < self.y + self.height
    
    def iou(self, other: 'Rectangle') -> float:
        """计算两个矩形的IOU"""
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x + self.width, other.x + other.width)
        y2 = min(self.y + self.height, other.y + other.height)
        
        if x1 >= x2 or y1 >= y2:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        union = self.area + other.area - intersection
        
        return intersection / union if union > 0 else 0.0

    def intersects(self, other: 'Rectangle') -> bool:
        """检查两个矩形是否相交"""
        return not (
            self.x + self.width <= other.x or
            other.x + other.width <= self.x or
            self.y + self.height <= other.y or
            other.y + other.height <= self.y
        )


class WindowManager:
    """窗口管理器"""

    def __init__(self):
        self._windows: Dict[str, Rectangle] = {}
        self._active_window: Optional[str] = None

    def register_window(self, window_id: str, bounds: Rectangle):
        self._windows[window_id] = bounds

    def unregister_window(self, window_id: str):
        self._windows.pop(window_id, None)
        if self._active_window == window_id:
            self._active_window = None

    def get_window_bounds(self, window_id: str) -> Optional[Rectangle]:
        return self._windows.get(window_id)

    def set_active_window(self, window_id: str):
        if window_id in self._windows:
            self._active_window = window_id

    def get_active_window(self) -> Optional[str]:
        return self._active_window

    def get_all_windows(self) -> Dict[str, Rectangle]:
        return dict(self._windows)

    def bring_to_front(self, window_id: str) -> bool:
        if window_id in self._windows:
            self._active_window = window_id
            return True
        return False

    def minimize(self, window_id: str) -> bool:
        if window_id in self._windows:
            return True
        return False

    def maximize(self, window_id: str) -> bool:
        if window_id in self._windows:
            bounds = self._windows[window_id]
            bounds.width = 1920
            bounds.height = 1080
            return True
        return False


_window_manager: Optional[WindowManager] = None


def get_window_manager() -> WindowManager:
    """获取窗口管理器单例"""
    global _window_manager
    if _window_manager is None:
        _window_manager = WindowManager()
    return _window_manager


class AutomationWorkflow:
    """自动化工作流 - 链接多个自动化步骤"""

    def __init__(self, name: str = ""):
        self.name = name
        self._steps: List[Tuple[str, Callable, Dict]] = []
        self._results: Dict[str, Any] = {}

    def add_step(self, step_name: str, action: Callable, params: Dict = None):
        self._steps.append((step_name, action, params or {}))

    async def execute(self) -> Dict[str, Any]:
        for step_name, action, params in self._steps:
            try:
                if asyncio.iscoroutinefunction(action):
                    result = await action(**params)
                else:
                    result = action(**params)
                self._results[step_name] = result
            except Exception as e:
                self._results[step_name] = {"error": str(e)}
                logger.error(f"Workflow step {step_name} failed: {e}")
                break
        return self._results

    def get_results(self) -> Dict[str, Any]:
        return self._results

    def clear(self):
        self._steps.clear()
        self._results.clear()


class ActionCache:
    
    def __init__(self, max_size: int = 100):
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self.max_size = max_size
    
    def _make_key(self, action: str, params: Dict) -> str:
        key_data = f"{action}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, action: str, params: Dict) -> Optional[Any]:
        key = self._make_key(action, params)
        
        if key in self._cache:
            result, timestamp = self._cache[key]
            if time.time() - timestamp < 300:
                self._cache.move_to_end(key)
                return result
            else:
                del self._cache[key]
        
        return None
    
    def set(self, action: str, params: Dict, result: Any):
        key = self._make_key(action, params)
        
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)
        
        self._cache[key] = (result, time.time())
        self._cache.move_to_end(key)


class ActionSequence:
    """动作序列 - 批量操作优化"""
    
    def __init__(self, controller: 'InputController'):
        self.controller = controller
        self._actions: List[Dict] = []
        self._enabled = True
    
    def add_move(self, x: int, y: int, duration: float = 0.0):
        self._actions.append(("move", (x, y), {"duration": duration}))
        return self
    
    def add_click(self, x: int = None, y: int = None, button: MouseButton = MouseButton.LEFT):
        self._actions.append(("click", (x, y), {"button": button}))
        return self
    
    def add_type(self, text: str, interval: float = 0.0):
        self._actions.append(("type", (text,), {"interval": interval}))
        return self
    
    async def execute(self) -> List[Dict]:
        """批量执行动作"""
        results = []
        
        if not self._enabled:
            return results
        
        actions = list(self._actions)
        self._actions.clear()
        
        merged = []
        last_click_pos = None
        last_click_button = None
        
        for action_type, args, kwargs in actions:
            if action_type == "move":
                if merged and merged[-1][0] == "move":
                    merged[-1] = (action_type, args, kwargs)
                else:
                    merged.append((action_type, args, kwargs))
            elif action_type == "click":
                pos = args
                btn = kwargs.get("button", MouseButton.LEFT)
                if last_click_pos == pos and last_click_button == btn:
                    continue
                merged.append((action_type, args, kwargs))
                last_click_pos = pos
                last_click_button = btn
            else:
                merged.append((action_type, args, kwargs))
        
        for action_type, args, kwargs in merged:
            try:
                if action_type == "move":
                    await self.controller.move_to(*args, **kwargs)
                elif action_type == "click":
                    await self.controller.click(*args, **kwargs)
                elif action_type == "type":
                    await self.controller.type_text(*args, **kwargs)
                
                results.append({"action": action_type, "success": True})
                
            except Exception as e:
                results.append({"action": action_type, "success": False, "error": str(e)})
        
        return results


class InputController:
    """鼠标键盘控制器 V2.0"""
    
    def __init__(self, safety_mode: bool = True):
        self.safety_mode = safety_mode
        self._pyautogui = None
        self._initialized = False
        self._cache = ActionCache(max_size=100)
        self._last_position = None
        self._action_sequence: Optional[ActionSequence] = None
        self._screen_size: Optional[Tuple[int, int]] = None
    
    async def initialize(self):
        """初始化"""
        try:
            import pyautogui
            self._pyautogui = pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.05
            self._initialized = True
            size = pyautogui.size()
            self._screen_size = (size.width, size.height)
            logger.info("InputController V2.0 initialized")
        except ImportError:
            logger.warning("pyautogui not installed")
            self._initialized = False
    
    def _validate_bounds(self, x: int, y: int) -> bool:
        if self._screen_size is None:
            return True
        w, h = self._screen_size
        return 0 <= x < w and 0 <= y < h
    
    def _check_init(self):
        if not self._initialized:
            raise RuntimeError("InputController not initialized")
    
    def begin_sequence(self) -> ActionSequence:
        """开始动作序列"""
        self._action_sequence = ActionSequence(self)
        return self._action_sequence
    
    async def commit_sequence(self) -> List[Dict]:
        """提交动作序列"""
        if self._action_sequence:
            results = await self._action_sequence.execute()
            self._action_sequence = None
            return results
        return []
    
    async def move_to(self, x: int, y: int, duration: float = 0.0):
        """移动鼠标"""
        self._check_init()
        
        if self.safety_mode and not self._validate_bounds(x, y):
            raise ValueError(f"Coordinates ({x}, {y}) outside screen bounds {self._screen_size}")
        
        self._pyautogui.moveTo(x, y, duration=duration)
        self._last_position = Point(x, y)
        logger.debug(f"Moved to ({x}, {y})")
    
    async def move_relative(self, dx: int, dy: int, duration: float = 0.0):
        """相对移动"""
        self._check_init()
        self._pyautogui.move(dx, dy, duration=duration)
    
    async def click(self, x: int = None, y: int = None, button: MouseButton = MouseButton.LEFT):
        """点击"""
        self._check_init()
        
        if x is not None and y is not None:
            if self.safety_mode and not self._validate_bounds(x, y):
                raise ValueError(f"Coordinates ({x}, {y}) outside screen bounds {self._screen_size}")
        
        self._pyautogui.click(x, y, button=button.value)
        logger.debug(f"Clicked at ({x}, {y}) with {button.value}")
    
    async def double_click(self, x: int = None, y: int = None, button: MouseButton = MouseButton.LEFT):
        """双击"""
        self._check_init()
        self._pyautogui.doubleClick(x, y, button=button.value)
    
    async def right_click(self, x: int = None, y: int = None):
        """右键点击"""
        await self.click(x, y, MouseButton.RIGHT)
    
    async def middle_click(self, x: int = None, y: int = None):
        """中键点击"""
        await self.click(x, y, MouseButton.MIDDLE)
    
    async def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5):
        """拖拽"""
        self._check_init()
        
        if self.safety_mode:
            if not self._validate_bounds(start_x, start_y):
                raise ValueError(f"Start coordinates ({start_x}, {start_y}) outside screen bounds")
            if not self._validate_bounds(end_x, end_y):
                raise ValueError(f"End coordinates ({end_x}, {end_y}) outside screen bounds")
        
        self._pyautogui.moveTo(start_x, start_y)
        self._pyautogui.dragTo(end_x, end_y, duration=duration, button='left')
    
    async def type_text(self, text: str, interval: float = 0.0):
        """输入文本"""
        self._check_init()
        self._pyautogui.write(text, interval=interval)
        logger.debug(f"Typed: {text[:20]}...")
    
    async def press_key(self, key: str):
        """按键"""
        self._check_init()
        self._pyautogui.press(key)
    
    async def hotkey(self, *keys):
        """组合键"""
        self._check_init()
        self._pyautogui.hotkey(*keys)
    
    async def scroll(self, clicks: int, x: int = None, y: int = None):
        """滚动"""
        self._check_init()
        self._pyautogui.scroll(clicks, x, y)
    
    async def get_position(self) -> Tuple[int, int]:
        """获取鼠标位置"""
        self._check_init()
        pos = self._pyautogui.position()
        return (pos.x, pos.y)
    
    async def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        self._check_init()
        if self._screen_size:
            return self._screen_size
        size = self._pyautogui.size()
        self._screen_size = (size.width, size.height)
        return self._screen_size
    
    async def smart_wait(
        self,
        vision_controller: 'VisionController',
        target: str,
        locate_method: str = "text",
        timeout: int = 30,
    ) -> Optional[Point]:
        """等待元素出现在指定位置后返回坐标"""
        point = await vision_controller.wait_for_element(locate_method, target, timeout=timeout)
        if point and self.safety_mode and not self._validate_bounds(point.x, point.y):
            raise ValueError(f"Element position ({point.x}, {point.y}) outside screen bounds")
        return point


class VisionController:
    """视觉定位控制器 V2.0 - 多策略融合 + EasyOCR备选"""
    
    def __init__(self):
        self.screenshot = Screenshot()
        self._ocr = None
        self._easyocr = None
        self._easyocr_reader = None
        self._cv2 = None
        self._np = None
        self._cache = ActionCache(max_size=200)
        self._confidence_threshold = 0.7
        self._max_retries = 3
        self._retry_delay = 0.5
        self._ocr_backend = "none"
        self._session_ocr_cache: Dict[str, Tuple[List[Dict], float]] = {}
    
    async def initialize(self):
        """初始化 - 按优先级探测 OCR 后端"""
        await self.screenshot.initialize()
        
        # 1. pytesseract (最高精度，需安装 Tesseract OCR 引擎)
        try:
            import pytesseract
            self._ocr = pytesseract
            self._ocr_backend = "tesseract"
            logger.info("OCR backend: tesseract (primary)")
        except ImportError:
            logger.warning("pytesseract not installed")
        
        # 2. EasyOCR (纯 Python，无需额外安装引擎，支持 80+ 语言)
        if not self._ocr:
            try:
                import easyocr
                self._easyocr_reader = easyocr.Reader(
                    ['ch_sim', 'en'],
                    gpu=False,
                    verbose=False
                )
                self._easyocr = easyocr
                self._ocr_backend = "easyocr"
                logger.info("OCR backend: easyocr (fallback)")
            except ImportError:
                logger.warning("easyocr not installed")
            except Exception as e:
                logger.warning(f"easyocr init failed: {e}")
        
        # OpenCV
        try:
            import cv2
            import numpy as np
            self._cv2 = cv2
            self._np = np
        except ImportError:
            logger.warning("opencv not installed")
    
    async def recognize_text(self, region: Rectangle = None, lang: str = "zh_en") -> List[Dict]:
        img = await self.screenshot.capture(region)
        
        cache_key = str(id(img)) if id(img) else None
        if cache_key and cache_key in self._session_ocr_cache:
            cached_results, cached_at = self._session_ocr_cache[cache_key]
            if time.time() - cached_at < 5.0:
                return cached_results
        
        results = []
        last_error = None
        
        for attempt in range(self._max_retries):
            try:
                if self._ocr:
                    try:
                        if self._np:
                            if len(img.shape) == 3:
                                gray = self._cv2.cvtColor(img, self._cv2.COLOR_BGR2GRAY)
                            else:
                                gray = img
                            data = self._ocr.image_to_data(gray, output_type=self._ocr.Output.DICT)
                            for i, txt in enumerate(data['text']):
                                if txt.strip():
                                    conf = data['conf'][i] / 100.0 if data['conf'][i] > 0 else 0.5
                                    if conf >= self._confidence_threshold:
                                        results.append({
                                            "text": txt,
                                            "bbox": (data['left'][i], data['top'][i],
                                                     data['left'][i] + data['width'][i],
                                                     data['top'][i] + data['height'][i]),
                                            "confidence": conf,
                                            "backend": "tesseract"
                                        })
                    except Exception as e:
                        logger.error(f"tesseract OCR error: {e}")
                
                if not results and self._easyocr_reader:
                    try:
                        if self._np:
                            is_list = isinstance(img, list)
                            if len(img.shape) == 3 and img.shape[2] == 4:
                                img = self._cv2.cvtColor(img, self._cv2.COLOR_BGRA2BGR)
                            elif len(img.shape) == 2:
                                img = self._cv2.cvtColor(img, self._cv2.COLOR_GRAY2BGR)
                        raw_results = self._easyocr_reader.readtext(
                            self._np.array(img) if self._np else img
                        )
                        for (bbox, text, conf) in raw_results:
                            if text.strip() and conf >= self._confidence_threshold:
                                x_coords = [p[0] for p in bbox]
                                y_coords = [p[1] for p in bbox]
                                results.append({
                                    "text": text,
                                    "bbox": (min(x_coords), min(y_coords),
                                             max(x_coords), max(y_coords)),
                                    "confidence": conf,
                                    "backend": "easyocr"
                                })
                    except Exception as e:
                        logger.error(f"easyocr error: {e}")
                
                if results:
                    break
                
            except Exception as e:
                last_error = e
            
            if attempt < self._max_retries - 1:
                delay = self._retry_delay * (2 ** attempt)
                await asyncio.sleep(delay)
        
        if cache_key:
            self._session_ocr_cache[cache_key] = (results, time.time())
        
        return results
    
    async def locate_by_text(self, text: str, region: Rectangle = None) -> Optional[Point]:
        cached = self._cache.get("locate_text", {"text": text, "region": str(region)})
        if cached:
            return cached
        
        results = await self.recognize_text(region)
        text_lower = text.lower()
        for item in results:
            if item.get("confidence", 0) >= self._confidence_threshold and text_lower in item["text"].lower():
                x1, y1, x2, y2 = item["bbox"]
                point = Point(x=(x1 + x2) // 2, y=(y1 + y2) // 2)
                self._cache.set("locate_text", {"text": text, "region": str(region)}, point)
                return point
        return None
    
    async def locate_by_image(self, template_path: str, confidence: float = 0.8) -> Optional[Point]:
        """模板匹配定位"""
        cached = self._cache.get("locate_image", {"path": template_path})
        if cached:
            return cached
        
        result = await self.screenshot.find_image(template_path, confidence)
        if result:
            point = result.center
            self._cache.set("locate_image", {"path": template_path}, point)
            return point
        
        return None
    
    async def locate_by_color(self, color: Tuple[int, int, int], tolerance: int = 10, region: Rectangle = None) -> List[Point]:
        """颜色定位"""
        if not self._cv2:
            return []
        
        img = await self.screenshot.capture(region)
        
        if len(img.shape) == 3 and img.shape[2] == 4:
            img = self._cv2.cvtColor(img, self._cv2.COLOR_BGRA2BGR)
        
        lower = self._np.array([max(0, c - tolerance) for c in color])
        upper = self._np.array([min(255, c + tolerance) for c in color])
        mask = self._cv2.inRange(img, lower, upper)
        
        contours, _ = self._cv2.findContours(mask, self._cv2.RETR_EXTERNAL, self._cv2.CHAIN_APPROX_SIMPLE)
        
        points = []
        for cnt in contours:
            M = self._cv2.moments(cnt)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                points.append(Point(x=cx, y=cy))
        
        return points
    
    async def locate_fuzzy(self, description: str, region: Rectangle = None) -> Optional[Point]:
        """模糊定位 - 组合多种策略"""
        strategies = [
            ("exact_text", self.locate_by_text),
            ("image", self.locate_by_image),
        ]
        
        for name, strategy in strategies:
            if name == "exact_text":
                result = await strategy(description, region)
            else:
                result = await strategy(description)
            
            if result:
                logger.debug(f"Fuzzy locate succeeded via {name}: {description}")
                return result
        
        return None
    
    async def wait_for_element(
        self,
        locate_method: str,
        target: str,
        timeout: int = 30,
        interval: float = 0.5,
    ) -> Optional[Point]:
        """智能等待元素出现"""
        start = time.time()
        last_error = None
        
        while time.time() - start < timeout:
            try:
                if locate_method == "text":
                    point = await self.locate_by_text(target)
                elif locate_method == "image":
                    point = await self.locate_by_image(target)
                elif locate_method == "fuzzy":
                    point = await self.locate_fuzzy(target)
                else:
                    point = None
                
                if point:
                    return point
                    
            except Exception as e:
                last_error = e
            
            await asyncio.sleep(interval)
        
        logger.warning(f"wait_for_element timeout: {target}, last_error: {last_error}")
        return None

    async def smart_wait_ocr(
        self,
        text: str,
        region: Rectangle = None,
        timeout: int = 30,
        initial_delay: float = 0.1,
    ) -> Optional[Point]:
        """Smart wait for OCR text with exponential backoff"""
        start = time.time()
        delay = initial_delay
        
        while time.time() - start < timeout:
            point = await self.locate_by_text(text, region)
            if point:
                return point
            
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 2.0)
        
        return None
    
    async def click_element(
        self,
        locate_method: str,
        target: str,
        input_controller: InputController,
        timeout: int = 10,
    ) -> bool:
        """点击元素"""
        point = await self.wait_for_element(locate_method, target, timeout=timeout)
        
        if point:
            await input_controller.click(point.x, point.y)
            return True
        
        return False
    
    def get_ocr_backend(self) -> str:
        return self._ocr_backend


class Screenshot:
    """截图与图像处理 V2.0
    
    支持多种截图后端（优先级: mss > pyscreenshot > pyautogui > PIL）
    所有方案均不调用 subprocess，纯系统 API
    """
    
    _cached_backend: Optional[str] = None
    _cached_mss: Optional[Any] = None
    _cached_pyscreenshot: Optional[Any] = None
    _cached_PIL_ImageGrab: Optional[Any] = None
    _cached_pyautogui: Optional[Any] = None
    
    def __init__(self):
        self._cv2 = None
        self._np = None
        self._mss = None
        self._pyscreenshot = None
        self._PIL_ImageGrab = None
        self._pyautogui = None
        self._backend = "none"
        self._initialized = False
    
    async def initialize(self):
        """初始化 - 按优先级探测截图后端（结果被类级缓存）"""
        try:
            import cv2
            import numpy as np
            self._cv2 = cv2
            self._np = np
        except ImportError:
            logger.warning("opencv not installed")

        if Screenshot._cached_backend is not None:
            self._backend = Screenshot._cached_backend
            self._mss = Screenshot._cached_mss
            self._pyscreenshot = Screenshot._cached_pyscreenshot
            self._PIL_ImageGrab = Screenshot._cached_PIL_ImageGrab
            self._pyautogui = Screenshot._cached_pyautogui
            self._initialized = True
            logger.info(f"Screenshot backend: {self._backend} (cached)")
            return

        # 1. mss - 最快，纯 C 实现
        try:
            import mss
            Screenshot._cached_mss = mss
            Screenshot._cached_backend = "mss"
            self._mss = mss
            self._backend = "mss"
            self._initialized = True
            logger.info("Screenshot backend: mss (fastest)")
            return
        except ImportError:
            pass

        # 2. pyscreenshot - 跨平台，纯 PIL/PyQt
        try:
            import pyscreenshot
            Screenshot._cached_pyscreenshot = pyscreenshot
            Screenshot._cached_backend = "pyscreenshot"
            self._pyscreenshot = pyscreenshot
            self._backend = "pyscreenshot"
            self._initialized = True
            logger.info("Screenshot backend: pyscreenshot")
            return
        except ImportError:
            pass

        # 3. PIL.ImageGrab - Python自带
        try:
            from PIL import ImageGrab
            Screenshot._cached_PIL_ImageGrab = ImageGrab
            Screenshot._cached_backend = "pil"
            self._PIL_ImageGrab = ImageGrab
            self._backend = "pil"
            self._initialized = True
            logger.info("Screenshot backend: PIL.ImageGrab")
            return
        except ImportError:
            pass

        # 4. pyautogui - 最终回退
        try:
            import pyautogui
            Screenshot._cached_pyautogui = pyautogui
            Screenshot._cached_backend = "pyautogui"
            self._pyautogui = pyautogui
            self._backend = "pyautogui"
            self._initialized = True
            logger.info("Screenshot backend: pyautogui")
            return
        except ImportError:
            pass

        logger.error("No screenshot backend available")
    
    async def capture(self, region: Rectangle = None) -> Any:
        """截图 - 根据可用后端选择最佳方案"""
        if not self._initialized:
            raise RuntimeError("Screenshot not initialized")
        
        if region:
            bbox = (region.x, region.y, region.x + region.width, region.y + region.height)
        else:
            bbox = None

        # mss 优先
        if self._mss:
            with self._mss.mss() as sct:
                monitor = sct.monitors[0] if not bbox else {
                    "left": bbox[0], "top": bbox[1],
                    "width": bbox[2] - bbox[0], "height": bbox[3] - bbox[1]
                }
                img = sct.grab(monitor)
                return self._np.array(img) if self._np else img

        # pyscreenshot
        if self._pyscreenshot:
            img = self._pyscreenshot.grab(bbox=bbox)
            return self._np.array(img) if self._np else img

        # PIL.ImageGrab
        if self._PIL_ImageGrab:
            if bbox:
                img = self._PIL_ImageGrab.grab(bbox=bbox)
            else:
                img = self._PIL_ImageGrab.grab()
            return self._np.array(img) if self._np else img

        # pyautogui 回退
        if self._pyautogui:
            img = self._pyautogui.screenshot()
            if region and self._np:
                import numpy as np
                arr = self._np.array(img)
                return arr[region.y:region.y + region.height, region.x:region.x + region.width]
            return img

        raise RuntimeError("No screenshot backend available")
    
    async def save(self, path: str, region: Rectangle = None) -> str:
        """截图并保存到文件"""
        img = await self.capture(region)
        if self._cv2 and hasattr(img, 'shape'):
            self._cv2.imwrite(path, img)
        elif hasattr(img, 'save'):
            img.save(path)
        else:
            from PIL import Image
            Image.fromarray(img).save(path)
        return path
    
    async def find_image(self, template_path: str, confidence: float = 0.8) -> Optional[Rectangle]:
        """模板匹配"""
        if not self._cv2:
            return None
        
        screenshot = await self.capture()
        template = self._cv2.imread(template_path)
        
        if template is None:
            return None
        
        if len(screenshot.shape) == 3:
            gray_screenshot = self._cv2.cvtColor(screenshot, self._cv2.COLOR_BGR2GRAY)
            gray_template = self._cv2.cvtColor(template, self._cv2.COLOR_BGR2GRAY)
        else:
            gray_screenshot = screenshot
            gray_template = template
        
        result = self._cv2.matchTemplate(gray_screenshot, gray_template, self._cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = self._cv2.minMaxLoc(result)
        
        if max_val >= confidence:
            w, h = gray_template.shape[1], gray_template.shape[0]
            return Rectangle(x=max_loc[0], y=max_loc[1], width=w, height=h)
        
        return None
    
    def get_backend(self) -> str:
        return self._backend


# 全局实例
_input_controller: Optional[InputController] = None
_vision_controller: Optional[VisionController] = None


async def get_input_controller() -> InputController:
    """获取输入控制器单例"""
    global _input_controller
    if _input_controller is None:
        _input_controller = InputController()
        await _input_controller.initialize()
    return _input_controller


async def get_vision_controller() -> VisionController:
    """获取视觉控制器单例"""
    global _vision_controller
    if _vision_controller is None:
        _vision_controller = VisionController()
        await _vision_controller.initialize()
    return _vision_controller