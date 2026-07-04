"""Regression test for WebRecorder's Playwright thread-affinity bug.

Playwright's sync API requires every call on a browser/page to run on the
exact OS thread that created it, or it raises "cannot switch to a different
thread (which happens to have exited)". In the desktop UI, start() runs
inside one throwaway background thread (which exits right after returning)
and stop()/take_screenshot() are triggered later from other threads (Flet
button click handlers, separate "stop" worker threads) -- this test
reproduces that exact shape with a real (headless) browser to guard against
a regression.
"""

import tempfile
import threading
import unittest
from pathlib import Path
from typing import Optional

from autoscope.config.loader import load_config
from autoscope.desktop.recorder.web_recorder import WebRecorder


def _run_in_new_thread(fn, errors: list, results: Optional[list] = None) -> None:
    def target() -> None:
        try:
            result = fn()
            if results is not None:
                results.append(result)
        except BaseException as e:  # noqa: BLE001 - captured for the assertion below
            errors.append(e)

    t = threading.Thread(target=target)
    t.start()
    t.join(timeout=30)


class TestWebRecorderCrossThreadSafety(unittest.TestCase):
    def test_start_screenshot_stop_from_three_different_threads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config("does-not-exist.yaml")
            config.web.screenshot_dir = str(Path(tmp) / "screenshots")
            config.web.video_dir = str(Path(tmp) / "videos")
            recorder = WebRecorder(config)
            errors: list = []
            stop_results: list = []

            # Each call below runs in its own brand-new thread, mirroring how
            # the desktop UI actually drives WebRecorder: a "launch" thread
            # for start() that exits immediately after, a button-click
            # handler thread for take_screenshot(), and a separate "stop"
            # worker thread later.
            _run_in_new_thread(
                lambda: recorder.start("about:blank", "thread_test", headless=True), errors
            )
            _run_in_new_thread(lambda: recorder.take_screenshot("thread_test_shot.png"), errors)
            _run_in_new_thread(recorder.stop, errors, stop_results)

            # stop() saves the generated script under the real scripts/ dir
            # (ScriptBuilder.save()'s default); clean it up so running this
            # test doesn't leave stray files in the repo.
            if stop_results and stop_results[0]:
                self.addCleanup(lambda p=stop_results[0]: p.unlink(missing_ok=True))

            self.assertEqual(errors, [], f"cross-thread Playwright calls raised: {errors!r}")
            self.assertTrue((Path(tmp) / "screenshots" / "thread_test_shot.png").exists())

    def test_take_screenshot_and_stop_are_noop_safe_before_start(self) -> None:
        recorder = WebRecorder(load_config("does-not-exist.yaml"))
        recorder.take_screenshot("never_started.png")  # must not raise
        self.assertIsNone(recorder.stop())


if __name__ == "__main__":
    unittest.main()
