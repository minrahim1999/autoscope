"""Regression tests for ScriptBuilder: empty recordings must still be valid Python."""

import tempfile
import unittest
from pathlib import Path

from autoscope.desktop.recorder.script_builder import ScriptBuilder


class TestScriptBuilderEmptyRecordings(unittest.TestCase):
    """A recording with zero captured actions used to generate a script with an
    empty `try:` block, which is a SyntaxError. This is exactly what happened
    when mobile taps were silently dropped (see scripts/*_mobile.py history)."""

    def test_empty_mobile_script_compiles(self) -> None:
        builder = ScriptBuilder(platform="mobile", name="empty")
        source = builder.build()
        self.assertIn("pass", source)
        compile(source, "<test>", "exec")

    def test_empty_web_script_compiles(self) -> None:
        builder = ScriptBuilder(platform="web", name="empty")
        source = builder.build()
        self.assertIn("pass", source)
        compile(source, "<test>", "exec")


class TestScriptBuilderMobileActions(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = ScriptBuilder(platform="mobile", name="flow")

    def test_records_tap_input_swipe_wait_screenshot(self) -> None:
        self.builder.add("tap", {"x": 100, "y": 200})
        self.builder.add("input", {"text": "hello"})
        self.builder.add("swipe", {"x1": 0, "y1": 0, "x2": 100, "y2": 100, "duration": 250})
        self.builder.add("wait", {"ms": 500})
        self.builder.add("screenshot", {"name": "shot.png"})

        source = self.builder.build()
        compile(source, "<test>", "exec")

        self.assertIn("device.click(100, 200)", source)
        self.assertIn("'text', 'hello'", source)
        self.assertIn("'swipe', '0', '0', '100', '100', '250'", source)
        self.assertIn("device.sleep(0.5)", source)
        self.assertIn("driver.screenshot('shot.png')", source)

    def test_no_actions_produces_no_platform_specific_calls(self) -> None:
        source = self.builder.build()
        self.assertNotIn("device.click", source)
        self.assertNotIn("driver.adb.run(['shell', 'input'", source)
        self.assertIn("        pass\n", source)


class TestScriptBuilderWebActions(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = ScriptBuilder(platform="web", name="flow", base_url="https://example.com")

    def test_records_goto_click_fill_wait_screenshot(self) -> None:
        self.builder.add("goto", {"url": "https://example.com/login"})
        self.builder.add("fill", {"selector": "#user", "value": "alice"})
        self.builder.add("click", {"selector": "button[type=submit]"})
        self.builder.add("wait", {"ms": 1500})
        self.builder.add("screenshot", {"name": "after_login.png"})

        source = self.builder.build()
        compile(source, "<test>", "exec")

        self.assertIn("page.goto('https://example.com/login')", source)
        self.assertIn("page.fill('#user', 'alice')", source)
        self.assertIn("page.click('button[type=submit]')", source)
        self.assertIn("page.wait_for_timeout(1500)", source)
        self.assertIn("driver.screenshot('after_login.png')", source)

    def test_click_without_selector_is_skipped(self) -> None:
        self.builder.add("click", {"selector": ""})
        source = self.builder.build()
        self.assertNotIn("page.click", source)


class TestScriptBuilderNameSanitization(unittest.TestCase):
    def test_special_characters_are_stripped(self) -> None:
        builder = ScriptBuilder(platform="web", name="My Test! @2026#")
        self.assertEqual(builder.name, "my_test_2026")

    def test_blank_name_falls_back_to_recording(self) -> None:
        builder = ScriptBuilder(platform="web", name="   ###   ")
        self.assertEqual(builder.name, "recording")

    def test_unsupported_platform_raises(self) -> None:
        builder = ScriptBuilder(platform="desktop", name="x")
        with self.assertRaises(ValueError):
            builder.build()


class TestScriptBuilderSave(unittest.TestCase):
    def test_repeated_saves_do_not_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            builder = ScriptBuilder(platform="mobile", name="dup")
            first = builder.save(directory)
            second = builder.save(directory)
            third = builder.save(directory)

            self.assertNotEqual(first, second)
            self.assertNotEqual(second, third)
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())
            self.assertTrue(third.exists())
            self.assertEqual(second.name, "dup_mobile_001.py")
            self.assertEqual(third.name, "dup_mobile_002.py")


if __name__ == "__main__":
    unittest.main()
