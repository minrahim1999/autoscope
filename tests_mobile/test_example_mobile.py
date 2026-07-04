"""Sample Android test using ADB/uiautomator2."""

from autoscope import AutomateTestCase


class TestExampleMobile(AutomateTestCase):
    tags = ("mobile",)

    def test_device_is_connected(self) -> None:
        serial = self.mobile.serial
        self.assertTrue(serial)
        # Check the device is responsive via adb shell
        output = self.mobile.shell("getprop ro.product.model")
        self.assertTrue(output)
        self.mobile_screenshot("device_connected.png")

    def test_home_screen_exists(self) -> None:
        # Avoid uiautomator2's DeviceInfo on API 37+ preview emulators,
        # which can throw ApplicationSharedMemory errors. Use a screenshot
        # and a shell-based screen-on check instead.
        output = self.mobile.shell("dumpsys power | grep 'mWakefulness='")
        self.assertIn("Awake", str(output))
        self.mobile_screenshot("home_screen.png")
