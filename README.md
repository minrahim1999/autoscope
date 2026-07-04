# AutoScope

A minimal, batteries-included test harness for **web** (via Playwright), **Android mobile** (via ADB + uiautomator2), and **iOS** (via WebDriverAgent) — now with a **desktop app** for recording and replaying web/mobile tests, packaged for **macOS (.dmg), Windows (.exe), and Linux**.

## Features

- **Desktop app** built with Flet (Flutter) for a modern, cross-platform native UI.
- **Manual test recording** for web and mobile: perform actions and generate automation scripts.
- **Auto test execution** of generated scripts for both web and mobile.
- Web testing with Chromium/Firefox/WebKit through Playwright.
- Android testing through real ADB-connected devices using `uiautomator2`.
- iOS testing (Simulator or real device) through WebDriverAgent using `wda`, including a full desktop **iOS Manual** recorder tab — macOS only (an Apple tooling requirement).
- Screenshot-on-failure for web, mobile, and iOS.
- Tag-based filtering (`web`, `mobile`, `ios`).
- JSON + HTML reports.
- Pure stdlib `unittest` — no heavy test framework to learn.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium   # or firefox / webkit
```

Make sure `adb` is on your PATH and your Android device is connected:

```bash
adb devices
```

For iOS, start WebDriverAgent against a booted Simulator (macOS + Xcode required; one-time per Simulator boot — the first run clones and builds WebDriverAgent, which takes a few minutes):

```bash
./tools/start_ios_wda.sh
```

## Desktop App

Launch the desktop application in development mode:

```bash
python run_desktop.py
# or
./run_desktop.sh
```

Use the moon/sun icon at the bottom of the navigation rail to switch between light and dark themes.

### Manual Recording

1. Choose **Web Manual**, **Mobile Manual**, or **iOS Manual** from the navigation rail.
2. Enter a start URL (web) or connect to a device (mobile/iOS — for iOS, start WebDriverAgent first, see Install).
3. Click **Start Recording / Connect & Stream**.
4. Interact with the browser or the streamed device screen. Use the camera button for a screenshot, or check "Record video" beforehand to also capture a video.
5. Click **Stop & Save** to generate a Python script in `scripts/`, then optionally click **Run Test** to replay it immediately.

### Auto Run

1. Choose **Auto Run** from the navigation rail.
2. Select a generated script.
3. Click **Run Selected**.
4. View the report in **Reports**.

## Packaging

The desktop app can be packaged into native installers using Flet's build commands.

### macOS (.app + .dmg)

Prerequisites: macOS, Xcode, CocoaPods, Flutter (auto-downloaded by Flet if missing).

```bash
./packaging/build_macos.sh
```

Outputs:
- `build/macos/AutoScope.app`
- `build/macos/AutoScope.dmg`

If `create-dmg` is not installed, the script installs it via Homebrew.

### Windows (.exe installer)

Prerequisites: Windows, Visual Studio with "Desktop development with C++" workload, Flutter.

```powershell
.\packaging\build_windows.ps1
```

Output: `build/windows/`

### Linux

Prerequisites: Linux, Flutter, GTK/build libraries (see `packaging/build_linux.sh` comments).

```bash
./packaging/build_linux.sh
```

Output: `build/linux/`

### Notes for packaged apps

- Generated scripts and reports are stored in the app's writable data directory, not inside the bundle.
- The first launch copies `config.yaml` into the app data directory so it can be edited later.
- Playwright Chromium browsers are not bundled; on first launch the app prompts to install them, or you can run `playwright install chromium` separately.
- `adb` is not bundled; it must be available on the user's PATH for mobile testing.
- The iOS Manual recorder tab only works when the desktop app itself runs on macOS with WebDriverAgent already running (see Install).

## CLI Quick Start

Run all tests:

```bash
python -m autoscope.cli run
```

Run only web tests:

```bash
python -m autoscope.cli run --tag web
```

Run only mobile tests:

```bash
python -m autoscope.cli run --tag mobile
```

Run only iOS tests (start WebDriverAgent first — see Install):

```bash
python -m autoscope.cli run --tag ios
```

## No-Script Crawl Mode

Pass a URL and optional credentials; the tool will log in (if selectors match), then crawl every internal link and report broken pages:

```bash
python -m autoscope.cli crawl --url https://example.com
```

With login:

```bash
python -m autoscope.cli crawl --url https://example.com --username alice --password secret
```

Limit scope:

```bash
python -m autoscope.cli crawl --url https://example.com --max-depth 2 --max-pages 20
```

Crawl reports are written to `var/reports/crawl.html` and `var/reports/crawl.json`.

## Configuration

Edit `config.yaml` or override with environment variables:

- `AT_WEB_HEADLESS=true`
- `AT_WEB_BROWSER=firefox`
- `AT_MOBILE_DEVICE_SERIAL=<serial>`
- `AT_MOBILE_APP_PACKAGE=com.example.app`
- `AT_IOS_WDA_URL=http://localhost:8100`
- `AT_IOS_BUNDLE_ID=com.example.app`

## Writing Tests

```python
from autoscope import AutomateTestCase

class TestMyApp(AutomateTestCase):
    tags = ("web",)          # or ("mobile",), ("ios",), or any combination

    def test_login(self):
        self.web.goto("https://example.com/login")
        self.web.page.fill("input[name='user']", "alice")
        self.web.page.click("button[type='submit']")
        self.assertIn("dashboard", self.web.page.url)
```

For mobile tests, `self.mobile` is a `uiautomator2` Device instance:

```python
class TestAndroid(AutomateTestCase):
    tags = ("mobile",)

    def test_button(self):
        self.mobile.device(text="OK").click()
```

For iOS tests, `self.ios` is a `wda.Client` session (requires WebDriverAgent already running — see Install):

```python
class TestIOS(AutomateTestCase):
    tags = ("ios",)

    def test_button(self):
        self.ios(name="OK").click()
```

## Project Layout

```
autoscope/
  config/       config loader
  drivers/      web, mobile, ios, adb wrappers
  core/         test base class + runner
  reporting/    JSON + HTML reporters
  cli.py        command-line entry point
tests_web/      web test packages
tests_mobile/   mobile test packages
tests_ios/      iOS test packages (requires a running WebDriverAgent)
```
