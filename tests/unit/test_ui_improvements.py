"""UI改善テスト (Issue #24)

エラーメッセージの日本語化、キーボードショートカット、
ステータスバー更新、操作フロー改善のテスト。
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.gui.error_messages import ErrorMessages
from src.gui.keyboard_shortcuts import KeyboardShortcutManager


class TestErrorMessages:
    """日本語エラーメッセージのテスト"""

    def test_file_not_found_message(self):
        msg = ErrorMessages.file_not_found("test.dbc")
        assert "test.dbc" in msg
        assert "見つかりません" in msg

    def test_unsupported_format_message(self):
        msg = ErrorMessages.unsupported_format(".xyz")
        assert ".xyz" in msg
        assert "サポート" in msg

    def test_parse_error_message(self):
        msg = ErrorMessages.parse_error("test.dbc", "invalid syntax")
        assert "test.dbc" in msg
        assert "解析" in msg or "パース" in msg

    def test_connection_error_message(self):
        msg = ErrorMessages.connection_error("CANoe が見つかりません")
        assert "接続" in msg

    def test_no_patterns_message(self):
        msg = ErrorMessages.no_patterns()
        assert "テストパターン" in msg

    def test_execution_error_message(self):
        msg = ErrorMessages.execution_error("TC-001", "timeout")
        assert "TC-001" in msg
        assert "実行" in msg

    def test_save_error_message(self):
        msg = ErrorMessages.save_error("/tmp/report.xlsx", "permission denied")
        assert "保存" in msg

    def test_all_messages_are_strings(self):
        """全メソッドが文字列を返す"""
        assert isinstance(ErrorMessages.file_not_found("f"), str)
        assert isinstance(ErrorMessages.unsupported_format(".x"), str)
        assert isinstance(ErrorMessages.parse_error("f", "e"), str)
        assert isinstance(ErrorMessages.connection_error("e"), str)
        assert isinstance(ErrorMessages.no_patterns(), str)
        assert isinstance(ErrorMessages.execution_error("id", "e"), str)
        assert isinstance(ErrorMessages.save_error("p", "e"), str)


class TestKeyboardShortcutManager:
    """キーボードショートカットマネージャのテスト"""

    def test_register_shortcut(self):
        mgr = KeyboardShortcutManager()
        callback = MagicMock()
        mgr.register("Ctrl+O", "ファイルを開く", callback)
        assert "Ctrl+O" in mgr.get_shortcuts()

    def test_get_description(self):
        mgr = KeyboardShortcutManager()
        callback = MagicMock()
        mgr.register("Ctrl+O", "ファイルを開く", callback)
        assert mgr.get_description("Ctrl+O") == "ファイルを開く"

    def test_get_all_shortcuts(self):
        mgr = KeyboardShortcutManager()
        mgr.register("Ctrl+O", "ファイルを開く", MagicMock())
        mgr.register("Ctrl+S", "保存", MagicMock())
        mgr.register("Ctrl+Q", "終了", MagicMock())
        shortcuts = mgr.get_shortcuts()
        assert len(shortcuts) == 3

    def test_get_shortcut_list_formatted(self):
        """ショートカット一覧のフォーマット表示"""
        mgr = KeyboardShortcutManager()
        mgr.register("Ctrl+O", "ファイルを開く", MagicMock())
        mgr.register("Ctrl+Q", "終了", MagicMock())
        formatted = mgr.get_formatted_list()
        assert "Ctrl+O" in formatted
        assert "ファイルを開く" in formatted

    def test_unregister_shortcut(self):
        mgr = KeyboardShortcutManager()
        mgr.register("Ctrl+O", "ファイルを開く", MagicMock())
        mgr.unregister("Ctrl+O")
        assert "Ctrl+O" not in mgr.get_shortcuts()

    def test_default_shortcuts(self):
        """デフォルトショートカットの定義"""
        defaults = KeyboardShortcutManager.get_default_shortcuts()
        assert isinstance(defaults, dict)
        assert len(defaults) > 0
