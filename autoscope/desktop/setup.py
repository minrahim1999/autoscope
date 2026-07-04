"""Runtime environment setup helpers for the packaged desktop app."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def _executable(name: str):
    path = shutil.which(name)
    if path:
        return path
    # macOS GUI apps often don't inherit shell PATH; search common locations
    home = os.path.expanduser("~")
    candidates = [
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
        f"{home}/Library/Android/sdk/platform-tools/{name}",
        f"{home}/Android/Sdk/platform-tools/{name}",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def check_adb():
    if _executable("adb"):
        return True, "adb found"
    return False, "adb not found in PATH. Install Android platform-tools and add adb to PATH."


def check_playwright_browsers():
    """Check whether Playwright has at least Chromium installed."""
    try:
        with sync_playwright() as p:
            browser_type = getattr(p, "chromium", None)
            if browser_type is None:
                return False, "chromium browser type not available"
            executable_path = browser_type.executable_path
            if executable_path and Path(executable_path).exists():
                return True, f"Chromium found at {executable_path}"
            return False, "Chromium browser not installed"
    except Exception as e:
        return False, f"Playwright check failed: {e}"


def install_playwright_browsers():
    """Try to install Playwright Chromium browsers."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode == 0:
            return True, "Chromium installed successfully"
        return False, result.stdout + result.stderr
    except Exception as e:
        return False, f"Installation failed: {e}"
