# AGENTS.md — AutoScope

Compact guidance for OpenCode sessions working in this repo.

## Project shape

- Python package `autoscope/` is a minimal test harness for **web** (Playwright) and **Android mobile** (`uiautomator2` + `adb`).
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
| Mobile driver | `autoscope/drivers/mobile.py` | `MobileDriver` (wraps `uiautomator2` + `adb`) |
| Crawler | `autoscope/crawler.py` | `crawl()` / `save_crawl_report()` |

## Developer commands

```bash
# Install deps + Playwright browser
pip install -r requirements.txt
playwright install chromium   # or firefox / webkit

# Run all unittest-based tests discovered under current dir
python -m autoscope.cli run

# Run only web or mobile tests (tag filtering)
python -m autoscope.cli run --tag web
python -m autoscope.cli run --tag mobile

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
  - `AT_MOBILE_*` → maps to `config.yaml:mobile.*`
  - `AT_RUNNER_*` → maps to `config.yaml:runner.*`
- Booleans are parsed (`true`/`false`) and digit-only values become ints; everything else is a string.
- In packaged desktop builds, `AUTOMATE_TESTER_HOME` points to the writable app-data dir and the packaged `config.yaml` is preferred.

## Writing tests

- Inherit from `autoscope.AutomateTestCase`.
- Tag classes to control which drivers are provisioned:
  - `tags = ("web",)` → starts the web driver
  - `tags = ("mobile",)` → starts the mobile driver
  - `tags = ("web", "mobile")` → starts both
  - Alternatively set class attrs `needs_web = True` / `needs_mobile = True`
- Inside a test:
  - `self.web` is a Playwright **`Page`** (not a `WebDriver`). Use `self.web.goto(...)`, `self.web.click(...)`, etc.
  - `self.mobile` is a `uiautomator2` **`Device`** (not a `MobileDriver`). Use `self.mobile(text="OK").click()`, etc.
  - `self.config` is the loaded `Config` dataclass.
- Screenshot helpers exist on the test case:
  - `self.web_screenshot(name)`
  - `self.mobile_screenshot(name)`
- Failure screenshots are auto-captured to `var/reports/screenshots/` if `screenshot_on_failure` is enabled.

## Generated scripts & desktop app

- The desktop recorder writes scripts to `scripts/`.
- A generated script is a plain Python file with a `run()` function.
- Its platform is detected from the first-line comment, e.g. `# platform: web` or `# platform: mobile`.
- The desktop **Auto Run** tab executes these scripts in a subprocess via `autoscope/desktop/runner/script_runner.py` and writes `var/reports/auto_results.json` + `var/reports/auto_report.html`.
- Playwright browsers and `adb` are **not bundled**; the app checks for them at startup and can prompt to install Chromium.

## Diagnostics & debugging

One-off Playwright probes live at the repo root for quick debugging:

- `tools/diag_load.py <url>` — load a page and print status/title/URL.
- `tools/diag_login.py` — hardcoded target login flow probe (uses `CRAWL_USERNAME` / `CRAWL_PASSWORD`).
- `tools/diag_crawl_steps.py` — step-by-step login + link extraction probe.

## Gotchas

- There is no test framework beyond stdlib `unittest`; the runner in `autoscope/core/runner.py` does discovery, tag filtering, and JSON/HTML reporting.
- Mobile tests require `adb` on PATH and a connected device. `device_serial: null` in config means "first available adb device".
- Web tests require the selected Playwright browser to be installed separately (`playwright install ...`).
- Crawl auto-login runs **only on the first page** and uses fallback selectors from `config.yaml` under `web.login_selectors`.
- Build scripts (`packaging/build_macos.sh`, `packaging/build_linux.sh`, `packaging/build_windows.ps1`) just call `flet build ...`; see `pyproject.toml [tool.flet]` for product/artifact names.
