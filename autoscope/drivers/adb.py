"""Thin wrapper around the adb command-line tool."""

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


class ADBError(Exception):
    pass


class ADB:
    def __init__(self, serial: Optional[str] = None) -> None:
        self._adb = shutil.which("adb")
        if not self._adb:
            raise ADBError("adb not found in PATH. Install Android platform-tools.")
        self.serial = serial

    def _args(self, cmd: List[str]) -> List[str]:
        args = [self._adb]
        if self.serial:
            args.extend(["-s", self.serial])
        args.extend(cmd)
        return args

    def run(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        args = self._args(cmd)
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=check,
        )

    def devices(self) -> List[str]:
        """Return list of connected device serials."""
        result = self.run(["devices"])
        lines = result.stdout.strip().splitlines()
        serials = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serials.append(parts[0])
        return serials

    def first_device(self) -> str:
        devices = self.devices()
        if not devices:
            raise ADBError("No Android device connected via adb.")
        return devices[0]

    def shell(self, command: str) -> str:
        result = self.run(["shell", command])
        return result.stdout.strip()

    def screenshot(self, dest: Path) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        remote = "/sdcard/autoscope_screenshot.png"
        self.run(["shell", "screencap", "-p", remote])
        self.run(["pull", remote, str(dest)])
        self.run(["shell", "rm", remote], check=False)
        return dest

    def install(self, apk_path: str) -> None:
        path = Path(apk_path)
        if not path.exists():
            raise ADBError(f"APK not found: {apk_path}")
        self.run(["install", "-r", str(path)])

    def uninstall(self, package: str) -> None:
        self.run(["uninstall", package], check=False)
