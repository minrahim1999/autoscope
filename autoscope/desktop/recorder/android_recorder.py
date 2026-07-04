"""Record manual Android interactions by streaming the device screen."""

import base64
import io
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from PIL import Image

from autoscope.config.loader import Config, load_config
from autoscope.desktop.recorder.script_builder import RecordedAction, ScriptBuilder
from autoscope.drivers.adb import ADB
from autoscope.drivers.android import AndroidDriver


class AndroidRecorder:
    """Stream an Android device screen to the desktop and record taps/inputs."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or load_config()
        self._driver: Optional[AndroidDriver] = None
        self._device = None
        self._adb: Optional[ADB] = None
        self._actions: List[RecordedAction] = []
        self._builder: Optional[ScriptBuilder] = None
        self._callback: Optional[Callable[[RecordedAction], None]] = None
        self._frame_callback: Optional[Callable[[str], None]] = None
        self._status_callback: Optional[Callable[[str], None]] = None
        self._recording = False
        self._streaming = False
        self._stream_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._screen_size: Tuple[int, int] = (0, 0)
        self._display_scale: float = 1.0
        self._video_process = None
        self._video_remote_path: Optional[str] = None
        self.video_path: Optional[Path] = None

    def set_callbacks(
        self,
        action_callback: Callable[[RecordedAction], None],
        frame_callback: Callable[[str], None],
    ) -> None:
        self._callback = action_callback
        self._frame_callback = frame_callback

    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Optional hook invoked when the stream health changes (e.g. device drops off)."""
        self._status_callback = callback

    def start(self, name: str = "android_recording", record_video: bool = False) -> None:
        """Connect to the first available Android device and start streaming."""
        self._actions = []
        self._builder = ScriptBuilder(platform="android", name=name)
        self._recording = True
        self._streaming = True
        self.video_path = None

        self._adb = ADB()
        serial = self.config.android.device_serial or self._adb.first_device()
        self.config.android.device_serial = serial

        self._driver = AndroidDriver(self.config.android)
        self._device = self._driver.start()

        # Determine real screen size via adb for accurate coordinate mapping
        try:
            size_output = self._driver.adb.run(["shell", "wm", "size"]).stdout.strip()
            # e.g. "Physical size: 1080x1920"
            for part in size_output.replace(",", " ").split():
                if "x" in part and part.split("x")[0].isdigit():
                    w, h = part.split("x")
                    self._screen_size = (int(w), int(h))
                    break
        except Exception:
            self._screen_size = (1080, 1920)

        if record_video:
            try:
                self._video_remote_path = "/sdcard/autoscope_record.mp4"
                self._video_process = self._driver.adb.start_screenrecord(self._video_remote_path)
            except Exception:
                self._video_process = None

        self._stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._stream_thread.start()

    def _stream_loop(self) -> None:
        """Continuously capture and encode screenshots for the UI."""
        consecutive_failures = 0
        disconnected = False
        # A device that stops responding (USB unplugged, screen off, adb drop)
        # used to fail silently forever with a frozen preview. Surface it after
        # a short grace period, and clear the warning once frames resume.
        failure_threshold = 15  # ~3s at the 0.2s loop interval below

        while self._streaming:
            try:
                if not self._device:
                    time.sleep(0.5)
                    continue
                img = self._device.screenshot()
                if img is None:
                    raise RuntimeError("empty screenshot from device")
                # Downscale for streaming performance while preserving aspect ratio
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
                            "Device not responding — check the USB/Wi-Fi connection"
                        )
            time.sleep(0.2)

    def tap(self, display_x: int, display_y: int, display_width: int, display_height: int) -> None:
        """Map tap coordinates from the on-screen image to device pixels."""
        if self._screen_size[0] == 0 or self._screen_size[1] == 0:
            return
        # Assume the image is stretched to fill the container (BoxFit.FILL)
        device_x = int(display_x / display_width * self._screen_size[0])
        device_y = int(display_y / display_height * self._screen_size[1])
        self._record("tap", {"x": device_x, "y": device_y})
        if self._driver:
            try:
                self._driver.adb.run(["shell", "input", "tap", str(device_x), str(device_y)])
            except Exception:
                pass

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        display_width: int,
        display_height: int,
        duration_ms: int = 300,
    ) -> None:
        if self._screen_size[0] == 0 or self._screen_size[1] == 0:
            return
        dx1 = int(x1 / display_width * self._screen_size[0])
        dy1 = int(y1 / display_height * self._screen_size[1])
        dx2 = int(x2 / display_width * self._screen_size[0])
        dy2 = int(y2 / display_height * self._screen_size[1])
        self._record("swipe", {"x1": dx1, "y1": dy1, "x2": dx2, "y2": dy2, "duration": duration_ms})
        if self._driver:
            try:
                self._driver.adb.run(
                    ["shell", "input", "swipe", str(dx1), str(dy1), str(dx2), str(dy2), str(duration_ms)]
                )
            except Exception:
                pass

    def input_text(self, text: str) -> None:
        """Send text to the device and record it."""
        self._record("input", {"text": text})
        if self._driver:
            try:
                # adb shell input text has limited charset; replace spaces with %s
                safe_text = text.replace(" ", "%s")
                self._driver.adb.run(["shell", "input", "text", safe_text])
            except Exception:
                pass

    def _record(self, action: str, data: dict) -> None:
        with self._lock:
            if not self._recording:
                return
            recorded = RecordedAction(action=action, platform="android", data=data)
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
        if self._video_process and self._driver:
            try:
                video_dir = Path(self.config.android.video_dir)
                name = self._builder.name if self._builder else "recording"
                dest = video_dir / f"{name}_android.mp4"
                self.video_path = self._driver.adb.stop_screenrecord(
                    self._video_process, self._video_remote_path, dest
                )
            except Exception:
                self.video_path = None
            self._video_process = None
        if self._driver:
            try:
                self._driver.stop()
            except Exception:
                pass
        self._driver = None
        self._device = None
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
    def serial(self) -> str:
        return self.config.android.device_serial or ""
