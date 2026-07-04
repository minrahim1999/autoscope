import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class WebConfig:
    browser: str = "chromium"
    headless: bool = False
    base_url: str = "https://example.com"
    timeout_ms: int = 30000
    viewport: dict = field(default_factory=lambda: {"width": 1280, "height": 720})
    screenshot_on_failure: bool = True
    screenshot_dir: str = "reports/screenshots"
    login_selectors: dict = field(default_factory=dict)


@dataclass
class MobileConfig:
    platform: str = "android"
    device_serial: Optional[str] = None
    app_package: Optional[str] = None
    app_activity: Optional[str] = None
    install_apk: Optional[str] = None
    uninstall_before: bool = False
    screenshot_on_failure: bool = True
    screenshot_dir: str = "reports/screenshots"


@dataclass
class RunnerConfig:
    output_dir: str = "reports"
    json_report: str = "reports/results.json"
    html_report: str = "reports/report.html"
    fail_fast: bool = False
    verbosity: int = 2


@dataclass
class Config:
    web: WebConfig = field(default_factory=WebConfig)
    mobile: MobileConfig = field(default_factory=MobileConfig)
    runner: RunnerConfig = field(default_factory=RunnerConfig)


def load_config(path: str = "config.yaml") -> Config:
    """Load configuration from YAML/JSON or environment overrides."""
    # In packaged apps, prefer the writable app-data config directory.
    if "AUTOMATE_TESTER_HOME" in os.environ and path == "config.yaml":
        alt_path = Path(os.environ["AUTOMATE_TESTER_HOME"]) / "config.yaml"
        if alt_path.exists():
            path = str(alt_path)
    config_path = Path(path)
    data: dict = {}
    if config_path.exists():
        text = config_path.read_text(encoding="utf-8")
        if config_path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(text) or {}
        elif config_path.suffix == ".json":
            data = json.loads(text)

    def _env_override(prefix: str, data_dict: dict) -> None:
        for key in data_dict:
            env_key = f"{prefix}_{key.upper()}"
            if env_key in os.environ:
                raw = os.environ[env_key]
                if raw.lower() in ("true", "false"):
                    data_dict[key] = raw.lower() == "true"
                elif raw.isdigit():
                    data_dict[key] = int(raw)
                else:
                    data_dict[key] = raw

    web_data = data.get("web", {})
    mobile_data = data.get("mobile", {})
    runner_data = data.get("runner", {})
    _env_override("AT_WEB", web_data)
    _env_override("AT_MOBILE", mobile_data)
    _env_override("AT_RUNNER", runner_data)

    return Config(
        web=WebConfig(**web_data),
        mobile=MobileConfig(**mobile_data),
        runner=RunnerConfig(**runner_data),
    )
