"""Regression tests for IOSDriver.

wda.Client is mocked throughout -- these tests are independent of whether a
WebDriverAgent instance or Simulator is actually available, so they run
everywhere (including CI). tests_ios/ holds the real, WDA-required
integration test.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from autoscope.config.loader import IOSConfig
from autoscope.drivers.ios import IOSDriver, IOSDriverError


def _make_driver(**overrides) -> IOSDriver:
    config = IOSConfig(**overrides)
    return IOSDriver(config)


class TestIOSDriverStart(unittest.TestCase):
    def test_raises_clear_error_when_wda_unreachable(self) -> None:
        driver = _make_driver(wda_url="http://localhost:9999")
        with mock.patch("autoscope.drivers.ios.wda.Client") as client_cls:
            client_cls.return_value.status.side_effect = ConnectionError("refused")
            with self.assertRaises(IOSDriverError) as ctx:
                driver.start()
        self.assertIn("localhost:9999", str(ctx.exception))
        self.assertIn("start_ios_wda.sh", str(ctx.exception))

    def test_raises_when_wda_reports_not_ready(self) -> None:
        driver = _make_driver()
        with mock.patch("autoscope.drivers.ios.wda.Client") as client_cls:
            client_cls.return_value.status.return_value = {"ready": False}
            with self.assertRaises(IOSDriverError):
                driver.start()

    def test_session_created_without_bundle_id_when_unset(self) -> None:
        driver = _make_driver(bundle_id=None)
        with mock.patch("autoscope.drivers.ios.wda.Client") as client_cls:
            fake_client = client_cls.return_value
            fake_client.status.return_value = {"ready": True}
            driver.start()
        fake_client.session.assert_called_once_with()

    def test_session_created_with_bundle_id_when_set(self) -> None:
        driver = _make_driver(bundle_id="com.example.app")
        with mock.patch("autoscope.drivers.ios.wda.Client") as client_cls:
            fake_client = client_cls.return_value
            fake_client.status.return_value = {"ready": True}
            driver.start()
        fake_client.session.assert_called_once_with(bundle_id="com.example.app")


class TestIOSDriverSessionAccess(unittest.TestCase):
    def test_session_property_raises_before_start(self) -> None:
        driver = _make_driver()
        with self.assertRaises(RuntimeError):
            _ = driver.session

    def test_session_property_returns_session_after_start(self) -> None:
        driver = _make_driver()
        with mock.patch("autoscope.drivers.ios.wda.Client") as client_cls:
            fake_client = client_cls.return_value
            fake_client.status.return_value = {"ready": True}
            started = driver.start()
        self.assertIs(driver.session, started)


class TestIOSDriverScreenshot(unittest.TestCase):
    def test_screenshot_saves_to_configured_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            driver = _make_driver(screenshot_dir=str(Path(tmp) / "shots"))
            with mock.patch("autoscope.drivers.ios.wda.Client") as client_cls:
                fake_client = client_cls.return_value
                fake_client.status.return_value = {"ready": True}
                driver.start()
                path = driver.screenshot("test.png")

            self.assertEqual(path, Path(tmp) / "shots" / "test.png")
            fake_client.session.return_value.screenshot.assert_called_once()


class TestIOSDriverStop(unittest.TestCase):
    def test_stop_terminates_configured_bundle(self) -> None:
        driver = _make_driver(bundle_id="com.example.app")
        with mock.patch("autoscope.drivers.ios.wda.Client") as client_cls:
            fake_client = client_cls.return_value
            fake_client.status.return_value = {"ready": True}
            driver.start()
            driver.stop()
        fake_client.app_terminate.assert_called_once_with("com.example.app")
        with self.assertRaises(RuntimeError):
            _ = driver.session

    def test_stop_is_safe_without_bundle_id(self) -> None:
        driver = _make_driver(bundle_id=None)
        with mock.patch("autoscope.drivers.ios.wda.Client") as client_cls:
            fake_client = client_cls.return_value
            fake_client.status.return_value = {"ready": True}
            driver.start()
            driver.stop()  # must not raise
        fake_client.app_terminate.assert_not_called()

    def test_stop_is_safe_when_never_started(self) -> None:
        driver = _make_driver()
        driver.stop()  # must not raise

    def test_stop_swallows_app_terminate_failure(self) -> None:
        driver = _make_driver(bundle_id="com.example.app")
        with mock.patch("autoscope.drivers.ios.wda.Client") as client_cls:
            fake_client = client_cls.return_value
            fake_client.status.return_value = {"ready": True}
            fake_client.app_terminate.side_effect = RuntimeError("device gone")
            driver.start()
            driver.stop()  # must not raise


if __name__ == "__main__":
    unittest.main()
