"""Regression tests for HTML report generation, in particular output escaping.

Crawl reports embed raw URLs and error text pulled from external, possibly
untrusted pages. Before this fix, generate_html_report() interpolated test
name/message/traceback directly into the page with no escaping, so a crawled
page containing e.g. "<script>...</script>" in its title/error would inject
markup into a report that gets opened straight in a browser.
"""

import unittest

from autoscope.reporting.html import generate_html_report


def _report_with(name: str, message: str, traceback_str: str = "") -> str:
    data = {
        "duration_seconds": 1.23,
        "summary": {"total": 1, "passed": 0, "failed": 1, "errors": 0, "skipped": 0},
        "tests": [
            {
                "name": name,
                "status": "failed",
                "message": message,
                "traceback": traceback_str,
            }
        ],
    }
    return generate_html_report(data)


class TestHtmlReportEscaping(unittest.TestCase):
    def test_script_tag_in_name_is_escaped(self) -> None:
        html_out = _report_with("<script>alert(1)</script>", "ok")
        self.assertNotIn("<script>alert(1)</script>", html_out)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html_out)

    def test_script_tag_in_message_is_escaped(self) -> None:
        html_out = _report_with("normal test", "<img src=x onerror=alert(1)>")
        self.assertNotIn("<img src=x onerror=alert(1)>", html_out)
        self.assertIn("&lt;img", html_out)

    def test_script_tag_in_traceback_is_escaped(self) -> None:
        html_out = _report_with("normal test", "boom", "<script>evil()</script>")
        self.assertNotIn("<script>evil()</script>", html_out)
        self.assertIn("&lt;script&gt;evil()&lt;/script&gt;", html_out)

    def test_ampersand_and_quotes_are_escaped(self) -> None:
        html_out = _report_with("A & B \"quoted\"", "it's <ok>")
        self.assertIn("A &amp; B", html_out)
        self.assertNotIn("<ok>", html_out)


class TestHtmlReportSummary(unittest.TestCase):
    def test_summary_counts_and_duration_appear(self) -> None:
        data = {
            "duration_seconds": 4.5,
            "summary": {"total": 4, "passed": 2, "failed": 1, "errors": 1, "skipped": 0},
            "tests": [],
        }
        html_out = generate_html_report(data)
        self.assertIn("Passed: 2", html_out)
        self.assertIn("Failed: 1", html_out)
        self.assertIn("Errors: 1", html_out)
        self.assertIn("Skipped: 0", html_out)
        self.assertIn("4.50 seconds", html_out)

    def test_passing_row_has_no_traceback_block(self) -> None:
        data = {
            "duration_seconds": 0.1,
            "summary": {"total": 1, "passed": 1, "failed": 0, "errors": 0, "skipped": 0},
            "tests": [{"name": "test_ok", "status": "passed", "message": None, "traceback": None}],
        }
        html_out = generate_html_report(data)
        self.assertNotIn("<pre>", html_out)


if __name__ == "__main__":
    unittest.main()
