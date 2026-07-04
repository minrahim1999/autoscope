"""Persisted desktop app UI preferences.

Distinct from config.yaml (driver/runner config, hand-edited, full of
explanatory comments a YAML rewrite would destroy): this is a small JSON
file for preferences the desktop app itself changes at runtime, such as
where to save generated scripts and reports. Lives alongside config.yaml in
the app's writable data directory.
"""

import json
from pathlib import Path
from typing import Optional

_SETTINGS_FILENAME = "desktop_settings.json"


def _settings_path() -> Path:
    # Deferred import: paths.py calls back into this module to resolve
    # get_scripts_dir()/get_reports_dir() overrides, so this can't be a
    # top-level import without creating a circular import.
    from autoscope.desktop.paths import get_app_dir

    return get_app_dir() / _SETTINGS_FILENAME


def load_settings() -> dict:
    path = _settings_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings(settings: dict) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def get_scripts_dir_override() -> Optional[str]:
    return load_settings().get("scripts_dir")


def set_scripts_dir_override(path: Optional[str]) -> None:
    settings = load_settings()
    if path:
        settings["scripts_dir"] = path
    else:
        settings.pop("scripts_dir", None)
    save_settings(settings)


def get_reports_dir_override() -> Optional[str]:
    return load_settings().get("reports_dir")


def set_reports_dir_override(path: Optional[str]) -> None:
    settings = load_settings()
    if path:
        settings["reports_dir"] = path
    else:
        settings.pop("reports_dir", None)
    save_settings(settings)
