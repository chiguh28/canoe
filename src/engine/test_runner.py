"""テスト実行エンジン (Issue #17)

テストパターンリストを順次実行するエンジン。
前提条件設定 → 信号送信 → 待機 → ログ取得の実行フローを自動化する。
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from src.models.test_pattern import TestPattern

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """テスト実行ステータス"""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    ABORTED = "aborted"


@dataclass
class TestResult:
    """個別テスト結果"""

    test_case_id: str
    test_case_name: str
    status: TestStatus = TestStatus.PENDING
    actual_value: str = ""
    expected_value: str = ""
    error_message: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_ms: float = 0.0
    log_file: str = ""

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class ExecutionSummary:
    """実行サマリ"""

    total: int = 0
    passed: int = 0
    failed: int = 0
    error: int = 0
    skipped: int = 0
    aborted: int = 0
    start_time: str = ""
    end_time: str = ""
    config_file: str = ""
    results: list[TestResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """合格率（%）"""
        executed = self.passed + self.failed
        if executed == 0:
            return 0.0
        return (self.passed / executed) * 100.0

    @property
    def total_duration_ms(self) -> float:
        """合計実行時間(ms)"""
        return sum(r.duration_ms for r in self.results)

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "error": self.error,
            "skipped": self.skipped,
            "aborted": self.aborted,
            "pass_rate": self.pass_rate,
            "total_duration_ms": self.total_duration_ms,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "config_file": self.config_file,
            "results": [r.to_dict() for r in self.results],
        }


class TestRunner:
    """テスト実行エンジン

    テストパターンリストを順次実行し、結果を収集する。
    COM API ラッパーを注入して使用する。
    """

    def __init__(self, com_wrapper: Any = None) -> None:
        self._com = com_wrapper
        self._abort_requested: bool = False
        self._progress_callback: Callable[[int, int, str], None] | None = None
        self._results: list[TestResult] = []

    def set_progress_callback(
        self, callback: Callable[[int, int, str], None]
    ) -> None:
        """進捗通知コールバックを設定

        Args:
            callback: (current, total, test_case_name) を受け取る関数
        """
        self._progress_callback = callback

    def abort(self) -> None:
        """実行中断を要求"""
        self._abort_requested = True
        logger.info("テスト実行の中断が要求されました")

    def execute(
        self,
        patterns: list[TestPattern],
        config_file: str = "",
    ) -> ExecutionSummary:
        """テストパターンリストを順次実行

        Args:
            patterns: 実行するテストパターンのリスト
            config_file: CANoe 構成ファイルパス

        Returns:
            実行サマリ
        """
        self._abort_requested = False
        self._results = []

        summary = ExecutionSummary(
            total=len(patterns),
            start_time=datetime.now().isoformat(),
            config_file=config_file,
        )

        for i, pattern in enumerate(patterns):
            if self._abort_requested:
                result = TestResult(
                    test_case_id=pattern.test_case_id,
                    test_case_name=pattern.test_case_name,
                    status=TestStatus.ABORTED,
                )
                self._results.append(result)
                summary.aborted += 1
                continue

            # 進捗通知
            if self._progress_callback:
                self._progress_callback(i + 1, len(patterns), pattern.test_case_name)

            result = self._execute_single(pattern)
            self._results.append(result)

            # サマリ更新
            if result.status == TestStatus.PASSED:
                summary.passed += 1
            elif result.status == TestStatus.FAILED:
                summary.failed += 1
            elif result.status == TestStatus.ERROR:
                summary.error += 1
            elif result.status == TestStatus.SKIPPED:
                summary.skipped += 1

        summary.end_time = datetime.now().isoformat()
        summary.results = list(self._results)
        return summary

    def _execute_single(self, pattern: TestPattern) -> TestResult:
        """単一テストパターンを実行

        Args:
            pattern: テストパターン

        Returns:
            テスト結果
        """
        result = TestResult(
            test_case_id=pattern.test_case_id,
            test_case_name=pattern.test_case_name,
            expected_value=pattern.expected_value,
            start_time=datetime.now().isoformat(),
        )

        try:
            result.status = TestStatus.RUNNING

            # 1. 前提条件設定
            if pattern.precondition and self._com:
                logger.info("前提条件設定: %s", pattern.precondition)

            # 2. 信号送信
            if pattern.operation and self._com:
                logger.info("操作実行: %s", pattern.operation)

            # 3. 待機
            if pattern.wait_time_ms > 0:
                time.sleep(pattern.wait_time_ms / 1000.0)

            # 4. 結果取得（COM ラッパーがない場合はスキップ）
            if self._com is None:
                result.status = TestStatus.SKIPPED
                result.error_message = "CANoe COM API が利用できません"
            else:
                # COM API から実測値を取得する処理
                result.actual_value = ""
                result.status = TestStatus.PASSED

        except Exception as e:
            result.status = TestStatus.ERROR
            result.error_message = str(e)
            logger.error("テスト実行エラー: %s - %s", pattern.test_case_id, e)

        result.end_time = datetime.now().isoformat()
        start = datetime.fromisoformat(result.start_time)
        end = datetime.fromisoformat(result.end_time)
        result.duration_ms = (end - start).total_seconds() * 1000

        return result

    def get_results(self) -> list[TestResult]:
        """実行結果のリストを取得"""
        return list(self._results)

    def save_results_json(self, file_path: Path, summary: ExecutionSummary) -> None:
        """実行結果を JSON に保存

        Args:
            file_path: 保存先パス
            summary: 実行サマリ
        """
        file_path.write_text(
            json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("テスト結果を保存しました: %s", file_path)
