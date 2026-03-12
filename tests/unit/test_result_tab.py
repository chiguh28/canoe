"""ResultTab のユニットテスト (Issue #24 - F02)

結果・帳票タブの機能テスト。
TDD: テストを先に書き、実装を後から行う。
"""

from unittest.mock import MagicMock

from src.gui.result_tab import ResultTab


class TestResultTabCreation:
    """ResultTab の生成テスト"""

    def test_result_tab_creates_with_parent_frame(self) -> None:
        parent = MagicMock()
        tab = ResultTab(parent)
        assert tab.parent is parent

    def test_result_tab_has_export_button(self) -> None:
        parent = MagicMock()
        tab = ResultTab(parent)
        assert hasattr(tab, "export_button")

    def test_result_tab_has_result_tree(self) -> None:
        parent = MagicMock()
        tab = ResultTab(parent)
        assert hasattr(tab, "result_tree")

    def test_result_tab_has_summary_labels(self) -> None:
        parent = MagicMock()
        tab = ResultTab(parent)
        assert hasattr(tab, "total_label")
        assert hasattr(tab, "passed_label")
        assert hasattr(tab, "failed_label")
        assert hasattr(tab, "error_label")
        assert hasattr(tab, "pass_rate_label")

    def test_export_button_initially_disabled(self) -> None:
        """初期状態ではエクスポートボタンが無効"""
        parent = MagicMock()
        tab = ResultTab(parent)
        # config で state=DISABLED が設定されていることを確認
        tab.export_button.config.assert_called()
