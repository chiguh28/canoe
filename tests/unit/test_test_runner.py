"""テスト実行エンジン テスト (Issue #17)"""

import json
from pathlib import Path
from unittest.mock import MagicMock

from src.engine.test_runner import (
    ExecutionSummary,
    TestResult,
    TestRunner,
    TestStatus,
)
from src.models.test_pattern import TestPattern


class TestTestResult:
    def test_initial_status_pending(self) -> None:
        r = TestResult(test_case_id="TC-001", test_case_name="テスト1")
        assert r.status == TestStatus.PENDING

    def test_to_dict(self) -> None:
        r = TestResult(test_case_id="TC-001", test_case_name="テスト1", status=TestStatus.PASSED)
        d = r.to_dict()
        assert d["status"] == "passed"
        assert d["test_case_id"] == "TC-001"


class TestExecutionSummary:
    def test_pass_rate_all_passed(self) -> None:
        s = ExecutionSummary(total=3, passed=3, failed=0)
        assert s.pass_rate == 100.0

    def test_pass_rate_some_failed(self) -> None:
        s = ExecutionSummary(total=4, passed=3, failed=1)
        assert s.pass_rate == 75.0

    def test_pass_rate_none_executed(self) -> None:
        s = ExecutionSummary(total=0, passed=0, failed=0)
        assert s.pass_rate == 0.0

    def test_total_duration(self) -> None:
        s = ExecutionSummary()
        s.results = [
            TestResult("TC-001", "t1", duration_ms=100.0),
            TestResult("TC-002", "t2", duration_ms=200.0),
        ]
        assert s.total_duration_ms == 300.0


class TestTestRunner:
    def test_execute_empty_list(self) -> None:
        runner = TestRunner()
        summary = runner.execute([])
        assert summary.total == 0
        assert len(summary.results) == 0

    def test_execute_without_com(self) -> None:
        """COM なしで実行すると SKIPPED"""
        runner = TestRunner(com_wrapper=None)
        patterns = [
            TestPattern(test_case_id="TC-001", test_case_name="テスト1"),
        ]
        summary = runner.execute(patterns)
        assert summary.total == 1
        assert summary.skipped == 1
        assert summary.results[0].status == TestStatus.SKIPPED

    def test_execute_with_com(self) -> None:
        """COM ありで実行すると PASSED"""
        mock_com = MagicMock()
        runner = TestRunner(com_wrapper=mock_com)
        patterns = [
            TestPattern(test_case_id="TC-001", test_case_name="テスト1"),
        ]
        summary = runner.execute(patterns)
        assert summary.total == 1
        assert summary.passed == 1

    def test_abort_execution(self) -> None:
        """中断テスト"""
        runner = TestRunner()
        patterns = [
            TestPattern(test_case_id="TC-001", test_case_name="テスト1"),
            TestPattern(test_case_id="TC-002", test_case_name="テスト2"),
        ]
        # 進捗コールバックで最初のパターン実行後に中断要求
        def abort_after_first(current: int, total: int, name: str) -> None:
            if current == 1:
                runner.abort()

        runner.set_progress_callback(abort_after_first)
        mock_com = MagicMock()
        runner._com = mock_com
        summary = runner.execute(patterns)
        assert summary.passed == 1
        assert summary.aborted == 1

    def test_progress_callback(self) -> None:
        """進捗コールバック"""
        callback = MagicMock()
        runner = TestRunner()
        runner.set_progress_callback(callback)
        patterns = [
            TestPattern(test_case_id="TC-001", test_case_name="テスト1"),
        ]
        runner.execute(patterns)
        callback.assert_called_once_with(1, 1, "テスト1")

    def test_get_results(self) -> None:
        runner = TestRunner()
        patterns = [TestPattern(test_case_id="TC-001", test_case_name="テスト1")]
        runner.execute(patterns)
        results = runner.get_results()
        assert len(results) == 1

    def test_save_results_json(self, tmp_path: Path) -> None:
        runner = TestRunner()
        summary = ExecutionSummary(total=1, passed=1)
        summary.results = [
            TestResult("TC-001", "テスト1", status=TestStatus.PASSED),
        ]

        json_file = tmp_path / "results.json"
        runner.save_results_json(json_file, summary)

        data = json.loads(json_file.read_text())
        assert data["total"] == 1
        assert data["passed"] == 1

    def test_execute_multiple_patterns(self) -> None:
        mock_com = MagicMock()
        runner = TestRunner(com_wrapper=mock_com)
        patterns = [
            TestPattern(test_case_id=f"TC-{i:03d}", test_case_name=f"テスト{i}")
            for i in range(1, 6)
        ]
        summary = runner.execute(patterns)
        assert summary.total == 5
        assert summary.passed == 5
        assert len(summary.results) == 5
