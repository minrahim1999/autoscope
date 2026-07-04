"""unittest TestResult that records JSON-serializable results."""

import traceback
import unittest
from typing import Any, Dict, List


class JSONTestResult(unittest.TestResult):
    def __init__(self) -> None:
        super().__init__()
        self.results: List[Dict[str, Any]] = []

    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        self.results.append({
            "name": str(test),
            "status": "passed",
            "message": None,
            "traceback": None,
        })

    def addFailure(self, test: unittest.TestCase, err) -> None:
        super().addFailure(test, err)
        self.results.append(self._error_record(test, err, "failed"))

    def addError(self, test: unittest.TestCase, err) -> None:
        super().addError(test, err)
        self.results.append(self._error_record(test, err, "error"))

    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        self.results.append({
            "name": str(test),
            "status": "skipped",
            "message": reason,
            "traceback": None,
        })

    def _error_record(self, test, err, status: str) -> Dict[str, Any]:
        exctype, value, tb = err
        return {
            "name": str(test),
            "status": status,
            "message": str(value),
            "traceback": "\n".join(traceback.format_exception(exctype, value, tb)),
        }

    def to_dict(self, duration: float) -> Dict[str, Any]:
        passed = sum(1 for r in self.results if r["status"] == "passed")
        failed = sum(1 for r in self.results if r["status"] == "failed")
        errors = sum(1 for r in self.results if r["status"] == "error")
        skipped = sum(1 for r in self.results if r["status"] == "skipped")
        return {
            "duration_seconds": duration,
            "summary": {
                "total": len(self.results),
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "skipped": skipped,
            },
            "tests": self.results,
        }
