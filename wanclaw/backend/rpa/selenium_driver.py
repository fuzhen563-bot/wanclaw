"""
Selenium RPA 引擎 V2.0
作为 Playwright 的备份方案，支持 Chrome/Firefox/Edge

不执行 subprocess，纯浏览器驱动
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SeleniumBrowser(Enum):
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"


@dataclass
class SeleniumConfig:
    browser: SeleniumBrowser = SeleniumBrowser.CHROME
    headless: bool = True
    window_size: tuple = (1920, 1080)
    user_agent: Optional[str] = None
    implicit_wait: int = 10
    page_load_timeout: int = 30


class SeleniumDriver:
    """Selenium 浏览器驱动"""
    
    def __init__(self, config: SeleniumConfig = None):
        self.config = config or SeleniumConfig()
        self.driver = None
        self._selenium = None
        self._webdriver = None
    
    async def initialize(self):
        """初始化 Selenium WebDriver"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service as ChromeService
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from selenium.webdriver.edge.options import Options as EdgeOptions
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            self._selenium = {
                "webdriver": webdriver,
                "ChromeService": ChromeService,
                "ChromeOptions": ChromeOptions,
                "FirefoxOptions": FirefoxOptions,
                "EdgeOptions": EdgeOptions,
                "By": By,
                "WebDriverWait": WebDriverWait,
                "EC": EC,
            }

            opts_class = {
                SeleniumBrowser.CHROME: self._selenium["ChromeOptions"],
                SeleniumBrowser.FIREFOX: self._selenium["FirefoxOptions"],
                SeleniumBrowser.EDGE: self._selenium["EdgeOptions"],
            }[self.config.browser]

            options = opts_class()
            options.headless = self.config.headless
            options.add_argument(f"--window-size={self.config.window_size[0]},{self.config.window_size[1]}")
            if self.config.user_agent:
                options.add_argument(f"user-agent={self.config.user_agent}")

            wdriver_class = getattr(self._selenium["webdriver"], self.config.browser.value).__class__.__bases__[0]
            if self.config.browser == SeleniumBrowser.CHROME:
                self.driver = self._selenium["webdriver"].Chrome(options=options)
            elif self.config.browser == SeleniumBrowser.FIREFOX:
                self.driver = self._selenium["webdriver"].Firefox(options=options)
            elif self.config.browser == SeleniumBrowser.EDGE:
                self.driver = self._selenium["webdriver"].Edge(options=options)

            self.driver.implicitly_wait(self.config.implicit_wait)
            self.driver.set_page_load_timeout(self.config.page_load_timeout)
            logger.info(f"SeleniumDriver initialized: {self.config.browser.value}")
        except ImportError as e:
            logger.error(f"Selenium not installed: {e}")
            raise

    async def goto(self, url: str):
        self.driver.get(url)

    async def screenshot(self, path: str = None) -> bytes:
        if path:
            self.driver.save_screenshot(path)
            return b""
        else:
            from selenium.common.exceptions import WebDriverException
            try:
                return self.driver.get_screenshot_as_png()
            except WebDriverException:
                return b""

    async def find_element(self, by: str, value: str):
        by_map = {
            "id": self._selenium["By"].ID,
            "css": self._selenium["By"].CSS_SELECTOR,
            "xpath": self._selenium["By"].XPATH,
            "text": self._selenium["By"].LINK_TEXT,
            "partial_text": self._selenium["By"].PARTIAL_LINK_TEXT,
            "name": self._selenium["By"].NAME,
            "class": self._selenium["By"].CLASS_NAME,
            "tag": self._selenium["By"].TAG_NAME,
        }
        return self.driver.find_element(by_map.get(by, self._selenium["By"].CSS_SELECTOR), value)

    async def find_elements(self, by: str, value: str) -> List:
        by_map = {
            "id": self._selenium["By"].ID,
            "css": self._selenium["By"].CSS_SELECTOR,
            "xpath": self._selenium["By"].XPATH,
            "name": self._selenium["By"].NAME,
            "class": self._selenium["By"].CLASS_NAME,
            "tag": self._selenium["By"].TAG_NAME,
        }
        return self.driver.find_elements(by_map.get(by, self._selenium["By"].CSS_SELECTOR), value)

    async def click(self, by: str, value: str):
        el = await self.find_element(by, value)
        el.click()

    async def fill(self, by: str, value: str, text: str):
        el = await self.find_element(by, value)
        el.clear()
        el.send_keys(text)

    async def submit(self, by: str, value: str):
        el = await self.find_element(by, value)
        el.submit()

    async def get_text(self, by: str, value: str) -> str:
        el = await self.find_element(by, value)
        return el.text

    async def get_attribute(self, by: str, value: str, attr: str) -> str:
        el = await self.find_element(by, value)
        return el.get_attribute(attr)

    async def is_visible(self, by: str, value: str) -> bool:
        try:
            el = await self.find_element(by, value)
            return el.is_displayed()
        except Exception:
            return False

    async def execute_script(self, script: str):
        return self.driver.execute_script(script)

    async def wait_for_element(self, by: str, value: str, timeout: int = 10):
        by_map = {
            "id": self._selenium["By"].ID,
            "css": self._selenium["By"].CSS_SELECTOR,
            "xpath": self._selenium["By"].XPATH,
            "name": self._selenium["By"].NAME,
        }
        wait = self._selenium["WebDriverWait"](self.driver, timeout)
        wait.until(self._selenium["EC"].presence_of_element_located(
            (by_map.get(by, self._selenium["By"].CSS_SELECTOR), value)
        ))

    async def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, *args):
        await self.close()


class SeleniumPool:
    """Selenium 浏览器池"""
    
    def __init__(self, max_browsers: int = 3):
        self.max_browsers = max_browsers
        self.drivers: List[SeleniumDriver] = []
        self.available: asyncio.Queue = asyncio.Queue()
    
    async def start(self):
        for _ in range(min(2, self.max_browsers)):
            driver = SeleniumDriver()
            try:
                await driver.initialize()
                self.drivers.append(driver)
                await self.available.put(driver)
            except Exception as e:
                logger.warning(f"Failed to start Selenium driver: {e}")

    async def stop(self):
        for driver in self.drivers:
            try:
                await driver.close()
            except Exception:
                pass

    async def acquire(self, config: SeleniumConfig = None) -> SeleniumDriver:
        try:
            driver = self.available.get_nowait()
        except asyncio.QueueEmpty:
            driver = SeleniumDriver(config)
            await driver.initialize()
            self.drivers.append(driver)
        return driver

    async def release(self, driver: SeleniumDriver):
        try:
            self.available.put_nowait(driver)
        except Exception:
            await driver.close()


_selenium_pool: Optional[SeleniumPool] = None


async def get_selenium_pool() -> SeleniumPool:
    global _selenium_pool
    if _selenium_pool is None:
        _selenium_pool = SeleniumPool()
        await _selenium_pool.start()
    return _selenium_pool
