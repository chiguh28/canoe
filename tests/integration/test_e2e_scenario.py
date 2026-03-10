"""E2E シナリオテスト (Issue #23)

完全なワークフローを検証する E2E テスト:
1. DBC/LDF ファイル読込 → 信号情報取得
2. テストパターン作成・保存・読込
3. テスト実行（モック COM）→ ログ記録
4. 判定エンジンによる結果判定
5. Excel 帳票出力
6. 異常系シナリオ（中断、エラーリカバリ）
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.engine.judgment import (
    ChangeDirection,
    JudgmentCriteria,
    JudgmentEngine,
    JudgmentResult,
    JudgmentType,
)
from src.engine.log_manager import LogEntry, LogManager
from src.engine.test_runner import ExecutionSummary, TestRunner, TestStatus
from src.models.signal_model import Protocol, SignalRepository
from src.models.test_pattern import TestPattern, TestPatternRepository
from src.parsers.dbc_parser import DBCParser
from src.parsers.ldf_parser import LDFParser


@pytest.fixture
def sample_dbc_path():
    """サンプル DBC ファイルパス"""
    return Path(__file__).parent.parent / "fixtures" / "sample.dbc"


@pytest.fixture
def sample_ldf_path():
    """サンプル LDF ファイルパス"""
    return Path(__file__).parent.parent / "fixtures" / "sample.ldf"


@pytest.fixture
def signal_repository(sample_dbc_path, sample_ldf_path):
    """DBC/LDF からパースした信号情報を持つリポジトリ"""
    repo = SignalRepository()
    dbc_signals = DBCParser().parse(sample_dbc_path)
    ldf_signals = LDFParser().parse(sample_ldf_path)
    repo.add_signals(dbc_signals)
    repo.add_signals(ldf_signals)
    return repo


@pytest.fixture
def test_patterns():
    """テストパターン一覧"""
    repo = TestPatternRepository()
    repo.add(TestPattern(
        test_case_name="エンジン回転数確認",
        target_signal="EngineSpeed",
        operation="エンジン回転数を3000rpmに設定",
        expected_value="3000",
        precondition="エンジン稼働中",
        wait_time_ms=0,
    ))
    repo.add(TestPattern(
        test_case_name="車速確認",
        target_signal="Speed",
        operation="車速を60km/hに設定",
        expected_value="60",
        precondition="走行モード",
        wait_time_ms=0,
    ))
    repo.add(TestPattern(
        test_case_name="ギア状態確認",
        target_signal="CurrentGear",
        operation="ギアを3速に設定",
        expected_value="3",
        precondition="走行モード",
        wait_time_ms=0,
    ))
    return repo


@pytest.fixture
def mock_com():
    """モック CANoe COM ラッパー"""
    com = MagicMock()
    com.get_signal_value.return_value = 3000.0
    return com


class TestE2EFullWorkflow:
    """完全な E2E ワークフローテスト"""

    def test_parse_to_repository_workflow(self, signal_repository):
        """DBC/LDF パース → リポジトリ格納のワークフロー"""
        # CAN と LIN 両方の信号が格納されている
        assert signal_repository.count > 0
        can_signals = signal_repository.filter_by_protocol(Protocol.CAN)
        lin_signals = signal_repository.filter_by_protocol(Protocol.LIN)
        assert len(can_signals) > 0
        assert len(lin_signals) > 0
        assert signal_repository.count == len(can_signals) + len(lin_signals)

    def test_signal_search_workflow(self, signal_repository):
        """信号検索ワークフロー"""
        results = signal_repository.search("Engine")
        assert len(results) > 0
        for sig in results:
            assert "engine" in sig.signal_name.lower() or "engine" in sig.message_name.lower()

    def test_pattern_create_save_load(self, test_patterns, tmp_path):
        """テストパターン作成 → 保存 → 読込のワークフロー"""
        # 保存
        json_path = tmp_path / "patterns.json"
        test_patterns.save_to_json(json_path)
        assert json_path.exists()

        # 読込
        loaded_repo = TestPatternRepository()
        loaded_repo.load_from_json(json_path)
        assert loaded_repo.count == test_patterns.count

        # 内容確認
        original = test_patterns.get_all()
        loaded = loaded_repo.get_all()
        for orig, load in zip(original, loaded, strict=True):
            assert orig.test_case_id == load.test_case_id
            assert orig.test_case_name == load.test_case_name
            assert orig.target_signal == load.target_signal

    def test_execution_with_mock_com(self, test_patterns, mock_com):
        """モック COM を使ったテスト実行ワークフロー"""
        runner = TestRunner(com_wrapper=mock_com)
        patterns = test_patterns.get_all()

        progress_log = []
        runner.set_progress_callback(
            lambda cur, total, name: progress_log.append((cur, total, name))
        )

        summary = runner.execute(patterns, config_file="test.cfg")

        assert summary.total == 3
        assert summary.passed == 3
        assert summary.failed == 0
        assert summary.pass_rate == 100.0
        assert len(progress_log) == 3
        assert summary.config_file == "test.cfg"

    def test_execution_results_json_save(self, test_patterns, mock_com, tmp_path):
        """テスト実行結果の JSON 保存ワークフロー"""
        runner = TestRunner(com_wrapper=mock_com)
        summary = runner.execute(test_patterns.get_all())

        json_path = tmp_path / "results.json"
        runner.save_results_json(json_path, summary)

        assert json_path.exists()
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["total"] == 3
        assert data["passed"] == 3
        assert len(data["results"]) == 3

    def test_log_and_judgment_workflow(self, tmp_path):
        """ログ記録 → 判定エンジンのワークフロー"""
        # ログ記録
        log_mgr = LogManager(log_dir=tmp_path / "logs")
        log = log_mgr.start_log("TC-001")
        log_mgr.add_entry("TC-001", LogEntry(
            timestamp=0.0, channel=1, message_name="EngineData",
            signal_name="EngineSpeed", value=0.0, direction="Tx",
        ))
        log_mgr.add_entry("TC-001", LogEntry(
            timestamp=0.1, channel=1, message_name="EngineData",
            signal_name="EngineSpeed", value=3000.0, direction="Rx",
        ))
        log_mgr.end_log("TC-001")

        # ログ保存
        csv_path = log_mgr.save_log_csv("TC-001")
        assert csv_path.exists()
        json_path = log_mgr.save_log_json("TC-001")
        assert json_path.exists()

        # 判定 - EXACT
        engine = JudgmentEngine()
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.EXACT,
            signal_name="EngineSpeed",
            expected_value=3000.0,
            tolerance=10.0,
        )
        detail = engine.judge("TC-001", log, criteria)
        assert detail.result == JudgmentResult.OK
        assert detail.actual_value == "3000.0"

    def test_judgment_range_workflow(self, tmp_path):
        """範囲判定ワークフロー"""
        log_mgr = LogManager(log_dir=tmp_path / "logs")
        log_mgr.start_log("TC-002")
        log_mgr.add_entry("TC-002", LogEntry(
            timestamp=0.0, channel=1, message_name="VehicleSpeed",
            signal_name="Speed", value=60.5, direction="Rx",
        ))
        log_mgr.end_log("TC-002")

        engine = JudgmentEngine()
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.RANGE,
            signal_name="Speed",
            range_min=50.0,
            range_max=70.0,
        )
        detail = engine.judge("TC-002", log_mgr.get_log("TC-002"), criteria)
        assert detail.result == JudgmentResult.OK

    def test_judgment_change_workflow(self, tmp_path):
        """変化検知ワークフロー"""
        log_mgr = LogManager(log_dir=tmp_path / "logs")
        log_mgr.start_log("TC-003")
        log_mgr.add_entry("TC-003", LogEntry(
            timestamp=0.0, channel=1, message_name="EngineData",
            signal_name="EngineSpeed", value=1000.0,
        ))
        log_mgr.add_entry("TC-003", LogEntry(
            timestamp=0.5, channel=1, message_name="EngineData",
            signal_name="EngineSpeed", value=3000.0,
        ))
        log_mgr.end_log("TC-003")

        engine = JudgmentEngine()
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.CHANGE,
            signal_name="EngineSpeed",
            change_direction=ChangeDirection.INCREASE,
        )
        detail = engine.judge("TC-003", log_mgr.get_log("TC-003"), criteria)
        assert detail.result == JudgmentResult.OK

    def test_full_pipeline_parse_to_report(
        self, signal_repository, test_patterns, mock_com, tmp_path
    ):
        """完全パイプライン: パース → 実行 → ログ → 判定 → 帳票"""
        # 1. 信号情報は signal_repository に格納済み
        assert signal_repository.count > 0

        # 2. テストパターン取得
        patterns = test_patterns.get_all()
        assert len(patterns) == 3

        # 3. テスト実行
        runner = TestRunner(com_wrapper=mock_com)
        summary = runner.execute(patterns, config_file="test_config.cfg")
        assert summary.total == 3

        # 4. ログ記録（テスト実行のシミュレーション）
        log_mgr = LogManager(log_dir=tmp_path / "logs")
        judgments = []
        engine = JudgmentEngine()

        for pattern in patterns:
            log = log_mgr.start_log(pattern.test_case_id)
            log_mgr.add_entry(pattern.test_case_id, LogEntry(
                timestamp=0.0, channel=1,
                message_name="TestMsg", signal_name=pattern.target_signal,
                value=float(pattern.expected_value), direction="Rx",
            ))
            log_mgr.end_log(pattern.test_case_id)

            criteria = JudgmentCriteria(
                judgment_type=JudgmentType.EXACT,
                signal_name=pattern.target_signal,
                expected_value=float(pattern.expected_value),
                tolerance=0.1,
            )
            detail = engine.judge(pattern.test_case_id, log, criteria)
            judgments.append(detail)

        # 5. 全判定 OK
        assert all(j.result == JudgmentResult.OK for j in judgments)

        # 6. Excel 帳票出力
        try:
            from src.report.excel_report import ExcelReportGenerator

            report_gen = ExcelReportGenerator()
            report_path = tmp_path / "test_report.xlsx"
            result_path = report_gen.generate(
                summary=summary,
                judgments=judgments,
                output_path=report_path,
                config_file="test_config.cfg",
            )
            assert result_path.exists()
            assert result_path.suffix == ".xlsx"
        except ImportError:
            pytest.skip("openpyxl not installed")

    def test_execution_results_json_roundtrip(
        self, test_patterns, mock_com, tmp_path
    ):
        """実行結果 JSON の保存→読込ラウンドトリップ"""
        runner = TestRunner(com_wrapper=mock_com)
        summary = runner.execute(test_patterns.get_all())

        json_path = tmp_path / "results.json"
        runner.save_results_json(json_path, summary)

        loaded = json.loads(json_path.read_text(encoding="utf-8"))
        assert loaded["total"] == summary.total
        assert loaded["passed"] == summary.passed
        assert len(loaded["results"]) == len(summary.results)
        for orig, loaded_r in zip(
            summary.results, loaded["results"], strict=True
        ):
            assert orig.test_case_id == loaded_r["test_case_id"]


class TestE2EErrorScenarios:
    """異常系シナリオテスト"""

    def test_execution_abort_mid_process(self, test_patterns, mock_com):
        """テスト実行中の中断シナリオ"""
        runner = TestRunner(com_wrapper=mock_com)
        patterns = test_patterns.get_all()

        # 1件目完了後に中断
        def abort_after_first(current: int, total: int, name: str) -> None:
            if current >= 1:
                runner.abort()

        runner.set_progress_callback(abort_after_first)
        summary = runner.execute(patterns)

        # 1件は実行完了、残りは中断
        assert summary.passed >= 1
        assert summary.aborted >= 1
        assert summary.total == 3

    def test_execution_without_com(self, test_patterns):
        """COM ラッパーなしでの実行（スキップされる）"""
        runner = TestRunner(com_wrapper=None)
        summary = runner.execute(test_patterns.get_all())

        assert summary.total == 3
        assert summary.skipped == 3
        assert summary.passed == 0

    def test_invalid_dbc_file(self, tmp_path):
        """不正な DBC ファイルのエラーハンドリング"""
        from src.parsers.dbc_parser import DBCParseError

        invalid_file = tmp_path / "invalid.dbc"
        invalid_file.write_text("INVALID CONTENT", encoding="utf-8")

        parser = DBCParser()
        with pytest.raises(DBCParseError):
            parser.parse(invalid_file)

    def test_missing_file_error(self, tmp_path):
        """存在しないファイルのエラーハンドリング"""
        from src.parsers.dbc_parser import DBCParseError

        parser = DBCParser()
        with pytest.raises(DBCParseError):
            parser.parse(tmp_path / "nonexistent.dbc")

    def test_empty_pattern_execution(self, mock_com):
        """空のパターンリストでの実行"""
        runner = TestRunner(com_wrapper=mock_com)
        summary = runner.execute([])

        assert summary.total == 0
        assert summary.passed == 0

    def test_log_without_start_raises(self):
        """ログ開始前のエントリ追加はエラー"""
        log_mgr = LogManager()
        with pytest.raises(KeyError):
            log_mgr.add_entry("TC-999", LogEntry(
                timestamp=0.0, channel=1,
                message_name="Msg", signal_name="Sig", value=0.0,
            ))

    def test_judgment_no_log_entries(self):
        """ログエントリなしでの判定はエラー"""
        from src.engine.log_manager import TestLog

        engine = JudgmentEngine()
        empty_log = TestLog(test_case_id="TC-999")

        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.EXACT,
            signal_name="SomeSignal",
            expected_value=100.0,
        )
        detail = engine.judge("TC-999", empty_log, criteria)
        assert detail.result == JudgmentResult.ERROR

    def test_judgment_ng_scenario(self, tmp_path):
        """NG 判定のシナリオ"""
        log_mgr = LogManager(log_dir=tmp_path / "logs")
        log = log_mgr.start_log("TC-NG")
        log_mgr.add_entry("TC-NG", LogEntry(
            timestamp=0.0, channel=1, message_name="Msg",
            signal_name="Speed", value=100.0, direction="Rx",
        ))
        log_mgr.end_log("TC-NG")

        engine = JudgmentEngine()
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.EXACT,
            signal_name="Speed",
            expected_value=60.0,
            tolerance=1.0,
        )
        detail = engine.judge("TC-NG", log, criteria)
        assert detail.result == JudgmentResult.NG

    def test_pattern_crud_error_handling(self):
        """テストパターンの CRUD エラーハンドリング"""
        repo = TestPatternRepository()
        with pytest.raises(KeyError):
            repo.get("TC-999")
        with pytest.raises(KeyError):
            repo.delete("TC-999")
        with pytest.raises(KeyError):
            repo.update("TC-999", TestPattern())


class TestE2ELogPersistence:
    """ログ永続化の E2E テスト"""

    def test_log_csv_roundtrip(self, tmp_path):
        """CSV ログの保存→読込ラウンドトリップ"""
        log_mgr = LogManager(log_dir=tmp_path / "logs")
        log_mgr.start_log("TC-001")
        entries = [
            LogEntry(0.0, 1, "EngineData", "EngineSpeed", 1000.0, "Tx"),
            LogEntry(0.1, 1, "EngineData", "EngineSpeed", 2000.0, "Rx"),
            LogEntry(0.2, 1, "EngineData", "EngineSpeed", 3000.0, "Rx"),
        ]
        for entry in entries:
            log_mgr.add_entry("TC-001", entry)
        log_mgr.end_log("TC-001")

        csv_path = log_mgr.save_log_csv("TC-001")
        loaded = log_mgr.load_log_csv(csv_path)

        assert len(loaded.entries) == 3
        assert loaded.entries[0].value == 1000.0
        assert loaded.entries[-1].value == 3000.0

    def test_log_json_roundtrip(self, tmp_path):
        """JSON ログの保存→読込ラウンドトリップ"""
        log_mgr = LogManager(log_dir=tmp_path / "logs")
        log_mgr.start_log("TC-002")
        log_mgr.add_entry("TC-002", LogEntry(
            0.0, 2, "VehicleSpeed", "Speed", 60.0, "Rx",
        ))
        log_mgr.end_log("TC-002")

        json_path = log_mgr.save_log_json("TC-002")
        loaded = log_mgr.load_log_json(json_path)

        assert loaded.test_case_id == "TC-002"
        assert len(loaded.entries) == 1
        assert loaded.entries[0].value == 60.0


class TestE2EReportGeneration:
    """帳票生成の E2E テスト"""

    def test_report_with_mixed_results(self, tmp_path):
        """OK/NG 混在結果の帳票生成"""
        try:
            from src.report.excel_report import ExcelReportGenerator
        except ImportError:
            pytest.skip("openpyxl not installed")

        from src.engine.test_runner import TestResult

        summary = ExecutionSummary(
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

        from src.engine.judgment import JudgmentDetail

        judgments = [
            JudgmentDetail("TC-001", JudgmentResult.OK, JudgmentType.EXACT,
                           "EngineSpeed", "3000", "3000", "0"),
            JudgmentDetail("TC-002", JudgmentResult.OK, JudgmentType.RANGE,
                           "Speed", "50~70", "60"),
            JudgmentDetail("TC-003", JudgmentResult.NG, JudgmentType.EXACT,
                           "CurrentGear", "3", "5", "2",
                           reason="差異 2 が許容差 0 を超えています"),
        ]

        gen = ExcelReportGenerator()
        report_path = tmp_path / "mixed_report.xlsx"
        result = gen.generate(summary, judgments, report_path)
        assert result.exists()

    def test_report_without_judgments(self, tmp_path):
        """判定結果なしの帳票生成"""
        try:
            from src.report.excel_report import ExcelReportGenerator
        except ImportError:
            pytest.skip("openpyxl not installed")

        summary = ExecutionSummary(total=0, start_time="2026-03-10T10:00:00")
        gen = ExcelReportGenerator()
        report_path = tmp_path / "empty_report.xlsx"
        result = gen.generate(summary, output_path=report_path)
        assert result.exists()
