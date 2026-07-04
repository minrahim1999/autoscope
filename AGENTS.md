# AGENTS.md — AutoScope

Compact guidance for OpenCode sessions working in this repo.

## Project shape

- Python package `autoscope/` is a minimal test harness for **web** (Playwright), **Android** (`uiautomator2` + `adb`), and **iOS** (WebDriverAgent via `wda`). The iOS recorder/driver requires the desktop app to run on macOS.
- Three usage modes:
  1. **CLI**: `python -m autoscope.cli`
  2. **Desktop recorder / runner**: `python run_desktop.py` (Flet UI)
  3. **Generated standalone scripts**: `scripts/*.py`
- No pytest, no CI, no lint/typecheck config — tests are stdlib `unittest` plus a custom tag filter in `autoscope/core/runner.py`.

## Entry points

| Surface | File | Real entry |
|---|---|---|
| CLI | `autoscope/cli.py` | `main()` → `run_tests()` or `crawl()` |
| Desktop dev | `main.py`, `run_desktop.py`, `run_desktop.sh` | `autoscope.desktop.app:main` |
| Test base class | `autoscope/core/case.py` | `AutomateTestCase` |
| Web driver | `autoscope/drivers/web.py` | `WebDriver` (wraps Playwright) |
| Android driver | `autoscope/drivers/android.py` | `AndroidDriver` (wraps `uiautomator2` + `adb`) |
| iOS driver | `autoscope/drivers/ios.py` | `IOSDriver` (wraps `wda`, connects to an already-running WebDriverAgent) |
| Crawler | `autoscope/crawler.py` | `crawl()` / `save_crawl_report()` |

## Developer commands

```bash
# Install deps + Playwright browser
pip install -r requirements.txt
playwright install chromium   # or firefox / webkit

# Run all unittest-based tests discovered under current dir
python -m autoscope.cli run

# Run only web, Android, or iOS tests (tag filtering)
python -m autoscope.cli run --tag web
python -m autoscope.cli run --tag android
python -m autoscope.cli run --tag ios

# iOS: start WebDriverAgent against a booted Simulator first (one-time per boot)
./tools/start_ios_wda.sh

# Run a single test module/class by limiting the start dir + pattern
python -m autoscope.cli run --start-dir tests_web --pattern test_example_web.py

# Crawl a site starting from a URL (reports -> var/reports/crawl.html & crawl.json)
python -m autoscope.cli crawl --url https://example.com
python -m autoscope.cli crawl --url https://example.com --username alice --password secret

# Desktop app in dev mode
python run_desktop.py
# or
./run_desktop.sh

# Convenience wrapper for CLI
./run.sh [run|...]
```

## Configuration

- Default config file: `config.yaml`.
- Env overrides use these exact prefixes (not `TESTPILOT_`):
  - `AT_WEB_*` → maps to `config.yaml:web.*`
  - `AT_ANDROID_*` → maps to `config.yaml:android.*`
  - `AT_IOS_*` → maps to `config.yaml:ios.*`
  - `AT_RUNNER_*` → maps to `config.yaml:runner.*`
- Booleans are parsed (`true`/`false`) and digit-only values become ints; everything else is a string.
- In packaged desktop builds, `AUTOMATE_TESTER_HOME` points to the writable app-data dir and the packaged `config.yaml` is preferred.

## Writing tests

- Inherit from `autoscope.AutomateTestCase`.
- Tag classes to control which drivers are provisioned:
  - `tags = ("web",)` → starts the web driver
  - `tags = ("android",)` → starts the Android driver
  - `tags = ("ios",)` → starts the iOS driver
  - `tags = ("web", "android", "ios")` → starts all three
  - Alternatively set class attrs `needs_web = True` / `needs_android = True` / `needs_ios = True`
- Inside a test:
  - `self.web` is a Playwright **`Page`** (not a `WebDriver`). Use `self.web.goto(...)`, `self.web.click(...)`, etc.
  - `self.android` is a `uiautomator2` **`Device`** (not an `AndroidDriver`). Use `self.android(text="OK").click()`, etc.
  - `self.ios` is a `wda.Client` session (not an `IOSDriver`). Use `self.ios.tap(x, y)`, `self.ios.swipe(...)`, etc.
  - `self.config` is the loaded `Config` dataclass.
- Screenshot helpers exist on the test case:
  - `self.web_screenshot(name)`
  - `self.android_screenshot(name)`
  - `self.ios_screenshot(name)`
- Failure screenshots are auto-captured to `var/reports/screenshots/` if `screenshot_on_failure` is enabled. Use distinct filenames across platforms — they share one directory.

## Generated scripts & desktop app

- The desktop recorder writes scripts to `scripts/`, for web, Android, and iOS (Web Manual, Android Manual, iOS Manual tabs).
- A generated script is a plain Python file with a `run()` function.
- Its platform is detected from the first-line comment, e.g. `# platform: web` or `# platform: android`.
- The desktop **Auto Run** tab executes these scripts in a subprocess via `autoscope/desktop/runner/script_runner.py` and writes `var/reports/auto_results.json` + `var/reports/auto_report.html`.
- Playwright browsers and `adb` are **not bundled**; the app checks for them at startup and can prompt to install Chromium.
- The desktop **Settings** tab lets the user pick custom scripts/reports folders (native OS dialog, `autoscope/desktop/folder_picker.py`), persisted to `desktop_settings.json` (`autoscope/desktop/settings.py`) and changeable anytime. `paths.py`'s `get_scripts_dir()`/`get_reports_dir()` are the single source of truth, so overrides apply everywhere automatically.

## Diagnostics & debugging

One-off Playwright probes live at the repo root for quick debugging:

- `tools/diag_load.py <url>` — load a page and print status/title/URL.
- `tools/diag_login.py` — hardcoded target login flow probe (uses `CRAWL_USERNAME` / `CRAWL_PASSWORD`).
- `tools/diag_crawl_steps.py` — step-by-step login + link extraction probe.

## Gotchas

- There is no test framework beyond stdlib `unittest`; the runner in `autoscope/core/runner.py` does discovery, tag filtering, and JSON/HTML reporting.
- Android tests require `adb` on PATH and a connected device. `device_serial: null` in config means "first available adb device".
- Web tests require the selected Playwright browser to be installed separately (`playwright install ...`).
- iOS tests require a WebDriverAgent instance already running at `config.yaml:ios.wda_url` (default `http://localhost:8100`); `IOSDriver` connects to it but does not build/launch WDA. Run `./tools/start_ios_wda.sh` once per Simulator boot. Real devices need `tidevice`. macOS + Xcode only.
- Crawl auto-login runs **only on the first page** and uses fallback selectors from `config.yaml` under `web.login_selectors`.
- Build scripts (`packaging/build_macos.sh`, `packaging/build_linux.sh`, `packaging/build_windows.ps1`) just call `flet build ...`; see `pyproject.toml [tool.flet]` for product/artifact names.
- Do not use `ft.FilePicker` (Flet 0.85.3): "Unknown control: FilePicker" on macOS desktop even on a fresh dev client (upstream bug, flet-dev/flet#6422/#6040). `autoscope/desktop/folder_picker.py` shells out to native OS folder dialogs as separate processes instead (tkinter's `askdirectory()` also doesn't work here — it needs the main thread on macOS, which Flet's event loop already owns).
- A leftover `build/macos/AutoScope.app` (or `build/windows`/`build/linux`) from a prior `flet build` takes priority over the downloaded dev client and can be missing controls added since — delete `build/<platform>/` first if something shows as "Unknown control" in dev mode.
