"""iOS driver using WebDriverAgent (via the `wda` client) for automation.

Unlike ADB for Android, there is no lightweight always-available system tool
for driving iOS UI. IOSDriver instead connects to an already-running
WebDriverAgent (WDA) HTTP server -- it does not build or launch WDA itself,
since that's a multi-minute Xcode build requiring the WebDriverAgent project
(not vendored in this repo). See tools/start_ios_wda.sh to start one against
a booted Simulator, or docs/README for real-device setup via `tidevice`.
"""

from pathlib import Path
from typing import Optional

import wda

from autoscope.config.loader import IOSConfig


class IOSDriverError(Exception):
    pass


class IOSDriver:
    def __init__(self, config: IOSConfig) -> None:
        self.config = config
        self._client: Optional[wda.Client] = None
        self._session: Optional[wda.Client] = None

    def start(self) -> wda.Client:
        self._client = wda.Client(self.config.wda_url)
        try:
            status = self._client.status()
        except Exception as exc:
            raise IOSDriverError(
                f"Could not reach WebDriverAgent at {self.config.wda_url}. "
                "Start one first -- see tools/start_ios_wda.sh (Simulator) "
                "or the iOS setup docs (real device via tidevice)."
            ) from exc
        if not status.get("ready", True):
            raise IOSDriverError(f"WebDriverAgent at {self.config.wda_url} reported not ready: {status}")

        if self.config.bundle_id:
            self._session = self._client.session(bundle_id=self.config.bundle_id)
        else:
            self._session = self._client.session()
        return self._session

    @property
    def session(self) -> wda.Client:
        if self._session is None:
            raise RuntimeError("iOS driver not started. Call start() first.")
        return self._session

    def screenshot(self, name: str) -> Path:
        path = Path(self.config.screenshot_dir) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        self.session.screenshot().save(str(path))
        return path

    def stop(self) -> None:
        if self._client and self.config.bundle_id:
            try:
                self._client.app_terminate(self.config.bundle_id)
            except Exception:
                pass
        self._session = None
        self._client = None
