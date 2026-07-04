"""Regression tests for AndroidRecorder's display-to-device coordinate mapping.

These exercise the pure math in isolation (no adb/device required) by
constructing an AndroidRecorder without calling start(), then manually
priming the bits start() would normally set: _screen_size, _builder, and
_recording. _driver stays None, so tap()/swipe()/input_text() record the
action but skip the real `adb shell input ...` call (guarded by
`if self._driver:`).
"""

import unittest
from pathlib import Path
from unittest import mock

from autoscope.config.loader import load_config
from autoscope.desktop.recorder.android_recorder import AndroidRecorder
from autoscope.desktop.recorder.script_builder import ScriptBuilder


def _make_recorder(screen_size=(1080, 1920)) -> AndroidRecorder:
    recorder = AndroidRecorder(load_config("does-not-exist.yaml"))
    recorder._screen_size = screen_size
    recorder._builder = ScriptBuilder(platform="android", name="test")
    recorder._recording = True
    return recorder


class TestTapCoordinateMapping(unittest.TestCase):
    def test_tap_scales_from_container_to_device_pixels(self) -> None:
        recorder = _make_recorder(screen_size=(1080, 1920))
        recorder.tap(180, 320, 360, 640)  # center-ish point in a 360x640 container
        self.assertEqual(len(recorder._actions), 1)
        action = recorder._actions[0]
        self.assertEqual(action.action, "tap")
        self.assertEqual(action.data, {"x": 540, "y": 960})

    def test_tap_top_left_corner_maps_to_origin(self) -> None:
        recorder = _make_recorder(screen_size=(1080, 1920))
        recorder.tap(0, 0, 360, 640)
        self.assertEqual(recorder._actions[0].data, {"x": 0, "y": 0})

    def test_tap_is_noop_when_screen_size_unknown(self) -> None:
        recorder = _make_recorder(screen_size=(0, 0))
        recorder.tap(100, 100, 360, 640)
        self.assertEqual(len(recorder._actions), 0)

    def test_tap_not_recorded_when_not_recording(self) -> None:
        recorder = _make_recorder()
        recorder._recording = False
        recorder.tap(100, 100, 360, 640)
        self.assertEqual(len(recorder._actions), 0)


class TestSwipeCoordinateMapping(unittest.TestCase):
    def test_swipe_scales_both_endpoints(self) -> None:
        recorder = _make_recorder(screen_size=(1080, 1920))
        recorder.swipe(0, 640, 360, 0, 360, 640, duration_ms=250)
        action = recorder._actions[0]
        self.assertEqual(action.action, "swipe")
        self.assertEqual(
            action.data,
            {"x1": 0, "y1": 1920, "x2": 1080, "y2": 0, "duration": 250},
        )

    def test_swipe_is_noop_when_screen_size_unknown(self) -> None:
        recorder = _make_recorder(screen_size=(0, 0))
        recorder.swipe(0, 0, 100, 100, 360, 640)
        self.assertEqual(len(recorder._actions), 0)


class TestInputTextRecording(unittest.TestCase):
    def test_input_text_is_recorded_without_a_driver(self) -> None:
        recorder = _make_recorder()
        recorder.input_text("hello world")
        self.assertEqual(recorder._actions[0].data, {"text": "hello world"})

    def test_stop_saves_script_with_recorded_actions(self) -> None:
        import tempfile

        recorder = _make_recorder()
        recorder.tap(180, 320, 360, 640)
        with tempfile.TemporaryDirectory() as tmp:
            path = recorder._builder.save(Path(tmp))
            source = path.read_text(encoding="utf-8")
            compile(source, "<test>", "exec")
            self.assertIn("device.click(540, 960)", source)


class TestVideoRecordingWiring(unittest.TestCase):
    """stop() must finalize/pull the video before tearing down the driver,
    and must not blow up when no video was ever started."""

    def test_stop_pulls_video_when_recording_was_active(self) -> None:
        recorder = _make_recorder()
        recorder._builder = None  # isolate this test from ScriptBuilder.save()'s filesystem writes
        fake_adb = mock.Mock()
        fake_adb.stop_screenrecord.return_value = Path("/tmp/fake_video.mp4")
        fake_driver = mock.Mock()
        fake_driver.adb = fake_adb
        recorder._driver = fake_driver
        recorder._video_process = mock.Mock()
        recorder._video_remote_path = "/sdcard/autoscope_record.mp4"

        recorder.stop()

        fake_adb.stop_screenrecord.assert_called_once()
        self.assertEqual(recorder.video_path, Path("/tmp/fake_video.mp4"))

    def test_stop_leaves_video_path_none_when_video_not_requested(self) -> None:
        recorder = _make_recorder()
        recorder._builder = None
        recorder.stop()
        self.assertIsNone(recorder.video_path)

    def test_stop_swallows_video_pull_failure(self) -> None:
        """A failed pull (device dropped mid-recording) must not prevent stop()
        from completing and tearing down the driver."""
        recorder = _make_recorder()
        recorder._builder = None
        fake_adb = mock.Mock()
        fake_adb.stop_screenrecord.side_effect = RuntimeError("device offline")
        fake_driver = mock.Mock()
        fake_driver.adb = fake_adb
        recorder._driver = fake_driver
        recorder._video_process = mock.Mock()
        recorder._video_remote_path = "/sdcard/autoscope_record.mp4"

        recorder.stop()  # must not raise

        self.assertIsNone(recorder.video_path)
        fake_driver.stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
