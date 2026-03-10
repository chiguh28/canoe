"""Pytest configuration and fixtures"""

import os
import sys
from unittest.mock import MagicMock

# Determine if we're in a headless environment
is_headless = not os.environ.get("DISPLAY")

# Mock tkinter in headless environments (CI) or when tkinter is not available
if is_headless or "tkinter" not in sys.modules:
    try:
        import tkinter  # noqa: F401

        # tkinter is installed but we're headless - need to replace it with mock
        if is_headless:
            # Create a mock tkinter module with proper constants
            tkinter_mock = MagicMock()

            # Define tkinter constants to avoid arithmetic errors with Mock objects
            tkinter_mock.BOTH = "both"
            tkinter_mock.TOP = "top"
            tkinter_mock.BOTTOM = "bottom"
            tkinter_mock.LEFT = "left"
            tkinter_mock.RIGHT = "right"
            tkinter_mock.X = "x"
            tkinter_mock.Y = "y"
            tkinter_mock.W = "w"
            tkinter_mock.E = "e"
            tkinter_mock.N = "n"
            tkinter_mock.S = "s"
            tkinter_mock.NW = "nw"
            tkinter_mock.NE = "ne"
            tkinter_mock.SW = "sw"
            tkinter_mock.SE = "se"
            tkinter_mock.CENTER = "center"
            tkinter_mock.SUNKEN = "sunken"
            tkinter_mock.RAISED = "raised"
            tkinter_mock.FLAT = "flat"
            tkinter_mock.RIDGE = "ridge"
            tkinter_mock.GROOVE = "groove"
            tkinter_mock.SOLID = "solid"

            # Mock variable classes (StringVar, IntVar, etc.)
            class MockVar:
                """Mock for tkinter variable classes"""

                def __init__(self, master: object = None, value: object = None) -> None:
                    self._value = value if value is not None else ""

                def get(self) -> object:
                    return self._value

                def set(self, value: object) -> None:
                    self._value = value

                def trace_add(self, *args: object, **kwargs: object) -> str:
                    return "mock_trace_id"

                def trace_remove(self, *args: object, **kwargs: object) -> None:
                    pass

            tkinter_mock.StringVar = MockVar
            tkinter_mock.IntVar = MockVar
            tkinter_mock.BooleanVar = MockVar
            tkinter_mock.DoubleVar = MockVar

            # Mock Tk root window
            tkinter_mock.Tk = MagicMock

            sys.modules["tkinter"] = tkinter_mock
            sys.modules["tkinter.ttk"] = MagicMock()
    except ModuleNotFoundError:
        # tkinter not installed - create mock
        tkinter_mock = MagicMock()

        # Define tkinter constants
        tkinter_mock.BOTH = "both"
        tkinter_mock.TOP = "top"
        tkinter_mock.BOTTOM = "bottom"
        tkinter_mock.LEFT = "left"
        tkinter_mock.RIGHT = "right"
        tkinter_mock.X = "x"
        tkinter_mock.Y = "y"
        tkinter_mock.W = "w"
        tkinter_mock.E = "e"
        tkinter_mock.N = "n"
        tkinter_mock.S = "s"
        tkinter_mock.NW = "nw"
        tkinter_mock.NE = "ne"
        tkinter_mock.SW = "sw"
        tkinter_mock.SE = "se"
        tkinter_mock.CENTER = "center"
        tkinter_mock.SUNKEN = "sunken"
        tkinter_mock.RAISED = "raised"
        tkinter_mock.FLAT = "flat"
        tkinter_mock.RIDGE = "ridge"
        tkinter_mock.GROOVE = "groove"
        tkinter_mock.SOLID = "solid"

        # Mock variable classes
        class MockVar:
            """Mock for tkinter variable classes"""

            def __init__(self, master: object = None, value: object = None) -> None:
                self._value = value if value is not None else ""

            def get(self) -> object:
                return self._value

            def set(self, value: object) -> None:
                self._value = value

            def trace_add(self, *args: object, **kwargs: object) -> str:
                return "mock_trace_id"

            def trace_remove(self, *args: object, **kwargs: object) -> None:
                pass

        tkinter_mock.StringVar = MockVar
        tkinter_mock.IntVar = MockVar
        tkinter_mock.BooleanVar = MockVar
        tkinter_mock.DoubleVar = MockVar
        tkinter_mock.Tk = MagicMock

        sys.modules["tkinter"] = tkinter_mock
        sys.modules["tkinter.ttk"] = MagicMock()
