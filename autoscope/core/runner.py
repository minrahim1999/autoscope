"""Test discovery and execution with JSON/HTML reporting."""

import json
import os
import sys
import time
import unittest
from pathlib import Path
from typing import List

from autoscope.config.loader import Config, load_config
from autoscope.reporting.html import generate_html_report
from autoscope.reporting.result import JSONTestResult


def filter_tests_by_tag(suite: unittest.TestSuite, tags: List[str]) -> unittest.TestSuite:
    """Return a new suite containing only tests whose class has one of the tags."""
    filtered = unittest.TestSuite()
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            filtered.addTests(filter_tests_by_tag(test, tags))
        else:
            cls = test.__class__
            test_tags = set(getattr(cls, "tags", ()))
            if not tags or test_tags.intersection(tags):
                filtered.addTest(test)
    return filtered


def run_tests(
    config: Config | None = None,
    start_dir: str = ".",
    pattern: str = "test_*.py",
    tags: List[str] | None = None,
) -> bool:
    """Discover and run tests, then write JSON + HTML reports."""
    config = config or load_config()
    Path(config.runner.output_dir).mkdir(parents=True, exist_ok=True)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir, pattern=pattern)

    if tags:
        suite = filter_tests_by_tag(suite, tags)

    result = JSONTestResult()

    start = time.time()
    suite.run(result)
    duration = time.time() - start

    # Print concise summary mirroring unittest verbosity
    summary = result.to_dict(0)["summary"]
    print(
        f"\nRan {summary['total']} tests: "
        f"{summary['passed']} passed, {summary['failed']} failed, "
        f"{summary['errors']} errors, {summary['skipped']} skipped"
    )
    duration = time.time() - start

    result_data = result.to_dict(duration)
    json_path = Path(config.runner.json_report)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result_data, indent=2), encoding="utf-8")

    html_path = Path(config.runner.html_report)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(generate_html_report(result_data), encoding="utf-8")

    print(f"\nReports written:\n  JSON: {json_path}\n  HTML: {html_path}")
    return result_data["summary"]["failed"] == 0 and result_data["summary"]["errors"] == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
