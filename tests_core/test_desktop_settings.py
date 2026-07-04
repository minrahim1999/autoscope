"""Tests for autoscope.desktop.settings (persisted desktop UI preferences)
and its wiring into paths.get_scripts_dir()/get_reports_dir().

Settings live in a small JSON file next to config.yaml in the app's writable
data directory (autoscope.desktop.paths.get_app_dir()), kept separate from
config.yaml itself so a rewrite here never clobbers config.yaml's comments.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from autoscope.desktop import paths, settings as desktop_settings


class TestSettingsRoundTrip(unittest.TestCase):
    def test_load_settings_returns_empty_dict_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("autoscope.desktop.paths.get_app_dir", return_value=Path(tmp)):
                self.assertEqual(desktop_settings.load_settings(), {})

    def test_scripts_dir_override_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("autoscope.desktop.paths.get_app_dir", return_value=Path(tmp)):
                self.assertIsNone(desktop_settings.get_scripts_dir_override())
                desktop_settings.set_scripts_dir_override("/custom/scripts")
                self.assertEqual(desktop_settings.get_scripts_dir_override(), "/custom/scripts")

    def test_reports_dir_override_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("autoscope.desktop.paths.get_app_dir", return_value=Path(tmp)):
                self.assertIsNone(desktop_settings.get_reports_dir_override())
                desktop_settings.set_reports_dir_override("/custom/reports")
                self.assertEqual(desktop_settings.get_reports_dir_override(), "/custom/reports")

    def test_setting_one_override_does_not_clobber_the_other(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("autoscope.desktop.paths.get_app_dir", return_value=Path(tmp)):
                desktop_settings.set_scripts_dir_override("/custom/scripts")
                desktop_settings.set_reports_dir_override("/custom/reports")
                self.assertEqual(desktop_settings.get_scripts_dir_override(), "/custom/scripts")
                self.assertEqual(desktop_settings.get_reports_dir_override(), "/custom/reports")

    def test_resetting_override_to_none_clears_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("autoscope.desktop.paths.get_app_dir", return_value=Path(tmp)):
                desktop_settings.set_scripts_dir_override("/custom/scripts")
                desktop_settings.set_scripts_dir_override(None)
                self.assertIsNone(desktop_settings.get_scripts_dir_override())

    def test_settings_persist_to_disk_across_fresh_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("autoscope.desktop.paths.get_app_dir", return_value=Path(tmp)):
                desktop_settings.set_reports_dir_override("/custom/reports")
                # A fresh load_settings() call re-reads the file from disk rather
                # than any in-memory cache.
                self.assertEqual(desktop_settings.load_settings(), {"reports_dir": "/custom/reports"})

    def test_corrupt_settings_file_is_treated_as_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "desktop_settings.json").write_text("not json", encoding="utf-8")
            with mock.patch("autoscope.desktop.paths.get_app_dir", return_value=Path(tmp)):
                self.assertEqual(desktop_settings.load_settings(), {})


class TestPathsRespectOverrides(unittest.TestCase):
    def test_get_scripts_dir_uses_default_when_no_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("autoscope.desktop.paths.get_app_dir", return_value=Path(tmp)):
                result = paths.get_scripts_dir()
                self.assertEqual(result, Path(tmp) / "scripts")
                self.assertTrue(result.exists())

    def test_get_scripts_dir_uses_override_when_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as custom:
            custom_scripts = Path(custom) / "my_scripts"
            with mock.patch("autoscope.desktop.paths.get_app_dir", return_value=Path(tmp)):
                desktop_settings.set_scripts_dir_override(str(custom_scripts))
                result = paths.get_scripts_dir()
                self.assertEqual(result, custom_scripts)
                self.assertTrue(result.exists())

    def test_get_reports_dir_uses_default_when_no_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("autoscope.desktop.paths.get_app_dir", return_value=Path(tmp)):
                result = paths.get_reports_dir()
                self.assertEqual(result, Path(tmp) / "var" / "reports")
                self.assertTrue(result.exists())

    def test_get_reports_dir_uses_override_when_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as custom:
            custom_reports = Path(custom) / "my_reports"
            with mock.patch("autoscope.desktop.paths.get_app_dir", return_value=Path(tmp)):
                desktop_settings.set_reports_dir_override(str(custom_reports))
                result = paths.get_reports_dir()
                self.assertEqual(result, custom_reports)
                self.assertTrue(result.exists())

    def test_resetting_override_reverts_to_default_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as custom:
            with mock.patch("autoscope.desktop.paths.get_app_dir", return_value=Path(tmp)):
                desktop_settings.set_scripts_dir_override(str(Path(custom) / "elsewhere"))
                desktop_settings.set_scripts_dir_override(None)
                result = paths.get_scripts_dir()
                self.assertEqual(result, Path(tmp) / "scripts")


if __name__ == "__main__":
    unittest.main()
