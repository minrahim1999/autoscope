"""Sample iOS test using WebDriverAgent (via the `wda` client).

Requires a WebDriverAgent instance already running and reachable at
config.ios.wda_url (default http://localhost:8100). For the Simulator, run
tools/start_ios_wda.sh once to build and launch it.
"""

from autoscope import AutomateTestCase


class TestExampleIOS(AutomateTestCase):
    tags = ("ios",)

    def test_device_is_connected(self) -> None:
        status = self.ios.status()
        self.assertTrue(status.get("ready"))
        # Prefixed to avoid colliding with tests/android's identically-named
        # screenshot in the shared var/reports/screenshots/ directory.
        self.ios_screenshot("ios_device_connected.png")

    def test_home_screen_exists(self) -> None:
        size = self.ios.window_size()
        self.assertGreater(size.width, 0)
        self.assertGreater(size.height, 0)
        self.ios_screenshot("ios_home_screen.png")
