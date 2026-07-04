"""Android driver using uiautomator2 + adb fallback helpers."""

from pathlib import Path
from typing import Optional

import uiautomator2 as u2

from autoscope.config.loader import AndroidConfig
from autoscope.drivers.adb import ADB


class AndroidDriver:
    def __init__(self, config: AndroidConfig) -> None:
        self.config = config
        self.adb = ADB(serial=config.device_serial)
        self._device: Optional[u2.Device] = None

    @property
    def serial(self) -> str:
        return self.config.device_serial or self.adb.first_device()

    def start(self) -> u2.Device:
        self.config.device_serial = self.serial
        self._device = u2.connect(self.serial)
        self._device.implicitly_wait(10.0)

        if self.config.uninstall_before and self.config.app_package:
            self.adb.uninstall(self.config.app_package)

        if self.config.install_apk:
            self.adb.install(self.config.install_apk)

        if self.config.app_package and self.config.app_activity:
            self._device.app_start(
                self.config.app_package,
                self.config.app_activity,
            )
        return self._device

    @property
    def device(self) -> u2.Device:
        if self._device is None:
            raise RuntimeError("Android driver not started. Call start() first.")
        return self._device

    def screenshot(self, name: str) -> Path:
        path = Path(self.config.screenshot_dir) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        self.device.screenshot(str(path))
        return path

    def stop(self) -> None:
        if self._device and self.config.app_package:
            try:
                self._device.app_stop(self.config.app_package)
            except Exception:
                pass
        self._device = None

    def shell(self, command: str) -> str:
        return self.adb.shell(command)
