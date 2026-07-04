"""Regression tests for the adb wrapper's output parsing.

ADB.__init__ requires a real adb binary to exist on PATH/common SDK
locations; that requirement is bypassed here by patching _find_adb so these
tests are independent of whether the test machine has Android tooling
installed. subprocess.run is patched to avoid touching a real adb/device.
"""

import subprocess
import unittest
from unittest import mock

from autoscope.drivers.adb import ADB, ADBError, _find_adb


def _fake_completed(stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["adb"], returncode=0, stdout=stdout, stderr="")


class TestFindAdb(unittest.TestCase):
    def test_raises_when_adb_missing_everywhere(self) -> None:
        with mock.patch("autoscope.drivers.adb.shutil.which", return_value=None), mock.patch(
            "autoscope.drivers.adb.Path.exists", return_value=False
        ):
            with self.assertRaises(ADBError):
                ADB()


class TestDevicesParsing(unittest.TestCase):
    def setUp(self) -> None:
        with mock.patch("autoscope.drivers.adb._find_adb", return_value="/usr/bin/adb"):
            self.adb = ADB()

    def test_single_ready_device(self) -> None:
        output = "List of devices attached\nemulator-5554\tdevice\n\n"
        with mock.patch.object(self.adb, "run", return_value=_fake_completed(output)):
            self.assertEqual(self.adb.devices(), ["emulator-5554"])

    def test_multiple_devices(self) -> None:
        output = "List of devices attached\nemulator-5554\tdevice\nR3CN30XXXX\tdevice\n\n"
        with mock.patch.object(self.adb, "run", return_value=_fake_completed(output)):
            self.assertEqual(self.adb.devices(), ["emulator-5554", "R3CN30XXXX"])

    def test_unauthorized_device_is_excluded(self) -> None:
        """A device awaiting a USB-debugging authorization prompt shows up as
        'unauthorized', not 'device' — it should not be treated as usable."""
        output = "List of devices attached\nABC123\tunauthorized\n\n"
        with mock.patch.object(self.adb, "run", return_value=_fake_completed(output)):
            self.assertEqual(self.adb.devices(), [])

    def test_offline_device_is_excluded(self) -> None:
        output = "List of devices attached\nABC123\toffline\n\n"
        with mock.patch.object(self.adb, "run", return_value=_fake_completed(output)):
            self.assertEqual(self.adb.devices(), [])

    def test_no_devices_attached(self) -> None:
        output = "List of devices attached\n\n"
        with mock.patch.object(self.adb, "run", return_value=_fake_completed(output)):
            self.assertEqual(self.adb.devices(), [])

    def test_first_device_raises_when_none_connected(self) -> None:
        output = "List of devices attached\n\n"
        with mock.patch.object(self.adb, "run", return_value=_fake_completed(output)):
            with self.assertRaises(ADBError):
                self.adb.first_device()

    def test_first_device_returns_first_of_several(self) -> None:
        output = "List of devices attached\nemulator-5554\tdevice\nR3CN30XXXX\tdevice\n\n"
        with mock.patch.object(self.adb, "run", return_value=_fake_completed(output)):
            self.assertEqual(self.adb.first_device(), "emulator-5554")


class TestShellAndSerialArgs(unittest.TestCase):
    def test_serial_is_injected_into_args_when_set(self) -> None:
        with mock.patch("autoscope.drivers.adb._find_adb", return_value="/usr/bin/adb"):
            adb = ADB(serial="emulator-5554")
        self.assertEqual(adb._args(["shell", "echo", "hi"])[:4], ["/usr/bin/adb", "-s", "emulator-5554", "shell"])

    def test_no_serial_flag_when_serial_unset(self) -> None:
        with mock.patch("autoscope.drivers.adb._find_adb", return_value="/usr/bin/adb"):
            adb = ADB()
        self.assertEqual(adb._args(["shell", "echo", "hi"])[:2], ["/usr/bin/adb", "shell"])


if __name__ == "__main__":
    unittest.main()
