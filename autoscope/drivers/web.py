"""Playwright-based web driver."""

from pathlib import Path
from typing import Optional

from playwright.sync_api import Page, Playwright, sync_playwright

from autoscope.config.loader import WebConfig


class WebDriver:
    def __init__(self, config: WebConfig) -> None:
        self.config = config
        self._playwright: Optional[Playwright] = None
        self._browser = None
        self._page: Optional[Page] = None

    def start(self) -> Page:
        self._playwright = sync_playwright().start()
        browser_type = getattr(self._playwright, self.config.browser, None)
        if not browser_type:
            raise ValueError(f"Unknown browser: {self.config.browser}")
        self._browser = browser_type.launch(headless=self.config.headless)
        context = self._browser.new_context(
            viewport=self.config.viewport,
        )
        self._page = context.new_page()
        self._page.set_default_timeout(self.config.timeout_ms)
        return self._page

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Web driver not started. Call start() first.")
        return self._page

    def screenshot(self, name: str) -> Path:
        path = Path(self.config.screenshot_dir) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(path))
        return path

    def stop(self) -> None:
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        self._page = None

    def goto(self, url: str) -> Page:
        self.page.goto(url)
        return self.page
