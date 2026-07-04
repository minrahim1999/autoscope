"""Generate a simple HTML report from JSON result data."""

import html
from string import Template
from typing import Any, Dict


_HTML = Template("""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>AutoScope Report</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; margin: 2rem; color: #222; }
    h1 { margin-bottom: 0.25rem; }
    .summary { display: flex; gap: 1rem; margin: 1rem 0; }
    .pill { padding: 0.5rem 1rem; border-radius: 999px; font-weight: 600; }
    .passed { background: #d1fae5; color: #065f46; }
    .failed { background: #fee2e2; color: #991b1b; }
    .error { background: #ffedd5; color: #7c2d12; }
    .skipped { background: #e0e7ff; color: #3730a3; }
    table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    th, td { text-align: left; padding: 0.6rem; border-bottom: 1px solid #e5e7eb; }
    th { background: #f9fafb; }
    pre { white-space: pre-wrap; background: #f3f4f6; padding: 0.75rem; border-radius: 0.375rem; }
    .status { text-transform: uppercase; font-size: 0.75rem; font-weight: 700; }
  </style>
</head>
<body>
  <h1>AutoScope Report</h1>
  <p>Duration: $duration seconds</p>
  <div class="summary">
    <span class="pill passed">Passed: $passed</span>
    <span class="pill failed">Failed: $failed</span>
    <span class="pill error">Errors: $errors</span>
    <span class="pill skipped">Skipped: $skipped</span>
  </div>
  <table>
    <thead>
      <tr><th>Test</th><th>Status</th><th>Message</th></tr>
    </thead>
    <tbody>
      $rows
    </tbody>
  </table>
</body>
</html>
""")


def _row(result: Dict[str, Any]) -> str:
    status = result["status"]
    name = html.escape(str(result["name"]))
    msg = html.escape(str(result["message"] or ""))
    detail = ""
    if result.get("traceback"):
        detail = f"<pre>{html.escape(str(result['traceback']))}</pre>"
    return (
        f"<tr>"
        f"<td>{name}</td>"
        f'<td class="status {html.escape(status)}">{html.escape(status)}</td>'
        f'<td>{msg}{detail}</td>'
        f"</tr>"
    )


def generate_html_report(data: Dict[str, Any]) -> str:
    summary = data["summary"]
    rows = "\n".join(_row(r) for r in data["tests"])
    return _HTML.substitute(
        duration=f"{data['duration_seconds']:.2f}",
        passed=summary["passed"],
        failed=summary["failed"],
        errors=summary["errors"],
        skipped=summary["skipped"],
        rows=rows,
    )
