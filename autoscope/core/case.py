"""Base test case that optionally provisions web/mobile drivers."""

import unittest
from pathlib import Path

from autoscope.config.loader import Config, load_config
from autoscope.drivers.mobile import MobileDriver
from autoscope.drivers.web import WebDriver


class AutomateTestCase(unittest.TestCase):
    """
    Inherit from this class to get managed web and/or mobile drivers.

    Class attributes:
        tags: tuple of strings, e.g. ("web",) or ("mobile",) or ("web", "mobile")
        needs_web: bool
        needs_mobile: bool
    """

    tags = ()

    @classmethod
    def setUpClass(cls) -> None:
        cls.config: Config = load_config()
        cls._web_driver: WebDriver | None = None
        cls._mobile_driver: MobileDriver | None = None

        if getattr(cls, "needs_web", False) or "web" in cls.tags:
            cls._web_driver = WebDriver(cls.config.web)
            cls.web = cls._web_driver.start()

        if getattr(cls, "needs_mobile", False) or "mobile" in cls.tags:
            cls._mobile_driver = MobileDriver(cls.config.mobile)
            cls.mobile = cls._mobile_driver.start()

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._web_driver:
            cls._web_driver.stop()
            cls._web_driver = None
        if cls._mobile_driver:
            cls._mobile_driver.stop()
            cls._mobile_driver = None

    def run(self, result=None):
        """Hook to capture screenshots on failure."""
        test_result = super().run(result)
        if not getattr(test_result, "wasSuccessful", lambda: True)():
            self._capture_failure_screenshot()
        return test_result

    def _capture_failure_screenshot(self) -> None:
        test_name = self.id().split(".")[-1]
        if self._web_driver and self.config.web.screenshot_on_failure:
            try:
                self._web_driver.screenshot(f"web_{test_name}.png")
            except Exception:
                pass
        if self._mobile_driver and self.config.mobile.screenshot_on_failure:
            try:
                self._mobile_driver.screenshot(f"mobile_{test_name}.png")
            except Exception:
                pass

    def web_screenshot(self, name: str) -> Path:
        """Take a web screenshot inside a test."""
        if not self._web_driver:
            raise RuntimeError("Web driver not enabled for this test.")
        return self._web_driver.screenshot(name)

    def mobile_screenshot(self, name: str) -> Path:
        """Take a mobile screenshot inside a test."""
        if not self._mobile_driver:
            raise RuntimeError("Mobile driver not enabled for this test.")
        return self._mobile_driver.screenshot(name)
