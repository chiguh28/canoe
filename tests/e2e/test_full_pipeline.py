"""全フェーズ通し E2E テスト

Phase 1（信号読込） → Phase 2（パターン作成・変換）
→ Phase 3（テスト実行） → Phase 4（判定・帳票出力）
の一連のワークフローを検証する。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.converter.batch_converter import BatchConverter
from src.engine.judgment import (
    JudgmentCriteria,
    JudgmentEngine,
    JudgmentResult,
    JudgmentType,
)
from src.engine.log_manager import LogEntry, LogManager
from src.engine.test_runner import ExecutionSummary, TestRunner
from src.models.signal_model import SignalRepository
from src.models.test_pattern import TestPattern
from src.parsers.dbc_parser import DBCParser
from src.parsers.ldf_parser import LDFParser
from src.report.excel_report import ExcelReportGenerator

from .conftest import MockCANoeCOM, MockOpenAIConverter


@pytest.mark.e2e
class TestFullPipeline:
    """E2E-N01: 全フェーズ通しテスト"""

    def test_full_workflow(
        self,
        signal_repository: SignalRepository,
        mock_canoe: MockCANoeCOM,
        mock_converter: MockOpenAIConverter,
        tmp_path: Path,
    ) -> None:
        """DBC/LDF 読込 → パターン作成 → 変換 → 実行 → 判定 → 帳票"""
        # --- Phase 1: 信号読込 ---
        assert signal_repository.count > 0

        # --- Phase 2: テストパターン作成・変換 ---
        patterns = [
            TestPattern(
                test_case_id="TC-001",
                test_case_name="エンジン回転数テスト",
                target_signal="EngineSpeed",
                operation="エンジン回転数を 2000rpm に設定",
                expected_value="スロットル開度が 20% 以上",
                wait_time_ms=100,
            ),
        ]

        batch = BatchConverter(converter=mock_converter)
        previews = batch.convert_all(patterns)
        assert len(previews) == 1
        assert previews[0].success is True

        confirmed = batch.confirm_all()
        assert len(confirmed) == 1

        export_path = tmp_path / "confirmed.json"
        batch.export_confirmed(export_path)
        assert export_path.exists()

        # --- Phase 3: テスト実行 ---
        runner = TestRunner(com_wrapper=mock_canoe)
        summary = runner.execute(patterns, config_file="test.cfg")

        assert summary.total == 1
        assert isinstance(summary, ExecutionSummary)
        assert len(summary.results) == 1

        # --- Phase 3.5: ログ作成（判定用） ---
        log_mgr = LogManager(log_dir=tmp_path / "logs")
        log_mgr.start_log("TC-001")
        log_mgr.add_entry(
            "TC-001",
            LogEntry(
                timestamp=0.0,
                channel=1,
                message_name="EngineData",
                signal_name="ThrottlePosition",
                value=22.5,
            ),
        )
        test_log = log_mgr.end_log("TC-001")

        # --- Phase 4: 判定 ---
        engine = JudgmentEngine()
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.RANGE,
            signal_name="ThrottlePosition",
            range_min=20.0,
            range_max=100.0,
        )
        detail = engine.judge("TC-001", test_log, criteria)
        assert detail.result == JudgmentResult.OK

        # --- Phase 4: 帳票出力 ---
        report_path = tmp_path / "report.xlsx"
        generator = ExcelReportGenerator()
        result_path = generator.generate(
            summary=summary,
            judgments=[detail],
            output_path=report_path,
            config_file="test.cfg",
        )
        assert result_path.exists()
        assert result_path.suffix == ".xlsx"

    def test_multi_file_mixed(
        self,
        sample_dbc_path: Path,
        sample_ldf_path: Path,
        mock_canoe: MockCANoeCOM,
        tmp_path: Path,
    ) -> None:
        """E2E-N02: CAN/LIN 混合テスト"""
        # DBC + LDF を個別にパース → SignalRepository にマージ
        repo = SignalRepository()
        dbc_signals = DBCParser().parse(sample_dbc_path)
        ldf_signals = LDFParser().parse(sample_ldf_path)

        repo.add_signals(dbc_signals)
        repo.add_signals(ldf_signals)

        assert repo.count > 0
        assert len(dbc_signals) > 0
        assert len(ldf_signals) > 0

        # CAN/LIN 両方の信号が含まれること
        from src.models.signal_model import Protocol

        can_signals = repo.filter_by_protocol(Protocol.CAN)
        lin_signals = repo.filter_by_protocol(Protocol.LIN)
        assert len(can_signals) > 0
        assert len(lin_signals) > 0

        # 混合パターン作成 → 実行
        patterns = [
            TestPattern(
                test_case_id="TC-MIX-001",
                test_case_name="CAN信号テスト",
                target_signal="CAN_Signal",
                operation="CAN 信号を設定",
                expected_value="応答あり",
                wait_time_ms=50,
            ),
            TestPattern(
                test_case_id="TC-MIX-002",
                test_case_name="LIN信号テスト",
                target_signal="LIN_Signal",
                operation="LIN 信号を設定",
                expected_value="応答あり",
                wait_time_ms=50,
            ),
        ]

        runner = TestRunner(com_wrapper=mock_canoe)
        summary = runner.execute(patterns)
        assert summary.total == 2
        assert len(summary.results) == 2

    def test_large_batch_execution(
        self,
        mock_canoe: MockCANoeCOM,
        tmp_path: Path,
    ) -> None:
        """E2E-N08: 大量パターン実行（50件）"""
        patterns = [
            TestPattern(
                test_case_id=f"TC-BATCH-{i:03d}",
                test_case_name=f"バッチテスト {i}",
                target_signal=f"Signal_{i}",
                operation=f"信号 {i} を設定",
                expected_value=f"期待値 {i}",
                wait_time_ms=0,
            )
            for i in range(1, 51)
        ]

        # 進捗コールバックの検証
        progress_log: list[tuple[int, int, str]] = []

        def on_progress(current: int, total: int, name: str) -> None:
            progress_log.append((current, total, name))

        runner = TestRunner(com_wrapper=mock_canoe)
        runner.set_progress_callback(on_progress)
        summary = runner.execute(patterns)

        assert summary.total == 50
        assert len(summary.results) == 50
        assert len(progress_log) == 50
        # 進捗が正しく 1/50 → 50/50 まで通知されること
        assert progress_log[0][0] == 1
        assert progress_log[0][1] == 50
        assert progress_log[-1][0] == 50
