# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Light/dark theme toggle in the desktop app navigation rail.

### Fixed
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
