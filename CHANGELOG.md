# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Light/dark theme toggle in the desktop app navigation rail.
- Swipe gesture support in **Mobile Manual**: drag on the device preview to record and replay swipes, using the `MobileRecorder.swipe()` / `ScriptBuilder` swipe support that already existed but had no UI to trigger it.
- Stream health feedback in **Mobile Manual**: after ~3s of failed screen captures (device unplugged, screen off, adb drop) the status line now says so instead of leaving a frozen, silently-dead preview; it clears automatically once frames resume.
- `tests_core/`: a new stdlib-`unittest` suite (49 tests, no browser/device required) covering `ScriptBuilder`, `config/loader.py`, HTML report escaping, `MobileRecorder` coordinate math, `adb` output parsing, and a headless smoke test that builds all five desktop views — the same class of check that would have caught the Flet API-drift bugs below automatically.

### Fixed
- Fixed HTML/crawl reports embedding unescaped test names, messages, and tracebacks (`autoscope/reporting/html.py`) — a crawled page with `<script>`/`<img onerror=...>` in its title or an exception message could inject markup into a report opened directly in a browser. Now escaped with `html.escape()`.
- Fixed `AT_WEB_*` / `AT_MOBILE_*` / `AT_RUNNER_*` environment variable overrides silently doing nothing unless the corresponding key already existed in `config.yaml` — `_env_override` only iterated keys already present in the loaded YAML dict instead of the full dataclass schema. Env overrides now apply regardless of what's in config.yaml, matching the documented behavior.
- Fixed the mobile recorder never showing the streamed device screen and dropping every tap/text input: `page.run_task()` requires an `async` coroutine in Flet 0.85 and was being called with plain sync functions (raised `TypeError`, silently swallowed in the streaming loop); tap coordinates were read from a nonexistent `TapEvent.local_x/local_y` (now `local_position.x/y`); and the live frame was assigned to a nonexistent `Image.src_base64` (now `Image.src`, which accepts a base64 data URI directly).
- Fixed a startup/runtime crash from `ft.Colors.SUCCESS` / `ft.Colors.WARNING`, which don't exist in this Flet version (Material3 has no built-in success/warning role) — replaced with `ft.Colors.GREEN` / `ft.Colors.AMBER`. This fired unconditionally whenever `adb` wasn't detected, before the main window ever appeared.
- Fixed generated recorder scripts being invalid Python (`SyntaxError`: empty `try:` block) when a manual recording session captured zero actions; `ScriptBuilder` now emits `pass` as a fallback body. Repaired three previously-committed scripts under `scripts/` that were broken this way.
- Fixed `config/loader.py` dataclass defaults still pointing at the old `reports/` path after the project-wide move to `var/reports/`; a missing config.yaml would silently resurrect the old layout.
- Fixed desktop app home page appearing empty on startup; navigation now refreshes the whole page once after building each view.
- Fixed **Mobile Manual** and **Auto Run** tabs failing to open due to Flet 0.85 API changes (`ft.Image` now requires `src`, `ft.alignment.center` replaced with `ft.Alignment.CENTER`, snackbar uses `page.overlay`).
- Fixed **Auto Run** script list throwing "Control must be added to the page first" during initial render.
- Widened the navigation rail so all labels, including "Mobile Manual", stay centered on a single line.
- Made cross-platform build scripts (`build_macos.sh`, `build_linux.sh`, `build_windows.ps1`) non-interactive and safe for CI by adding `--yes` and `--no-rich-output` flags.
- Bypassed rich Windows console crash on CI runners by piping `flet build` output through a log file and setting UTF-8 console/env encoding.

## [1.0.0] - 2026-07-04

### Added
- Initial release of AutoScope: a minimal test harness for web (Playwright) and Android mobile (uiautomator2 + adb).
- Desktop recorder / runner built with Flet for manual web and mobile test recording.
- CLI for running stdlib `unittest`-based tests with tag filtering (`web`, `mobile`).
- No-script crawl mode with optional auto-login and JSON/HTML reports.
- Screenshot-on-failure helpers for both web and mobile tests.
- Config loading from `config.yaml` with env overrides using `AT_WEB_*`, `AT_MOBILE_*`, and `AT_RUNNER_*` prefixes.
- Packaging scripts for macOS (`.app` + `.dmg`), Windows (`.exe`), and Linux.
