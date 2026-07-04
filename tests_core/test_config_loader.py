"""Regression tests for autoscope.config.loader.

Covers the var/reports/ default-path fix (dataclass defaults had drifted from
the checked-in config.yaml after the reports/ -> var/reports/ migration) plus
YAML and environment-variable override behavior.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from autoscope.config.loader import Config, load_config


class TestDefaults(unittest.TestCase):
    def test_defaults_use_var_reports_layout(self) -> None:
        """A missing/fresh config.yaml must not resurrect the old reports/ layout."""
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = str(Path(tmp) / "does_not_exist.yaml")
            config = load_config(missing_path)

        self.assertEqual(config.web.screenshot_dir, "var/reports/screenshots")
        self.assertEqual(config.mobile.screenshot_dir, "var/reports/screenshots")
        self.assertEqual(config.web.video_dir, "var/reports/videos")
        self.assertEqual(config.mobile.video_dir, "var/reports/videos")
        self.assertEqual(config.ios.screenshot_dir, "var/reports/screenshots")
        self.assertEqual(config.ios.video_dir, "var/reports/videos")
        self.assertEqual(config.ios.wda_url, "http://localhost:8100")
        self.assertIsNone(config.ios.bundle_id)
        self.assertEqual(config.runner.output_dir, "var/reports")
        self.assertEqual(config.runner.json_report, "var/reports/results.json")
        self.assertEqual(config.runner.html_report, "var/reports/report.html")

    def test_returns_config_dataclass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config(str(Path(tmp) / "missing.yaml"))
        self.assertIsInstance(config, Config)


class TestYamlOverrides(unittest.TestCase):
    def test_yaml_values_override_defaults(self) -> None:
        yaml_text = """
web:
  browser: firefox
  headless: true
  base_url: https://staging.example.com
mobile:
  device_serial: emulator-5554
runner:
  verbosity: 1
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yaml"
            path.write_text(yaml_text, encoding="utf-8")
            config = load_config(str(path))

        self.assertEqual(config.web.browser, "firefox")
        self.assertTrue(config.web.headless)
        self.assertEqual(config.web.base_url, "https://staging.example.com")
        self.assertEqual(config.mobile.device_serial, "emulator-5554")
        self.assertEqual(config.runner.verbosity, 1)


class TestEnvOverrides(unittest.TestCase):
    def _load_with_env(self, env: dict, yaml_text: str = "web:\n  browser: chromium\n") -> Config:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yaml"
            path.write_text(yaml_text, encoding="utf-8")
            with mock.patch.dict(os.environ, env, clear=False):
                return load_config(str(path))

    def test_bool_env_override(self) -> None:
        config = self._load_with_env({"AT_WEB_BROWSER": "firefox"})
        self.assertEqual(config.web.browser, "firefox")

    def test_true_false_strings_become_bool(self) -> None:
        yaml_text = "web:\n  browser: chromium\n  headless: false\n"
        config = self._load_with_env({"AT_WEB_HEADLESS": "true"}, yaml_text)
        self.assertIs(config.web.headless, True)

    def test_digit_strings_become_int(self) -> None:
        yaml_text = "runner:\n  verbosity: 2\n"
        config = self._load_with_env({"AT_RUNNER_VERBOSITY": "3"}, yaml_text)
        self.assertEqual(config.runner.verbosity, 3)
        self.assertIsInstance(config.runner.verbosity, int)

    def test_plain_string_stays_string(self) -> None:
        yaml_text = "mobile:\n  device_serial: null\n"
        config = self._load_with_env({"AT_MOBILE_DEVICE_SERIAL": "emulator-5554"}, yaml_text)
        self.assertEqual(config.mobile.device_serial, "emulator-5554")

    def test_ios_wda_url_env_override(self) -> None:
        yaml_text = "ios:\n  bundle_id: null\n"
        config = self._load_with_env({"AT_IOS_WDA_URL": "http://localhost:9100"}, yaml_text)
        self.assertEqual(config.ios.wda_url, "http://localhost:9100")

    def test_env_override_applies_even_when_key_absent_from_yaml(self) -> None:
        """Regression: _env_override used to only iterate keys already present
        in the loaded YAML dict, so AT_WEB_BROWSER was silently ignored unless
        config.yaml happened to already spell out `web.browser`."""
        yaml_text = "web:\n  base_url: https://example.com\n"
        config = self._load_with_env({"AT_WEB_BROWSER": "firefox"}, yaml_text)
        self.assertEqual(config.web.browser, "firefox")

    def test_env_override_applies_with_completely_empty_section(self) -> None:
        yaml_text = "web: {}\n"
        config = self._load_with_env({"AT_WEB_HEADLESS": "true"}, yaml_text)
        self.assertIs(config.web.headless, True)


if __name__ == "__main__":
    unittest.main()
