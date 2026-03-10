"""結果・帳票タブのテスト

テスト結果表示、Excel帳票出力のテスト。
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.engine.judgment import JudgmentDetail, JudgmentResult, JudgmentType
from src.engine.test_runner import ExecutionSummary, TestResult, TestStatus
from src.gui.report_tab import ReportTab


@pytest.fixture
def mock_parent():
    return MagicMock()


@pytest.fixture
def sample_summary():
    return ExecutionSummary(
        total=3,
        passed=2,
        failed=1,
        start_time="2026-03-10T10:00:00",
        end_time="2026-03-10T10:01:00",
        config_file="test.cfg",
        results=[
            TestResult("TC-001", "テスト1", TestStatus.PASSED,
                       actual_value="3000", expected_value="3000"),
            TestResult("TC-002", "テスト2", TestStatus.PASSED,
                       actual_value="60", expected_value="60"),
            TestResult("TC-003", "テスト3", TestStatus.FAILED,
                       actual_value="5", expected_value="3"),
        ],
    )


@pytest.fixture
def sample_judgments():
    return [
        JudgmentDetail("TC-001", JudgmentResult.OK, JudgmentType.EXACT,
                       "EngineSpeed", "3000", "3000", "0"),
        JudgmentDetail("TC-002", JudgmentResult.OK, JudgmentType.RANGE,
                       "Speed", "50~70", "60"),
        JudgmentDetail("TC-003", JudgmentResult.NG, JudgmentType.EXACT,
                       "CurrentGear", "3", "5", "2"),
    ]


class TestReportTab:
    """結果・帳票タブのテスト"""

    def test_creation(self, mock_parent):
        tab = ReportTab(mock_parent)
        assert tab.summary is None
        assert tab.judgments == []

    def test_set_results(self, mock_parent, sample_summary, sample_judgments):
        tab = ReportTab(mock_parent)
        tab.set_results(sample_summary, sample_judgments)
        assert tab.summary is sample_summary
        assert len(tab.judgments) == 3

    def test_result_to_row(self, mock_parent, sample_summary):
        tab = ReportTab(mock_parent)
        result = sample_summary.results[0]
        row = tab.result_to_row(result)
        assert row[0] == "TC-001"
        assert row[1] == "テスト1"
        assert "passed" in row[5].lower() or row[5] == "passed"

    def test_generate_report_without_results(self, mock_parent, tmp_path):
        tab = ReportTab(mock_parent)
        with pytest.raises(ValueError, match="結果"):
            tab.generate_report(tmp_path / "report.xlsx")

    def test_generate_report(self, mock_parent, sample_summary, sample_judgments, tmp_path):
        try:
            import openpyxl  # noqa: F401
        except ImportError:
            pytest.skip("openpyxl not installed")

        tab = ReportTab(mock_parent)
        tab.set_results(sample_summary, sample_judgments)
        report_path = tab.generate_report(tmp_path / "report.xlsx")
        assert report_path.exists()
        assert report_path.suffix == ".xlsx"

    def test_get_statistics(self, mock_parent, sample_summary, sample_judgments):
        tab = ReportTab(mock_parent)
        tab.set_results(sample_summary, sample_judgments)
        stats = tab.get_statistics()
        assert stats["total"] == 3
        assert stats["passed"] == 2
        assert stats["failed"] == 1
        assert stats["pass_rate"] == pytest.approx(66.67, abs=0.01)

    def test_clear_results(self, mock_parent, sample_summary, sample_judgments):
        tab = ReportTab(mock_parent)
        tab.set_results(sample_summary, sample_judgments)
        tab.clear_results()
        assert tab.summary is None
        assert tab.judgments == []
