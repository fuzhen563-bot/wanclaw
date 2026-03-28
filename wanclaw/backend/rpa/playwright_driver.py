"""
浏览器RPA引擎
基于Playwright的浏览器自动化操作
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class BrowserType(Enum):
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class ElementLocatorType(Enum):
    ID = "id"
    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    PLACEHOLDER = "placeholder"
    ROLE = "role"
    LABEL = "label"


@dataclass
class ElementLocator:
    """元素定位器"""
    type: ElementLocatorType
    value: str
    value2: Optional[str] = None  # 用于role类型


@dataclass
class BrowserConfig:
    """浏览器配置"""
    browser_type: BrowserType = BrowserType.CHROMIUM
    headless: bool = True
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    user_agent: Optional[str] = None
    timeout: int = 30000
    slow_mo: int = 0


@dataclass
class RPAAction:
    """RPA动作"""
    action_type: str
    locator: Optional[ElementLocator] = None
    value: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)


class BrowserPool:
    """浏览器池管理"""
    
    def __init__(self, max_browsers: int = 5):
        self.max_browsers = max_browsers
        self.playwright = None
        self.browsers: List[Any] = []
        self.available: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    async def start(self):
        """启动浏览器池"""
        try:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            self._running = True
            logger.info(f"BrowserPool started with {self.max_browsers} browsers")
        except ImportError:
            logger.error("Playwright not installed")
            raise
    
    async def stop(self):
        """停止浏览器池"""
        self._running = False
        for browser in self.browsers:
            try:
                await browser.close()
            except:
                pass
        if self.playwright:
            await self.playwright.stop()
    
    @asynccontextmanager
    async def acquire(self, config: BrowserConfig = None):
        """获取浏览器实例"""
        config = config or BrowserConfig()
        
        # 尝试从池中获取
        browser = None
        try:
            browser = self.available.get_nowait()
        except asyncio.QueueEmpty:
            # 创建新浏览器
            browser = await self._create_browser(config)
        
        try:
            yield browser
            # 归还到池中
            if len(self.browsers) < self.max_browsers:
                self.available.put_nowait(browser)
            else:
                await browser.close()
        except Exception:
            await browser.close()
            raise
    
    async def _create_browser(self, config: BrowserConfig):
        """创建浏览器"""
        browser_type = getattr(self.playwright, config.browser_type.value)
        browser = await browser_type.launch(
            headless=config.headless,
            slow_mo=config.slow_mo,
        )
        self.browsers.append(browser)
        return browser


class BrowserDriver:
    """浏览器驱动"""
    
    def __init__(self, playwright, browser_type: BrowserType = BrowserType.CHROMIUM):
        self.playwright = playwright
        self.browser_type = browser_type
        self.browser = None
        self.context = None
        self.page = None
        self.config = BrowserConfig(browser_type=browser_type)
    
    async def launch(self, config: BrowserConfig = None):
        """启动浏览器"""
        self.config = config or self.config
        
        browser_type = getattr(self.playwright, self.config.browser_type.value)
        self.browser = await browser_type.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo,
        )
        
        self.context = await self.browser.new_context(
            viewport=self.config.viewport,
            user_agent=self.config.user_agent,
        )
        
        self.page = await self.context.new_page()
        logger.info(f"Browser launched: {self.config.browser_type.value}")
    
    async def goto(self, url: str, wait_until: str = "networkidle", timeout: int = None):
        """导航到URL"""
        timeout = timeout or self.config.timeout
        await self.page.goto(url, wait_until=wait_until, timeout=timeout)
        logger.debug(f"Navigated to: {url}")
    
    async def reload(self):
        """刷新页面"""
        await self.page.reload()
    
    async def go_back(self):
        """后退"""
        await self.page.go_back()
    
    async def go_forward(self):
        """前进"""
        await self.page.go_forward()
    
    async def screenshot(self, path: str = None, full_page: bool = False) -> Optional[bytes]:
        """截图"""
        if path:
            await self.page.screenshot(path=path, full_page=full_page)
            return None
        return await self.page.screenshot(full_page=full_page)
    
    async def close(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    # ===== 元素操作 =====
    
    async def _locate(self, locator: ElementLocator):
        """定位元素"""
        loc_type = locator.type
        value = locator.value
        
        if loc_type == ElementLocatorType.ID:
            return self.page.locator(f"#{value}")
        elif loc_type == ElementLocatorType.CSS:
            return self.page.locator(value)
        elif loc_type == ElementLocatorType.XPATH:
            return self.page.locator(f"xpath={value}")
        elif loc_type == ElementLocatorType.TEXT:
            return self.page.get_by_text(value, exact=False)
        elif loc_type == ElementLocatorType.PLACEHOLDER:
            return self.page.get_by_placeholder(value)
        elif loc_type == ElementLocatorType.ROLE:
            return self.page.get_by_role(locator.value, **locator.params)
        elif loc_type == ElementLocatorType.LABEL:
            return self.page.get_by_label(value)
        
        raise ValueError(f"Unknown locator type: {loc_type}")
    
    async def click(self, locator: ElementLocator, timeout: int = None):
        """点击元素"""
        element = await self._locate(locator)
        timeout = timeout or self.config.timeout
        await element.click(timeout=timeout)
    
    async def double_click(self, locator: ElementLocator, timeout: int = None):
        """双击元素"""
        element = await self._locate(locator)
        timeout = timeout or self.config.timeout
        await element.dblclick(timeout=timeout)
    
    async def right_click(self, locator: ElementLocator, timeout: int = None):
        """右键点击"""
        element = await self._locate(locator)
        timeout = timeout or self.config.timeout
        await element.click(button="right", timeout=timeout)
    
    async def fill(self, locator: ElementLocator, value: str, timeout: int = None):
        """填写输入框"""
        element = await self._locate(locator)
        timeout = timeout or self.config.timeout
        await element.fill(value, timeout=timeout)
    
    async def type_text(self, locator: ElementLocator, text: str, delay: int = 0, timeout: int = None):
        """输入文本（模拟按键）"""
        element = await self._locate(locator)
        timeout = timeout or self.config.timeout
        await element.type(text, delay=delay, timeout=timeout)
    
    async def press(self, locator: ElementLocator, key: str, timeout: int = None):
        """按键"""
        element = await self._locate(locator)
        timeout = timeout or self.config.timeout
        await element.press(key, timeout=timeout)
    
    async def select_option(self, locator: ElementLocator, value: str, timeout: int = None):
        """选择选项"""
        element = await self._locate(locator)
        timeout = timeout or self.config.timeout
        await element.select_option(value, timeout=timeout)
    
    async def check(self, locator: ElementLocator, timeout: int = None):
        """勾选复选框"""
        element = await self._locate(locator)
        timeout = timeout or self.config.timeout
        await element.check(timeout=timeout)
    
    async def uncheck(self, locator: ElementLocator, timeout: int = None):
        """取消勾选"""
        element = await self._locate(locator)
        timeout = timeout or self.config.timeout
        await element.uncheck(timeout=timeout)
    
    async def hover(self, locator: ElementLocator, timeout: int = None):
        """悬停"""
        element = await self._locate(locator)
        timeout = timeout or self.config.timeout
        await element.hover(timeout=timeout)
    
    async def scroll_into_view(self, locator: ElementLocator, timeout: int = None):
        """滚动到元素可见"""
        element = await self._locator(locator)
        timeout = timeout or self.config.timeout
        await element.scroll_into_view_if_needed(timeout=timeout)
    
    # ===== 等待操作 =====
    
    async def wait_for_load_state(self, state: str = "networkidle", timeout: int = None):
        """等待加载状态"""
        timeout = timeout or self.config.timeout
        await self.page.wait_for_load_state(state, timeout=timeout)
    
    async def wait_for_selector(self, locator: ElementLocator, timeout: int = None, state: str = "visible"):
        """等待元素出现"""
        element = await self._locate(locator)
        timeout = timeout or self.config.timeout
        await element.wait_for(state=state, timeout=timeout)
    
    async def wait_for_url(self, url_pattern: str, timeout: int = None):
        """等待URL变化"""
        timeout = timeout or self.config.timeout
        await self.page.wait_for_url(url_pattern, timeout=timeout)
    
    async def wait_for_navigation(self, timeout: int = None):
        """等待导航完成"""
        timeout = timeout or self.config.timeout
        await self.page.wait_for_load_state("networkidle", timeout=timeout)
    
    # ===== 获取数据 =====
    
    async def get_text(self, locator: ElementLocator, timeout: int = None) -> str:
        """获取元素文本"""
        element = await self._locate(locator)
        timeout = timeout or self.config.timeout
        return await element.text_content(timeout=timeout) or ""
    
    async def get_attribute(self, locator: ElementLocator, name: str, timeout: int = None) -> Optional[str]:
        """获取元素属性"""
        element = await self._locate(locator)
        timeout = timeout or self.config.timeout
        return await element.get_attribute(name, timeout=timeout)
    
    async def get_inner_html(self, locator: ElementLocator, timeout: int = None) -> str:
        """获取元素HTML"""
        element = await self._locate(locator)
        timeout = timeout or self.config.timeout
        return await element.inner_html(timeout=timeout) or ""
    
    async def is_visible(self, locator: ElementLocator) -> bool:
        """检查元素是否可见"""
        element = await self._locate(locator)
        return await element.is_visible()
    
    async def is_enabled(self, locator: ElementLocator) -> bool:
        """检查元素是否可用"""
        element = await self._locate(locator)
        return await element.is_enabled()
    
    # ===== 执行JS =====
    
    async def evaluate(self, script: str):
        """执行JavaScript"""
        return await self.page.evaluate(script)
    
    async def eval_on_selector(self, selector: str, script: str):
        """在元素上执行JavaScript"""
        return await self.page.eval_on_selector(selector, script)


class SmartElementLocator:
    """智能元素定位（AI辅助）"""
    
    def __init__(self, ai_model=None):
        self.ai = ai_model
    
    async def locate(self, description: str, page) -> Optional[Any]:
        """AI驱动的元素定位"""
        if self.ai:
            # AI生成选择器
            selector = await self._ai_generate_selector(description, page)
            if selector:
                return page.locator(selector).first
        
        # 回退到基础定位
        return await self._fallback_locate(description, page)
    
    async def _ai_generate_selector(self, description: str, page) -> Optional[str]:
        """AI生成选择器"""
        # 获取页面结构
        page_html = await page.content()
        
        # 调用AI生成选择器
        # 这里需要根据实际的AI模型实现
        prompt = f"""请根据以下描述生成CSS选择器：
描述: {description}
页面HTML: {page_html[:2000]}

请返回CSS选择器，不要其他内容。"""
        
        # 实际调用AI的代码需要根据模型实现
        return None
    
    async def _fallback_locate(self, description: str, page) -> Optional[Any]:
        """基础定位策略"""
        # 1. 文本匹配
        try:
            return page.get_by_text(description).first
        except:
            pass
        
        # 2. 占位符匹配
        try:
            return page.get_by_placeholder(description).first
        except:
            pass
        
        # 3. 按钮/链接文本
        try:
            return page.get_by_role("button", name=description).first
        except:
            pass
        
        # 4. 链接文本
        try:
            return page.get_by_role("link", name=description).first
        except:
            pass
        
        return None


class RPAManager:
    """RPA管理器"""
    
    def __init__(self):
        self.browser_pool = BrowserPool()
        self.playwright = None
        self._running = False
    
    async def start(self):
        """启动RPA管理器"""
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()
        await self.browser_pool.start()
        self._running = True
        logger.info("RPAManager started")
    
    async def stop(self):
        """停止RPA管理器"""
        self._running = False
        await self.browser_pool.stop()
        if self.playwright:
            await self.playwright.stop()
    
    @asynccontextmanager
    async def new_browser(self, config: BrowserConfig = None):
        """创建新浏览器"""
        driver = BrowserDriver(self.playwright, config.browser_type if config else BrowserType.CHROMIUM)
        await driver.launch(config)
        try:
            yield driver
        finally:
            await driver.close()
    
    async def execute(self, action: str, target: str = None, params: Dict = None) -> Dict[str, Any]:
        """执行RPA操作"""
        if action == "launch_browser":
            async with self.new_browser() as browser:
                return {"status": "success", "browser": "launched"}
        
        elif action == "goto":
            async with self.new_browser() as browser:
                await browser.goto(target)
                return {"status": "success", "url": target}
        
        elif action == "screenshot":
            async with self.new_browser() as browser:
                await browser.goto(target)
                data = await browser.screenshot()
                return {"status": "success", "screenshot": len(data)}
        
        return {"error": f"Unknown action: {action}"}


# 全局实例
_rpa_manager: Optional[RPAManager] = None


async def get_rpa_manager() -> RPAManager:
    """获取RPA管理器单例"""
    global _rpa_manager
    if _rpa_manager is None:
        _rpa_manager = RPAManager()
        await _rpa_manager.start()
    return _rpa_manager


# 便捷函数
def locate_by_id(value: str) -> ElementLocator:
    return ElementLocator(ElementLocatorType.ID, value)


def locate_by_css(value: str) -> ElementLocator:
    return ElementLocator(ElementLocatorType.CSS, value)


def locate_by_xpath(value: str) -> ElementLocator:
    return ElementLocator(ElementLocatorType.XPATH, value)


def locate_by_text(value: str) -> ElementLocator:
    return ElementLocator(ElementLocatorType.TEXT, value)


def locate_by_placeholder(value: str) -> ElementLocator:
    return ElementLocator(ElementLocatorType.PLACEHOLDER, value)


def locate_by_role(value: str, **kwargs) -> ElementLocator:
    return ElementLocator(ElementLocatorType.ROLE, value, params=kwargs)