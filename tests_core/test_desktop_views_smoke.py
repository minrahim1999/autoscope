"""Headless smoke tests that build every desktop view without a live GUI.

This is exactly the class of check that would have caught the original bug
report ("Android screen doesn't show"): Flet API drift such as
ft.Colors.SUCCESS not existing, ft.Image.src_base64 not existing, or
TapEvent.local_x not existing all raise plain AttributeError/TypeError the
instant the view function runs, across all six desktop views (Home, Web
Manual, Android Manual, iOS Manual, Auto Run, Reports) — no display, browser,
Android device, or WebDriverAgent required to catch them. Runs on every
`autoscope run`, unlike a manual click through the GUI.
"""

import unittest

from autoscope.config.loader import load_config
from autoscope.desktop.runner.script_runner import ScriptRunner
from autoscope.desktop.views.android_manual import AndroidManualViewMixin
from autoscope.desktop.views.auto_run import AutoRunViewMixin
from autoscope.desktop.views.home import HomeViewMixin
from autoscope.desktop.views.ios_manual import IOSManualViewMixin
from autoscope.desktop.views.reports import ReportsViewMixin
from autoscope.desktop.views.web_manual import WebManualViewMixin


class _FakePage:
    """Stand-in for flet.Page: enough surface for view builders to run against."""

    def __init__(self) -> None:
        self.overlay = []

    def update(self, *args, **kwargs) -> None:
        pass

    def run_task(self, handler, *args, **kwargs):
        # Real Flet requires `handler` to be an async coroutine function and
        # schedules it on the page's event loop; here we just verify the
        # contract callers must honor, since violating it is exactly what
        # broke the Android screen originally.
        import inspect

        if not inspect.iscoroutinefunction(handler):
            raise TypeError("handler must be a coroutine function")
        return None


class _FakeContentArea:
    def __init__(self) -> None:
        self.content = None


class _FakeApp(
    HomeViewMixin,
    WebManualViewMixin,
    AndroidManualViewMixin,
    IOSManualViewMixin,
    AutoRunViewMixin,
    ReportsViewMixin,
):
    def __init__(self) -> None:
        self.page = _FakePage()
        self.config = load_config("does-not-exist.yaml")
        self.content_area = _FakeContentArea()
        self._android_recorder = None
        self._web_recorder = None
        self._ios_recorder = None
        self._script_runner = ScriptRunner(self.config)
        self._selected_index = 0


class TestDesktopViewsBuildHeadlessly(unittest.TestCase):
    def setUp(self) -> None:
        self.app = _FakeApp()

    def test_home_view_builds(self) -> None:
        self.app._show_home()
        self.assertIsNotNone(self.app.content_area.content)

    def test_web_manual_view_builds(self) -> None:
        self.app._show_web_manual()
        self.assertIsNotNone(self.app.content_area.content)

    def test_android_manual_view_builds(self) -> None:
        self.app._show_android_manual()
        self.assertIsNotNone(self.app.content_area.content)

    def test_ios_manual_view_builds(self) -> None:
        self.app._show_ios_manual()
        self.assertIsNotNone(self.app.content_area.content)

    def test_auto_run_view_builds(self) -> None:
        self.app._show_auto_run()
        self.assertIsNotNone(self.app.content_area.content)

    def test_reports_view_builds(self) -> None:
        self.app._show_reports()
        self.assertIsNotNone(self.app.content_area.content)


if __name__ == "__main__":
    unittest.main()
