"""Pytest configuration and fixtures"""

import sys
from unittest.mock import MagicMock

# Mock tkinter if not available (e.g., on headless Linux)
try:
    import tkinter  # noqa: F401
except ModuleNotFoundError:
    # Create a mock tkinter module
    tkinter_mock = MagicMock()
    sys.modules["tkinter"] = tkinter_mock
    sys.modules["tkinter.ttk"] = MagicMock()
