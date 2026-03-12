"""異常系・回復 E2E テスト

エラー発生時の適切なハンドリングと復旧を検証する。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.engine.canoe_com import CANoeError
from src.engine.judgment import (
    JudgmentCriteria,
    JudgmentEngine,
    JudgmentResult,
    JudgmentType,
)
from src.engine.log_manager import TestLog
from src.engine.test_runner import TestRunner, TestStatus
from src.models.test_pattern import TestPattern
from src.parsers.dbc_parser import DBCParseError, DBCParser
from src.parsers.ldf_parser import LDFParseError, LDFParser
from src.report.excel_report import ExcelReportGenerator

from .conftest import (
    ERROR_FIXTURES_DIR,
    MockCANoeCOM,
    MockCANoeCOMDisconnecting,
    MockCANoeCOMFailing,
)


@pytest.mark.e2e
class TestFileErrors:
    """E2E-E01: ファイル読込エラー"""

    def test_corrupted_dbc(self) -> None:
        """破損 DBC ファイルの読み込み"""
        corrupted_path = ERROR_FIXTURES_DIR / "corrupted.dbc"
        parser = DBCParser()
        with pytest.raises(DBCParseError):
            parser.parse(corrupted_path)

    def test_empty_ldf(self) -> None:
        """空 LDF ファイルの読み込み"""
        empty_path = ERROR_FIXTURES_DIR / "empty.ldf"
        parser = LDFParser()
        with pytest.raises(LDFParseError):
            parser.parse(empty_path)

    def test_nonexistent_file(self) -> None:
        """存在しないファイルの読み込み"""
        parser = DBCParser()
        with pytest.raises(DBCParseError):
            parser.parse(Path("/nonexistent/file.dbc"))

        ldf_parser = LDFParser()
        with pytest.raises(LDFParseError):
            ldf_parser.parse(Path("/nonexistent/file.ldf"))


@pytest.mark.e2e
class TestExecutionErrors:
    """E2E-E04〜E07: 実行エラー"""

    def test_canoe_connection_failure(self) -> None:
        """E2E-E04: CANoe 接続失敗"""
        failing_com = MockCANoeCOMFailing()
        with pytest.raises(CANoeError, match="接続失敗"):
            failing_com.connect()

    def test_canoe_disconnect_during_measurement(self) -> None:
        """E2E-E05: 測定中の CANoe 切断"""
        disconnecting_com = MockCANoeCOMDisconnecting()
        disconnecting_com.connect()
        disconnecting_com.start_measurement()

        with pytest.raises(CANoeError, match="切断"):
            disconnecting_com.stop_measurement()

    def test_abort_during_execution(
        self,
        mock_canoe: MockCANoeCOM,
    ) -> None:
        """E2E-E06: 実行中断"""
        patterns = [
            TestPattern(
                test_case_id=f"TC-ABORT-{i:03d}",
                test_case_name=f"中断テスト {i}",
                operation=f"操作 {i}",
                expected_value=f"期待値 {i}",
                wait_time_ms=0,
            )
            for i in range(1, 6)
        ]

        runner = TestRunner(com_wrapper=mock_canoe)

        # 2件目実行後に中断を要求
        call_count = 0

        def on_progress(current: int, total: int, name: str) -> None:
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                runner.abort()

        runner.set_progress_callback(on_progress)
        summary = runner.execute(patterns)

        assert summary.total == 5
        # 最初の2件は実行済み、残りは ABORTED
        executed = [r for r in summary.results if r.status != TestStatus.ABORTED]
        aborted = [r for r in summary.results if r.status == TestStatus.ABORTED]
        assert len(executed) >= 1  # 少なくとも1件は実行済み
        assert len(aborted) >= 1  # 少なくとも1件は中断
        assert summary.aborted >= 1

    def test_invalid_test_pattern_empty_signal(
        self,
        mock_canoe: MockCANoeCOM,
    ) -> None:
        """E2E-E07: 空の信号名のテストパターン"""
        patterns = [
            TestPattern(
                test_case_id="TC-INVALID",
                test_case_name="",
                target_signal="",
                operation="",
                expected_value="",
                wait_time_ms=0,
            ),
        ]

        runner = TestRunner(com_wrapper=mock_canoe)
        summary = runner.execute(patterns)

        # 空パターンでもエラーにならず実行される（COMが何もしないため）
        assert summary.total == 1
        assert len(summary.results) == 1

    def test_runner_without_com(self) -> None:
        """CANoe COM なしでの TestRunner 実行 → SKIPPED"""
        patterns = [
            TestPattern(
                test_case_id="TC-NOCOM",
                test_case_name="COM なしテスト",
                operation="操作",
                expected_value="期待値",
                wait_time_ms=0,
            ),
        ]

        runner = TestRunner(com_wrapper=None)
        summary = runner.execute(patterns)

        assert summary.total == 1
        assert summary.skipped == 1
        assert summary.results[0].status == TestStatus.SKIPPED
        assert "COM API" in summary.results[0].error_message


@pytest.mark.e2e
class TestJudgmentErrors:
    """判定エラー系テスト"""

    def test_no_log_entries(self) -> None:
        """ログエントリなしでの判定 → ERROR"""
        engine = JudgmentEngine()
        empty_log = TestLog(test_case_id="TC-EMPTY", entries=[])

        result = engine.judge(
            "TC-EMPTY",
            empty_log,
            JudgmentCriteria(
                judgment_type=JudgmentType.EXACT,
                signal_name="MissingSig",
                expected_value=100.0,
            ),
        )
        assert result.result == JudgmentResult.ERROR
        assert "見つかりません" in result.reason

    def test_exact_judgment_ng(self) -> None:
        """EXACT 判定 NG（値不一致）"""
        from src.engine.log_manager import LogEntry

        engine = JudgmentEngine()
        log = TestLog(
            test_case_id="TC-NG",
            entries=[LogEntry(0.0, 1, "Msg", "Sig", 50.0)],
        )
        result = engine.judge(
            "TC-NG",
            log,
            JudgmentCriteria(
                judgment_type=JudgmentType.EXACT,
                signal_name="Sig",
                expected_value=100.0,
                tolerance=0.0,
            ),
        )
        assert result.result == JudgmentResult.NG
        assert "差異" in result.reason

    def test_range_judgment_ng(self) -> None:
        """RANGE 判定 NG（範囲外）"""
        from src.engine.log_manager import LogEntry

        engine = JudgmentEngine()
        log = TestLog(
            test_case_id="TC-RANGE-NG",
            entries=[LogEntry(0.0, 1, "Msg", "Temp", 75.3)],
        )
        result = engine.judge(
            "TC-RANGE-NG",
            log,
            JudgmentCriteria(
                judgment_type=JudgmentType.RANGE,
                signal_name="Temp",
                range_min=80.0,
                range_max=100.0,
            ),
        )
        assert result.result == JudgmentResult.NG
        assert "範囲" in result.reason

    def test_compound_judgment_partial_ng(self) -> None:
        """COMPOUND 判定（AND）で一部 NG → 全体 NG"""
        from src.engine.log_manager import LogEntry

        engine = JudgmentEngine()
        log = TestLog(
            test_case_id="TC-COMPOUND-NG",
            entries=[
                LogEntry(0.0, 1, "Msg", "SigA", 100.0),
                LogEntry(0.0, 1, "Msg", "SigB", 200.0),  # 範囲外
            ],
        )
        result = engine.judge(
            "TC-COMPOUND-NG",
            log,
            JudgmentCriteria(
                judgment_type=JudgmentType.COMPOUND,
                signal_name="Compound",
                sub_criteria=[
                    JudgmentCriteria(
                        judgment_type=JudgmentType.EXACT,
                        signal_name="SigA",
                        expected_value=100.0,
                    ),
                    JudgmentCriteria(
                        judgment_type=JudgmentType.RANGE,
                        signal_name="SigB",
                        range_min=0.0,
                        range_max=100.0,
                    ),
                ],
                compound_operator="AND",
            ),
        )
        assert result.result == JudgmentResult.NG


@pytest.mark.e2e
class TestReportErrors:
    """E2E-E08: 帳票出力エラー"""

    def test_invalid_output_directory(self) -> None:
        """存在しない出力先への Excel 出力"""
        from src.engine.test_runner import ExecutionSummary

        gen = ExcelReportGenerator()
        nonexistent = Path("/nonexistent/dir/report.xlsx")

        with pytest.raises((FileNotFoundError, OSError)):
            gen.generate(
                summary=ExecutionSummary(total=0),
                output_path=nonexistent,
            )

    def test_empty_summary_report(self, tmp_path: Path) -> None:
        """空のサマリで帳票出力（エラーにならないこと）"""
        from src.engine.test_runner import ExecutionSummary

        gen = ExcelReportGenerator()
        report_path = tmp_path / "empty_report.xlsx"
        result_path = gen.generate(
            summary=ExecutionSummary(total=0),
            output_path=report_path,
        )
        assert result_path.exists()
