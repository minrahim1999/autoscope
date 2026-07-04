"""Run generated automation scripts and produce JSON/HTML reports."""

import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional

from autoscope.config.loader import Config, load_config
from autoscope.desktop.paths import get_reports_dir, get_scripts_dir
from autoscope.reporting.html import generate_html_report


class ScriptRunner:
    """Run a generated Python script in an isolated subprocess."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or load_config()

    @staticmethod
    def discover_scripts(directory: Optional[Path] = None) -> List[Path]:
        directory = directory or get_scripts_dir()
        if not directory.exists():
            return []
        return sorted(directory.glob("*.py"))

    @staticmethod
    def detect_platform(script_path: Path) -> str:
        text = script_path.read_text(encoding="utf-8")
        for line in text.splitlines()[:5]:
            if line.startswith("# platform:"):
                return line.split(":", 1)[1].strip()
        name = script_path.name
        if "_web" in name:
            return "web"
        if "_mobile" in name:
            return "mobile"
        return "unknown"

    def run(self, script_path: Path) -> Dict:
        """Run the script and return a result dict."""
        script_path = Path(script_path).resolve()
        if not script_path.exists():
            return self._result("error", 0.0, f"Script not found: {script_path}")

        platform = self.detect_platform(script_path)

        # Build a temporary wrapper that imports and runs the target script's run()
        wrapper = f"""
import sys
import json
import time
import traceback
sys.path.insert(0, {repr(str(script_path.parent))})
sys.path.insert(0, {repr(str(Path.cwd()))})
start = time.time()
try:
    module_name = {repr(script_path.stem)}
    module = __import__(module_name)
    module.run()
    result = {{"status": "passed", "duration": time.time() - start, "error": None}}
except Exception as e:
    result = {{
        "status": "failed",
        "duration": time.time() - start,
        "error": repr(e),
        "traceback": traceback.format_exc(),
    }}
print("__RESULT__" + json.dumps(result))
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(wrapper)
            wrapper_path = Path(f.name)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd()) + os.pathsep + env.get("PYTHONPATH", "")

        start = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, str(wrapper_path)],
                capture_output=True,
                text=True,
                cwd=str(Path.cwd()),
                env=env,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            return self._result("error", time.time() - start, "Script timed out after 300s")
        finally:
            try:
                wrapper_path.unlink()
            except Exception:
                pass

        output = proc.stdout + proc.stderr
        duration = time.time() - start

        result_data = None
        for line in proc.stdout.splitlines():
            if line.startswith("__RESULT__"):
                try:
                    result_data = json.loads(line[len("__RESULT__"):])
                except Exception:
                    pass
                break

        if result_data:
            status = result_data.get("status", "failed")
            error = result_data.get("error")
            tb = result_data.get("traceback")
            return self._result(status, duration, error, tb, output)

        if proc.returncode == 0:
            return self._result("passed", duration, None, None, output)
        return self._result("failed", duration, output, None, output)

    def _result(
        self,
        status: str,
        duration: float,
        error: Optional[str],
        traceback_str: Optional[str] = None,
        output: str = "",
    ) -> Dict:
        return {
            "status": status,
            "duration_seconds": duration,
            "error": error,
            "traceback": traceback_str,
            "output": output,
        }

    def run_and_report(self, script_path: Path) -> Dict:
        """Run a script and write JSON/HTML reports."""
        result = self.run(script_path)
        report_data = {
            "type": "auto_run",
            "script": str(script_path),
            "duration_seconds": result["duration_seconds"],
            "summary": {
                "total": 1,
                "passed": 1 if result["status"] == "passed" else 0,
                "failed": 1 if result["status"] == "failed" else 0,
                "errors": 1 if result["status"] == "error" else 0,
                "skipped": 0,
            },
            "tests": [
                {
                    "name": script_path.name,
                    "status": result["status"],
                    "message": result["error"] or "",
                    "traceback": result["traceback"] or "",
                }
            ],
        }

        output_dir = get_reports_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        json_path = output_dir / "auto_results.json"
        json_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

        html_path = output_dir / "auto_report.html"
        html_path.write_text(generate_html_report(report_data), encoding="utf-8")

        result["json_report"] = str(json_path)
        result["html_report"] = str(html_path)
        return result
