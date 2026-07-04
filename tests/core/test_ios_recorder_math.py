"""Regression tests for IOSRecorder's display-to-point coordinate mapping.

These exercise the pure math in isolation (no WebDriverAgent/Simulator
required) by constructing an IOSRecorder without calling start(), then
manually priming the bits start() would normally set: _point_size, _builder,
and _recording. _session stays None, so tap()/swipe()/input_text() record
the action but skip the real wda call (guarded by `if self._session:`).

Unlike Android (where screenshot pixels == input pixels), wda's tap()/
swipe() expect *points* (window_size()), not screenshot pixels -- hence
"point_size" rather than "screen_size" here.
"""

import unittest
from pathlib import Path
from unittest import mock

from autoscope.config.loader import load_config
from autoscope.desktop.recorder.ios_recorder import IOSRecorder
from autoscope.desktop.recorder.script_builder import ScriptBuilder


def _make_recorder(point_size=(402.0, 874.0)) -> IOSRecorder:
    recorder = IOSRecorder(load_config("does-not-exist.yaml"))
    recorder._point_size = point_size
    recorder._builder = ScriptBuilder(platform="ios", name="test")
    recorder._recording = True
    return recorder


class TestTapCoordinateMapping(unittest.TestCase):
    def test_tap_scales_from_container_to_point_space(self) -> None:
        recorder = _make_recorder(point_size=(402.0, 874.0))
        recorder.tap(180, 320, 360, 640)  # center-ish point in a 360x640 container
        self.assertEqual(len(recorder._actions), 1)
        action = recorder._actions[0]
        self.assertEqual(action.action, "tap")
        self.assertEqual(action.data, {"x": 201, "y": 437})

    def test_tap_top_left_corner_maps_to_origin(self) -> None:
        recorder = _make_recorder(point_size=(402.0, 874.0))
        recorder.tap(0, 0, 360, 640)
        self.assertEqual(recorder._actions[0].data, {"x": 0, "y": 0})

    def test_tap_is_noop_when_point_size_unknown(self) -> None:
        recorder = _make_recorder(point_size=(0.0, 0.0))
        recorder.tap(100, 100, 360, 640)
        self.assertEqual(len(recorder._actions), 0)

    def test_tap_not_recorded_when_not_recording(self) -> None:
        recorder = _make_recorder()
        recorder._recording = False
        recorder.tap(100, 100, 360, 640)
        self.assertEqual(len(recorder._actions), 0)

    def test_tap_calls_session_with_point_coordinates(self) -> None:
        recorder = _make_recorder(point_size=(402.0, 874.0))
        fake_session = mock.Mock()
        recorder._session = fake_session
        recorder.tap(180, 320, 360, 640)
        fake_session.tap.assert_called_once_with(201, 437)


class TestSwipeCoordinateMapping(unittest.TestCase):
    def test_swipe_scales_both_endpoints(self) -> None:
        recorder = _make_recorder(point_size=(402.0, 874.0))
        recorder.swipe(0, 640, 360, 0, 360, 640, duration_ms=250)
        action = recorder._actions[0]
        self.assertEqual(action.action, "swipe")
        self.assertEqual(
            action.data,
            {"x1": 0, "y1": 874, "x2": 402, "y2": 0, "duration": 250},
        )

    def test_swipe_is_noop_when_point_size_unknown(self) -> None:
        recorder = _make_recorder(point_size=(0.0, 0.0))
        recorder.swipe(0, 0, 100, 100, 360, 640)
        self.assertEqual(len(recorder._actions), 0)

    def test_swipe_calls_session_with_seconds_not_milliseconds(self) -> None:
        recorder = _make_recorder(point_size=(402.0, 874.0))
        fake_session = mock.Mock()
        recorder._session = fake_session
        recorder.swipe(0, 640, 360, 0, 360, 640, duration_ms=250)
        fake_session.swipe.assert_called_once_with(0, 874, 402, 0, 0.25)


class TestInputTextRecording(unittest.TestCase):
    def test_input_text_is_recorded_without_a_session(self) -> None:
        recorder = _make_recorder()
        recorder.input_text("hello world")
        self.assertEqual(recorder._actions[0].data, {"text": "hello world"})

    def test_input_text_calls_send_keys(self) -> None:
        recorder = _make_recorder()
        fake_session = mock.Mock()
        recorder._session = fake_session
        recorder.input_text("hello world")
        fake_session.send_keys.assert_called_once_with("hello world")

    def test_stop_saves_script_with_recorded_actions(self) -> None:
        import tempfile

        recorder = _make_recorder()
        recorder.tap(180, 320, 360, 640)
        with tempfile.TemporaryDirectory() as tmp:
            path = recorder._builder.save(Path(tmp))
            source = path.read_text(encoding="utf-8")
            compile(source, "<test>", "exec")
            self.assertIn("session.tap(201, 437)", source)


class TestVideoRecordingWiring(unittest.TestCase):
    """stop() must gracefully SIGINT the simctl recording process before
    tearing down the driver, and must not blow up when no video was started."""

    def test_start_launches_simctl_recordvideo_when_simulator_found(self) -> None:
        recorder = _make_recorder()
        recorder._builder = ScriptBuilder(platform="ios", name="vid")
        with mock.patch(
            "autoscope.desktop.recorder.ios_recorder._find_booted_simulator_udid",
            return_value="ABCD-1234",
        ), mock.patch("autoscope.desktop.recorder.ios_recorder.IOSDriver") as driver_cls, mock.patch(
            "autoscope.desktop.recorder.ios_recorder.subprocess.Popen"
        ) as popen, mock.patch(
            "autoscope.desktop.recorder.ios_recorder.threading.Thread"
        ):
            fake_driver = driver_cls.return_value
            fake_session = mock.Mock()
            fake_session.window_size.return_value = mock.Mock(width=402, height=874)
            fake_driver.start.return_value = fake_session

            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                recorder.config.ios.video_dir = tmp
                recorder.start("vid", record_video=True)

            args = popen.call_args[0][0]
        self.assertEqual(args[:4], ["xcrun", "simctl", "io", "ABCD-1234"])
        self.assertEqual(args[4], "recordVideo")

    def test_start_skips_video_when_no_simulator_found(self) -> None:
        recorder = _make_recorder()
        with mock.patch(
            "autoscope.desktop.recorder.ios_recorder._find_booted_simulator_udid",
            return_value=None,
        ), mock.patch("autoscope.desktop.recorder.ios_recorder.IOSDriver") as driver_cls, mock.patch(
            "autoscope.desktop.recorder.ios_recorder.subprocess.Popen"
        ) as popen, mock.patch(
            "autoscope.desktop.recorder.ios_recorder.threading.Thread"
        ):
            fake_driver = driver_cls.return_value
            fake_session = mock.Mock()
            fake_session.window_size.return_value = mock.Mock(width=402, height=874)
            fake_driver.start.return_value = fake_session
            recorder.start("vid", record_video=True)
        popen.assert_not_called()
        self.assertIsNone(recorder._video_process)

    def test_stop_sends_sigint_and_captures_video_path(self) -> None:
        recorder = _make_recorder()
        recorder._builder = None
        fake_process = mock.Mock()
        recorder._video_process = fake_process
        recorder._video_local_path = Path("/tmp/fake_ios_video.mov")

        recorder.stop()

        fake_process.send_signal.assert_called_once()
        self.assertEqual(recorder.video_path, Path("/tmp/fake_ios_video.mov"))
        self.assertIsNone(recorder._video_process)

    def test_stop_leaves_video_path_none_when_video_not_requested(self) -> None:
        recorder = _make_recorder()
        recorder._builder = None
        recorder.stop()
        self.assertIsNone(recorder.video_path)

    def test_stop_swallows_video_signal_failure(self) -> None:
        recorder = _make_recorder()
        recorder._builder = None
        fake_process = mock.Mock()
        fake_process.send_signal.side_effect = RuntimeError("process gone")
        recorder._video_process = fake_process

        recorder.stop()  # must not raise

        self.assertIsNone(recorder.video_path)


if __name__ == "__main__":
    unittest.main()
