"""Convert recorded actions into runnable Python automation scripts."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from autoscope.desktop.paths import get_scripts_dir


@dataclass
class RecordedAction:
    action: str
    platform: str
    data: dict = field(default_factory=dict)
    timestamp: Optional[str] = None


class ScriptBuilder:
    """Build a runnable Python script from recorded web/mobile actions."""

    def __init__(self, platform: str, name: str, base_url: Optional[str] = None) -> None:
        self.platform = platform  # "web" or "mobile"
        self.name = self._sanitize_name(name)
        self.base_url = base_url
        self.actions: List[RecordedAction] = []

    def add(self, action: str, data: dict) -> None:
        self.actions.append(
            RecordedAction(
                action=action,
                platform=self.platform,
                data=data,
                timestamp=datetime.now().isoformat(timespec="seconds"),
            )
        )

    def _sanitize_name(self, name: str) -> str:
        name = re.sub(r"[^\w\s-]", "", name).strip().lower()
        name = re.sub(r"[-\s]+", "_", name)
        if not name:
            name = "recording"
        return name

    def _quote(self, value: str) -> str:
        return repr(value)

    def build_web_script(self) -> str:
        lines = [
            f"# platform: web",
            f"# name: {self.name}",
            f"# generated: {datetime.now().isoformat()}",
            "from autoscope.drivers.web import WebDriver",
            "from autoscope.config.loader import load_config",
            "",
            "def run():",
            "    config = load_config()",
            "    driver = WebDriver(config.web)",
            "    page = driver.start()",
            "    try:",
        ]
        body_start = len(lines)

        last_url: Optional[str] = None
        for act in self.actions:
            if act.action == "goto":
                url = act.data.get("url", self.base_url or "about:blank")
                lines.append(f"        page.goto({self._quote(url)})")
                last_url = url
            elif act.action == "click":
                selector = act.data.get("selector", "")
                if selector:
                    lines.append(f"        page.click({self._quote(selector)})")
            elif act.action == "fill":
                selector = act.data.get("selector", "")
                value = act.data.get("value", "")
                if selector:
                    lines.append(f"        page.fill({self._quote(selector)}, {self._quote(value)})")
            elif act.action == "wait":
                ms = act.data.get("ms", 1000)
                lines.append(f"        page.wait_for_timeout({ms})")
            elif act.action == "screenshot":
                name = act.data.get("name", "screenshot.png")
                lines.append(f"        driver.screenshot({self._quote(name)})")

        if len(lines) == body_start:
            lines.append("        pass")

        lines.extend(
            [
                "    finally:",
                "        driver.stop()",
                "",
                'if __name__ == "__main__":',
                "    run()",
                "",
            ]
        )
        return "\n".join(lines)

    def build_mobile_script(self) -> str:
        lines = [
            f"# platform: mobile",
            f"# name: {self.name}",
            f"# generated: {datetime.now().isoformat()}",
            "from autoscope.drivers.mobile import MobileDriver",
            "from autoscope.config.loader import load_config",
            "",
            "def run():",
            "    config = load_config()",
            "    driver = MobileDriver(config.mobile)",
            "    device = driver.start()",
            "    try:",
        ]
        body_start = len(lines)

        for act in self.actions:
            if act.action == "tap":
                x = act.data.get("x", 0)
                y = act.data.get("y", 0)
                lines.append(f"        device.click({x}, {y})")
            elif act.action == "input":
                text = act.data.get("text", "")
                # Use adb shell input text to avoid element selection issues.
                lines.append(f"        driver.adb.run(['shell', 'input', 'text', {self._quote(text)}])")
            elif act.action == "swipe":
                x1 = act.data.get("x1", 0)
                y1 = act.data.get("y1", 0)
                x2 = act.data.get("x2", 0)
                y2 = act.data.get("y2", 0)
                duration = act.data.get("duration", 300)
                lines.append(
                    f"        driver.adb.run(['shell', 'input', 'swipe', '{x1}', '{y1}', '{x2}', '{y2}', '{duration}'])"
                )
            elif act.action == "wait":
                ms = act.data.get("ms", 1000)
                lines.append(f"        device.sleep({ms / 1000.0})")
            elif act.action == "screenshot":
                name = act.data.get("name", "screenshot.png")
                lines.append(f"        driver.screenshot({self._quote(name)})")

        if len(lines) == body_start:
            lines.append("        pass")

        lines.extend(
            [
                "    finally:",
                "        driver.stop()",
                "",
                'if __name__ == "__main__":',
                "    run()",
                "",
            ]
        )
        return "\n".join(lines)

    def build(self) -> str:
        if self.platform == "web":
            return self.build_web_script()
        if self.platform == "mobile":
            return self.build_mobile_script()
        raise ValueError(f"Unsupported platform: {self.platform}")

    def save(self, directory: Optional[Path] = None) -> Path:
        directory = directory or get_scripts_dir()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.name}_{self.platform}.py"
        counter = 1
        while path.exists():
            path = directory / f"{self.name}_{self.platform}_{counter:03d}.py"
            counter += 1
        path.write_text(self.build(), encoding="utf-8")
        return path
