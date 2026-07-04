import json
import os
from dataclasses import dataclass, field, fields
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
    screenshot_dir: str = "var/reports/screenshots"
    video_dir: str = "var/reports/videos"
    login_selectors: dict = field(default_factory=dict)


@dataclass
class AndroidConfig:
    device_serial: Optional[str] = None
    app_package: Optional[str] = None
    app_activity: Optional[str] = None
    install_apk: Optional[str] = None
    uninstall_before: bool = False
    screenshot_on_failure: bool = True
    screenshot_dir: str = "var/reports/screenshots"
    video_dir: str = "var/reports/videos"


@dataclass
class IOSConfig:
    # IOSDriver connects to an already-running WebDriverAgent instance; it
    # does not build/launch WDA itself (that's a multi-minute Xcode build
    # requiring the WebDriverAgent project, which this repo does not vendor).
    # See tools/start_ios_wda.sh to start one against a booted Simulator.
    wda_url: str = "http://localhost:8100"
    bundle_id: Optional[str] = None
    screenshot_on_failure: bool = True
    screenshot_dir: str = "var/reports/screenshots"
    video_dir: str = "var/reports/videos"


@dataclass
class RunnerConfig:
    output_dir: str = "var/reports"
    json_report: str = "var/reports/results.json"
    html_report: str = "var/reports/report.html"
    fail_fast: bool = False
    verbosity: int = 2


@dataclass
class Config:
    web: WebConfig = field(default_factory=WebConfig)
    android: AndroidConfig = field(default_factory=AndroidConfig)
    ios: IOSConfig = field(default_factory=IOSConfig)
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

    def _env_override(prefix: str, data_dict: dict, schema: type) -> None:
        # Iterate the dataclass schema, not data_dict's own keys, so an env var
        # can set a value even when config.yaml omits that key entirely.
        for f in fields(schema):
            env_key = f"{prefix}_{f.name.upper()}"
            if env_key in os.environ:
                raw = os.environ[env_key]
                if raw.lower() in ("true", "false"):
                    data_dict[f.name] = raw.lower() == "true"
                elif raw.isdigit():
                    data_dict[f.name] = int(raw)
                else:
                    data_dict[f.name] = raw

    web_data = data.get("web", {})
    android_data = data.get("android", {})
    ios_data = data.get("ios", {})
    runner_data = data.get("runner", {})
    _env_override("AT_WEB", web_data, WebConfig)
    _env_override("AT_ANDROID", android_data, AndroidConfig)
    _env_override("AT_IOS", ios_data, IOSConfig)
    _env_override("AT_RUNNER", runner_data, RunnerConfig)

    return Config(
        web=WebConfig(**web_data),
        android=AndroidConfig(**android_data),
        ios=IOSConfig(**ios_data),
        runner=RunnerConfig(**runner_data),
    )
