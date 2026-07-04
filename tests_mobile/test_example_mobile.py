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
        # Simple uiautomator2 smoke check: device info is available
        info = self.mobile.info
        self.assertIn("screenOn", info)
