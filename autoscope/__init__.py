"""AutoScope — minimal web + Android test harness."""

from .core.case import AutomateTestCase
from .core.runner import run_tests
from .config.loader import load_config

__all__ = ["AutomateTestCase", "run_tests", "load_config"]
__version__ = "0.1.0"
