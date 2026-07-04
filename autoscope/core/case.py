"""Base test case that optionally provisions web/Android/iOS drivers."""

import unittest
from pathlib import Path

from autoscope.config.loader import Config, load_config
from autoscope.drivers.android import AndroidDriver
from autoscope.drivers.ios import IOSDriver
from autoscope.drivers.web import WebDriver


class AutomateTestCase(unittest.TestCase):
    """
    Inherit from this class to get managed web/Android/iOS drivers.

    Class attributes:
        tags: tuple of strings, e.g. ("web",) or ("android",) or ("web", "android", "ios")
        needs_web: bool
        needs_android: bool
        needs_ios: bool
    """

    tags = ()

    @classmethod
    def setUpClass(cls) -> None:
        cls.config: Config = load_config()
        cls._web_driver: WebDriver | None = None
        cls._android_driver: AndroidDriver | None = None
        cls._ios_driver: IOSDriver | None = None

        if getattr(cls, "needs_web", False) or "web" in cls.tags:
            cls._web_driver = WebDriver(cls.config.web)
            cls.web = cls._web_driver.start()

        if getattr(cls, "needs_android", False) or "android" in cls.tags:
            cls._android_driver = AndroidDriver(cls.config.android)
            cls.android = cls._android_driver.start()

        if getattr(cls, "needs_ios", False) or "ios" in cls.tags:
            cls._ios_driver = IOSDriver(cls.config.ios)
            cls.ios = cls._ios_driver.start()

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._web_driver:
            cls._web_driver.stop()
            cls._web_driver = None
        if cls._android_driver:
            cls._android_driver.stop()
            cls._android_driver = None
        if cls._ios_driver:
            cls._ios_driver.stop()
            cls._ios_driver = None

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
        if self._android_driver and self.config.android.screenshot_on_failure:
            try:
                self._android_driver.screenshot(f"android_{test_name}.png")
            except Exception:
                pass
        if self._ios_driver and self.config.ios.screenshot_on_failure:
            try:
                self._ios_driver.screenshot(f"ios_{test_name}.png")
            except Exception:
                pass

    def web_screenshot(self, name: str) -> Path:
        """Take a web screenshot inside a test."""
        if not self._web_driver:
            raise RuntimeError("Web driver not enabled for this test.")
        return self._web_driver.screenshot(name)

    def android_screenshot(self, name: str) -> Path:
        """Take an Android screenshot inside a test."""
        if not self._android_driver:
            raise RuntimeError("Android driver not enabled for this test.")
        return self._android_driver.screenshot(name)

    def ios_screenshot(self, name: str) -> Path:
        """Take an iOS screenshot inside a test."""
        if not self._ios_driver:
            raise RuntimeError("iOS driver not enabled for this test.")
        return self._ios_driver.screenshot(name)
