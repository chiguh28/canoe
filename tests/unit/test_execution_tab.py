"""テスト実行制御UI テスト (Issue #18)"""

from unittest.mock import MagicMock

from src.engine.test_runner import TestRunner
from src.gui.execution_tab import ExecutionTab
from src.models.test_pattern import TestPattern


class TestExecutionTabCreation:
    def test_creates_with_parent(self) -> None:
        parent = MagicMock()
        tab = ExecutionTab(parent)
        assert tab.runner is not None

    def test_creates_with_custom_runner(self) -> None:
        parent = MagicMock()
        runner = TestRunner()
        tab = ExecutionTab(parent, runner=runner)
        assert tab.runner is runner

    def test_has_start_button(self) -> None:
        tab = ExecutionTab(MagicMock())
        assert hasattr(tab, "start_button")

    def test_has_abort_button(self) -> None:
        tab = ExecutionTab(MagicMock())
        assert hasattr(tab, "abort_button")

    def test_has_progress_bar(self) -> None:
        tab = ExecutionTab(MagicMock())
        assert hasattr(tab, "progress_bar")

    def test_has_log_text(self) -> None:
        tab = ExecutionTab(MagicMock())
        assert hasattr(tab, "log_text")


class TestExecutionTabState:
    def test_initial_not_running(self) -> None:
        tab = ExecutionTab(MagicMock())
        assert not tab.is_running

    def test_initial_summary_none(self) -> None:
        tab = ExecutionTab(MagicMock())
        assert tab.summary is None

    def test_set_patterns(self) -> None:
        tab = ExecutionTab(MagicMock())
        patterns = [TestPattern(test_case_id="TC-001")]
        tab.set_patterns(patterns)
        assert len(tab._patterns) == 1

    def test_log_entries_initially_empty(self) -> None:
        tab = ExecutionTab(MagicMock())
        assert tab.log_entries == []


class TestExecutionTabLog:
    def test_add_log(self) -> None:
        tab = ExecutionTab(MagicMock())
        tab._add_log("テストメッセージ")
        assert len(tab.log_entries) == 1
        assert "テストメッセージ" in tab.log_entries[0]
