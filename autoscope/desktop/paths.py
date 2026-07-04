"""Resolve application directories for development and packaged builds."""

import os
import shutil
from pathlib import Path


def is_packaged() -> bool:
    """Return True when running inside a Flet packaged app."""
    return bool(os.environ.get("FLET_APP_STORAGE_DATA"))


def get_app_dir() -> Path:
    """Return a writable directory for scripts, reports, and config."""
    if is_packaged():
        base = Path(os.environ["FLET_APP_STORAGE_DATA"])
    else:
        base = Path.cwd()
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_scripts_dir() -> Path:
    path = get_app_dir() / "scripts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_reports_dir() -> Path:
    path = get_app_dir() / "var" / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_path() -> Path:
    """Return the active config.yaml path. In packaged mode this is copied to app data."""
    app_dir = get_app_dir()
    packaged_config = app_dir / "config.yaml"
    if is_packaged():
        if not packaged_config.exists() and (Path.cwd() / "config.yaml").exists():
            shutil.copy(Path.cwd() / "config.yaml", packaged_config)
        return packaged_config
    # Development: prefer project root config.yaml
    project_config = Path.cwd() / "config.yaml"
    if project_config.exists():
        return project_config
    return packaged_config
