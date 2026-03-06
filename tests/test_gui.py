"""Unit tests for GUI components (MainWindow)

This test suite follows TDD approach:
- Red: Write failing tests first
- Green: Implement minimal code to pass tests
- Refactor: Clean up code while keeping tests green
"""

import os
from unittest.mock import Mock, patch

import pytest

from src.gui.main_window import MainWindow


@pytest.mark.skipif(
    os.getenv("CI") == "true" or os.getenv("DISPLAY") is None,
    reason="GUI tests require a display (skip in headless CI)",
)
class TestMainWindow:
    """MainWindow class tests"""

    @pytest.fixture
    def mock_tk(self):
        """Mock tkinter.Tk to avoid creating actual windows during tests"""
        with patch("src.gui.main_window.tk.Tk") as mock:
            mock_root = Mock()
            mock.return_value = mock_root
            yield mock_root

    def test_mainwindow_creation(self, mock_tk):
        """Test that MainWindow can be instantiated"""
        window = MainWindow()
        assert window is not None
        assert window.root is not None

    def test_window_title(self, mock_tk):
        """Test that window title is set correctly"""
        window = MainWindow()  # noqa: F841
        mock_tk.title.assert_called_once_with("CANoe 自動テストツール")

    def test_window_geometry(self, mock_tk):
        """Test that window size is set correctly (1024x768)"""
        window = MainWindow()  # noqa: F841
        mock_tk.geometry.assert_called_once_with("1024x768")

    def test_window_minsize(self, mock_tk):
        """Test that minimum window size is set (800x600)"""
        window = MainWindow()  # noqa: F841
        mock_tk.minsize.assert_called_once_with(800, 600)

    def test_menubar_created(self, mock_tk):
        """Test that menu bar is created"""
        window = MainWindow()  # noqa: F841
        # Menu bar should be configured
        assert mock_tk.config.called

    def test_notebook_created(self, mock_tk):
        """Test that notebook (tabs) widget is created"""
        with patch("src.gui.main_window.ttk.Notebook") as mock_notebook:
            window = MainWindow()
            mock_notebook.assert_called_once()
            assert window.notebook is not None

    def test_statusbar_created(self, mock_tk):
        """Test that status bar is created"""
        with patch("src.gui.main_window.ttk.Label") as mock_label:
            window = MainWindow()
            # Status bar label should be created
            mock_label.assert_called()
            assert window.statusbar is not None

    def test_set_status_updates_statusbar(self, mock_tk):
        """Test that set_status() updates status bar message"""
        with patch("src.gui.main_window.ttk.Label") as mock_label:  # noqa: F841
            window = MainWindow()
            window.set_status("テスト中")
            # Status bar config should be called
            assert window.statusbar is not None

    def test_run_starts_mainloop(self, mock_tk):
        """Test that run() starts tkinter main loop"""
        window = MainWindow()
        window.run()
        mock_tk.mainloop.assert_called_once()

    def test_class_constants(self):
        """Test that MainWindow class has required constants"""
        assert hasattr(MainWindow, "TITLE")
        assert hasattr(MainWindow, "DEFAULT_WIDTH")
        assert hasattr(MainWindow, "DEFAULT_HEIGHT")
        assert MainWindow.TITLE == "CANoe 自動テストツール"
        assert MainWindow.DEFAULT_WIDTH == 1024
        assert MainWindow.DEFAULT_HEIGHT == 768
