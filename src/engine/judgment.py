"""ログ解析・テスト結果判定ロジック (Issue #20)

テスト実行ログを解析し、各テストパターンに対して
OK/NG/ERROR を自動判定するロジックを提供する。
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from src.engine.log_manager import LogEntry, TestLog

logger = logging.getLogger(__name__)


class JudgmentType(Enum):
    """判定種別"""

    EXACT = "exact"  # 値一致判定
    RANGE = "range"  # 範囲判定
    CHANGE = "change"  # 変化検知判定
    TIMEOUT = "timeout"  # タイムアウト判定
    COMPOUND = "compound"  # 複合判定


class JudgmentResult(Enum):
    """判定結果"""

    OK = "OK"
    NG = "NG"
    ERROR = "ERROR"


class ChangeDirection(Enum):
    """変化方向"""

    INCREASE = "increase"
    DECREASE = "decrease"
    NO_CHANGE = "no_change"


@dataclass
class JudgmentCriteria:
    """判定基準"""

    judgment_type: JudgmentType
    signal_name: str
    expected_value: float | None = None  # EXACT 用
    tolerance: float = 0.0  # EXACT の許容差
    range_min: float | None = None  # RANGE 用
    range_max: float | None = None  # RANGE 用
    change_direction: ChangeDirection | None = None  # CHANGE 用
    timeout_ms: float | None = None  # TIMEOUT 用
    # COMPOUND 用
    sub_criteria: list[JudgmentCriteria] = field(default_factory=list)
    compound_operator: str = "AND"  # "AND" or "OR"


@dataclass
class JudgmentDetail:
    """判定結果の詳細"""

    test_case_id: str
    result: JudgmentResult
    judgment_type: JudgmentType
    signal_name: str
    expected_value: str = ""
    actual_value: str = ""
    difference: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        d = asdict(self)
        d["result"] = self.result.value
        d["judgment_type"] = self.judgment_type.value
        return d


class JudgmentEngine:
    """判定エンジン

    テスト実行ログを解析し、判定基準に基づいて OK/NG/ERROR を判定する。
    """

    def judge(
        self,
        test_case_id: str,
        log: TestLog,
        criteria: JudgmentCriteria,
    ) -> JudgmentDetail:
        """テスト結果を判定

        Args:
            test_case_id: テストケースID
            log: テスト実行ログ
            criteria: 判定基準

        Returns:
            判定結果の詳細
        """
        if criteria.judgment_type == JudgmentType.EXACT:
            return self._judge_exact(test_case_id, log, criteria)
        elif criteria.judgment_type == JudgmentType.RANGE:
            return self._judge_range(test_case_id, log, criteria)
        elif criteria.judgment_type == JudgmentType.CHANGE:
            return self._judge_change(test_case_id, log, criteria)
        elif criteria.judgment_type == JudgmentType.TIMEOUT:
            return self._judge_timeout(test_case_id, log, criteria)
        elif criteria.judgment_type == JudgmentType.COMPOUND:
            return self._judge_compound(test_case_id, log, criteria)
        else:
            return JudgmentDetail(
                test_case_id=test_case_id,
                result=JudgmentResult.ERROR,
                judgment_type=criteria.judgment_type,
                signal_name=criteria.signal_name,
                reason=f"未知の判定種別: {criteria.judgment_type}",
            )

    def _get_signal_entries(
        self, log: TestLog, signal_name: str
    ) -> list[LogEntry]:
        """指定信号のログエントリを取得"""
        return [e for e in log.entries if e.signal_name == signal_name]

    def _judge_exact(
        self, test_case_id: str, log: TestLog, criteria: JudgmentCriteria
    ) -> JudgmentDetail:
        """値一致判定"""
        entries = self._get_signal_entries(log, criteria.signal_name)
        if not entries:
            return JudgmentDetail(
                test_case_id=test_case_id,
                result=JudgmentResult.ERROR,
                judgment_type=JudgmentType.EXACT,
                signal_name=criteria.signal_name,
                expected_value=str(criteria.expected_value),
                reason="対象信号のログエントリが見つかりません",
            )

        # 最後のエントリの値を使用
        actual = entries[-1].value
        expected = criteria.expected_value
        if expected is None:
            return JudgmentDetail(
                test_case_id=test_case_id,
                result=JudgmentResult.ERROR,
                judgment_type=JudgmentType.EXACT,
                signal_name=criteria.signal_name,
                reason="期待値が設定されていません",
            )

        diff = abs(actual - expected)
        is_ok = diff <= criteria.tolerance

        return JudgmentDetail(
            test_case_id=test_case_id,
            result=JudgmentResult.OK if is_ok else JudgmentResult.NG,
            judgment_type=JudgmentType.EXACT,
            signal_name=criteria.signal_name,
            expected_value=str(expected),
            actual_value=str(actual),
            difference=str(diff),
            reason="" if is_ok else f"差異 {diff} が許容差 {criteria.tolerance} を超えています",
        )

    def _judge_range(
        self, test_case_id: str, log: TestLog, criteria: JudgmentCriteria
    ) -> JudgmentDetail:
        """範囲判定"""
        entries = self._get_signal_entries(log, criteria.signal_name)
        if not entries:
            return JudgmentDetail(
                test_case_id=test_case_id,
                result=JudgmentResult.ERROR,
                judgment_type=JudgmentType.RANGE,
                signal_name=criteria.signal_name,
                reason="対象信号のログエントリが見つかりません",
            )

        actual = entries[-1].value
        range_min = criteria.range_min if criteria.range_min is not None else float("-inf")
        range_max = criteria.range_max if criteria.range_max is not None else float("inf")

        is_ok = range_min <= actual <= range_max

        return JudgmentDetail(
            test_case_id=test_case_id,
            result=JudgmentResult.OK if is_ok else JudgmentResult.NG,
            judgment_type=JudgmentType.RANGE,
            signal_name=criteria.signal_name,
            expected_value=f"{range_min} ~ {range_max}",
            actual_value=str(actual),
            reason="" if is_ok else f"値 {actual} が範囲 [{range_min}, {range_max}] 外です",
        )

    def _judge_change(
        self, test_case_id: str, log: TestLog, criteria: JudgmentCriteria
    ) -> JudgmentDetail:
        """変化検知判定"""
        entries = self._get_signal_entries(log, criteria.signal_name)
        if len(entries) < 2:
            return JudgmentDetail(
                test_case_id=test_case_id,
                result=JudgmentResult.ERROR,
                judgment_type=JudgmentType.CHANGE,
                signal_name=criteria.signal_name,
                reason="変化検知には2つ以上のエントリが必要です",
            )

        first_value = entries[0].value
        last_value = entries[-1].value
        diff = last_value - first_value

        if criteria.change_direction == ChangeDirection.INCREASE:
            is_ok = diff > 0
            expected_str = "増加"
        elif criteria.change_direction == ChangeDirection.DECREASE:
            is_ok = diff < 0
            expected_str = "減少"
        elif criteria.change_direction == ChangeDirection.NO_CHANGE:
            is_ok = diff == 0
            expected_str = "変化なし"
        else:
            return JudgmentDetail(
                test_case_id=test_case_id,
                result=JudgmentResult.ERROR,
                judgment_type=JudgmentType.CHANGE,
                signal_name=criteria.signal_name,
                reason="変化方向が設定されていません",
            )

        actual_str = f"{first_value} -> {last_value} (差: {diff})"
        return JudgmentDetail(
            test_case_id=test_case_id,
            result=JudgmentResult.OK if is_ok else JudgmentResult.NG,
            judgment_type=JudgmentType.CHANGE,
            signal_name=criteria.signal_name,
            expected_value=expected_str,
            actual_value=actual_str,
            reason="" if is_ok else f"期待: {expected_str}, 実際: 差={diff}",
        )

    def _judge_timeout(
        self, test_case_id: str, log: TestLog, criteria: JudgmentCriteria
    ) -> JudgmentDetail:
        """タイムアウト判定"""
        entries = self._get_signal_entries(log, criteria.signal_name)
        if not entries:
            return JudgmentDetail(
                test_case_id=test_case_id,
                result=JudgmentResult.NG,
                judgment_type=JudgmentType.TIMEOUT,
                signal_name=criteria.signal_name,
                reason="タイムアウト: 信号が受信されませんでした",
            )

        timeout_ms = criteria.timeout_ms or 0
        if len(entries) >= 2:
            elapsed = (entries[-1].timestamp - entries[0].timestamp) * 1000
            is_ok = elapsed <= timeout_ms
        else:
            is_ok = True

        return JudgmentDetail(
            test_case_id=test_case_id,
            result=JudgmentResult.OK if is_ok else JudgmentResult.NG,
            judgment_type=JudgmentType.TIMEOUT,
            signal_name=criteria.signal_name,
            expected_value=f"<= {timeout_ms} ms",
            actual_value=f"{(entries[-1].timestamp - entries[0].timestamp) * 1000:.1f} ms"
            if len(entries) >= 2 else "N/A",
            reason="" if is_ok else "タイムアウト超過",
        )

    def _judge_compound(
        self, test_case_id: str, log: TestLog, criteria: JudgmentCriteria
    ) -> JudgmentDetail:
        """複合判定"""
        if not criteria.sub_criteria:
            return JudgmentDetail(
                test_case_id=test_case_id,
                result=JudgmentResult.ERROR,
                judgment_type=JudgmentType.COMPOUND,
                signal_name=criteria.signal_name,
                reason="サブ判定基準が設定されていません",
            )

        sub_results = []
        for sub in criteria.sub_criteria:
            detail = self.judge(test_case_id, log, sub)
            sub_results.append(detail)

        if criteria.compound_operator == "AND":
            is_ok = all(r.result == JudgmentResult.OK for r in sub_results)
        else:  # OR
            is_ok = any(r.result == JudgmentResult.OK for r in sub_results)

        ng_reasons = [r.reason for r in sub_results if r.result != JudgmentResult.OK and r.reason]

        return JudgmentDetail(
            test_case_id=test_case_id,
            result=JudgmentResult.OK if is_ok else JudgmentResult.NG,
            judgment_type=JudgmentType.COMPOUND,
            signal_name=criteria.signal_name,
            reason="; ".join(ng_reasons) if ng_reasons else "",
        )

    def save_results_json(
        self, results: list[JudgmentDetail], file_path: Path
    ) -> None:
        """判定結果を JSON に保存"""
        data = [r.to_dict() for r in results]
        file_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
