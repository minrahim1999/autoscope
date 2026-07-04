"""Record manual iOS interactions by streaming the WebDriverAgent-connected screen.

Mirrors MobileRecorder's shape closely, with two iOS-specific differences:
  - Screenshots are in device pixels, but wda's tap()/swipe() expect points
    (window_size()), so display coordinates are scaled into point space
    instead of raw pixels.
  - Video is recorded via `xcrun simctl io <udid> recordVideo` (Simulator
    only) instead of adb's screenrecord, since there is no equivalent tool
    for real devices without extra setup.
"""

import base64
import io
import re
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import wda

from autoscope.config.loader import Config, load_config
from autoscope.desktop.recorder.script_builder import RecordedAction, ScriptBuilder
from autoscope.drivers.ios import IOSDriver


def _find_booted_simulator_udid() -> Optional[str]:
    """Best-effort lookup of the currently booted Simulator's UDID (for video recording)."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices"], capture_output=True, text=True, timeout=10
        )
        match = re.search(r"([0-9A-Fa-f-]{36})\s*\(Booted\)", result.stdout)
        return match.group(1) if match else None
    except Exception:
        return None


class IOSRecorder:
    """Stream an iOS screen to the desktop and record taps/swipes/text as a script."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or load_config()
        self._driver: Optional[IOSDriver] = None
        self._session: Optional[wda.Client] = None
        self._builder: Optional[ScriptBuilder] = None
        self._actions: List[RecordedAction] = []
        self._callback: Optional[Callable[[RecordedAction], None]] = None
        self._frame_callback: Optional[Callable[[str], None]] = None
        self._status_callback: Optional[Callable[[str], None]] = None
        self._recording = False
        self._streaming = False
        self._stream_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._point_size: Tuple[float, float] = (0.0, 0.0)
        self._video_process: Optional[subprocess.Popen] = None
        self._video_local_path: Optional[Path] = None
        self.video_path: Optional[Path] = None

    def set_callbacks(
        self,
        action_callback: Callable[[RecordedAction], None],
        frame_callback: Callable[[str], None],
    ) -> None:
        self._callback = action_callback
        self._frame_callback = frame_callback

    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Optional hook invoked when the stream health changes (e.g. WDA drops off)."""
        self._status_callback = callback

    def start(self, name: str = "ios_recording", record_video: bool = False) -> None:
        """Connect to WebDriverAgent and start streaming."""
        self._actions = []
        self._builder = ScriptBuilder(platform="ios", name=name)
        self._recording = True
        self._streaming = True
        self.video_path = None

        self._driver = IOSDriver(self.config.ios)
        self._session = self._driver.start()

        try:
            size = self._session.window_size()
            self._point_size = (float(size.width), float(size.height))
        except Exception:
            self._point_size = (0.0, 0.0)

        if record_video:
            udid = _find_booted_simulator_udid()
            if udid:
                self._video_local_path = Path(self.config.ios.video_dir) / f"{name}_ios.mov"
                self._video_local_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    self._video_process = subprocess.Popen(
                        ["xcrun", "simctl", "io", udid, "recordVideo", str(self._video_local_path)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    self._video_process = None

        self._stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._stream_thread.start()

    def _stream_loop(self) -> None:
        """Continuously capture and encode screenshots for the UI."""
        consecutive_failures = 0
        disconnected = False
        failure_threshold = 15  # ~3s at the 0.2s loop interval below

        while self._streaming:
            try:
                if not self._session:
                    time.sleep(0.5)
                    continue
                img = self._session.screenshot()
                if img is None:
                    raise RuntimeError("empty screenshot from device")
                img.thumbnail((480, 854))
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                if self._frame_callback:
                    self._frame_callback(f"data:image/png;base64,{b64}")
                if disconnected and self._status_callback:
                    self._status_callback("Streaming...")
                consecutive_failures = 0
                disconnected = False
            except Exception:
                consecutive_failures += 1
                if consecutive_failures == failure_threshold and not disconnected:
                    disconnected = True
                    if self._status_callback:
                        self._status_callback(
                            "Device not responding — check WebDriverAgent is still running"
                        )
            time.sleep(0.2)

    def tap(self, display_x: float, display_y: float, display_width: int, display_height: int) -> None:
        """Map tap coordinates from the on-screen image to WDA point space."""
        if self._point_size[0] == 0 or self._point_size[1] == 0:
            return
        point_x = round(display_x / display_width * self._point_size[0])
        point_y = round(display_y / display_height * self._point_size[1])
        self._record("tap", {"x": point_x, "y": point_y})
        if self._session:
            try:
                self._session.tap(point_x, point_y)
            except Exception:
                pass

    def swipe(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        display_width: int,
        display_height: int,
        duration_ms: int = 300,
    ) -> None:
        if self._point_size[0] == 0 or self._point_size[1] == 0:
            return
        px1 = round(x1 / display_width * self._point_size[0])
        py1 = round(y1 / display_height * self._point_size[1])
        px2 = round(x2 / display_width * self._point_size[0])
        py2 = round(y2 / display_height * self._point_size[1])
        self._record("swipe", {"x1": px1, "y1": py1, "x2": px2, "y2": py2, "duration": duration_ms})
        if self._session:
            try:
                self._session.swipe(px1, py1, px2, py2, duration_ms / 1000.0)
            except Exception:
                pass

    def input_text(self, text: str) -> None:
        """Send text to whatever's focused on the device and record it."""
        self._record("input", {"text": text})
        if self._session:
            try:
                self._session.send_keys(text)
            except Exception:
                pass

    def _record(self, action: str, data: dict) -> None:
        with self._lock:
            if not self._recording:
                return
            recorded = RecordedAction(action=action, platform="ios", data=data)
            self._actions.append(recorded)
            assert self._builder is not None
            self._builder.add(action, data)
            if self._callback:
                self._callback(recorded)

    def take_screenshot(self, name: str) -> None:
        self._record("screenshot", {"name": name})
        if self._driver:
            try:
                self._driver.screenshot(name)
            except Exception:
                pass

    def stop(self) -> Optional[Path]:
        """Stop streaming/recording and save the generated script."""
        self._recording = False
        self._streaming = False
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=2)

        if self._video_process:
            try:
                self._video_process.send_signal(signal.SIGINT)
                self._video_process.wait(timeout=5)
                self.video_path = self._video_local_path
            except Exception:
                self.video_path = None
            self._video_process = None

        if self._driver:
            try:
                self._driver.stop()
            except Exception:
                pass
        self._driver = None
        self._session = None
        if self._builder:
            return self._builder.save()
        return None

    @property
    def is_recording(self) -> bool:
        return self._recording

    def get_script_preview(self) -> str:
        if self._builder:
            return self._builder.build()
        return ""

    @property
    def wda_url(self) -> str:
        return self.config.ios.wda_url
