"""テストパターンデータモデル (Issue #13)

テストパターンの入力フォームで使用するデータモデル。
テストケースID自動採番、保存・読込機能を提供する。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class TestPattern:
    """テストパターン

    各テストケースのフィールドを管理する。
    """

    test_case_id: str = ""  # TC-001 形式
    test_case_name: str = ""  # テストケース名
    target_signal: str = ""  # 対象信号名
    operation: str = ""  # 操作内容（日本語）
    expected_value: str = ""  # 期待値（日本語）
    precondition: str = ""  # 前提条件
    wait_time_ms: int = 0  # 待機時間(ms)
    remarks: str = ""  # 備考

    def to_dict(self) -> dict[str, object]:
        """辞書に変換"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TestPattern:
        """辞書から生成"""
        return cls(
            test_case_id=str(data.get("test_case_id", "")),
            test_case_name=str(data.get("test_case_name", "")),
            target_signal=str(data.get("target_signal", "")),
            operation=str(data.get("operation", "")),
            expected_value=str(data.get("expected_value", "")),
            precondition=str(data.get("precondition", "")),
            wait_time_ms=int(str(data.get("wait_time_ms", 0))),
            remarks=str(data.get("remarks", "")),
        )


class TestPatternRepository:
    """テストパターンのリポジトリ

    テストパターンの管理（追加・編集・削除・検索）と
    自動採番、保存・読込機能を提供する。
    """

    def __init__(self) -> None:
        self._patterns: list[TestPattern] = []
        self._next_id: int = 1

    def add(self, pattern: TestPattern) -> TestPattern:
        """テストパターンを追加（IDを自動採番）"""
        pattern.test_case_id = f"TC-{self._next_id:03d}"
        self._next_id += 1
        self._patterns.append(pattern)
        return pattern

    def update(self, test_case_id: str, updated: TestPattern) -> TestPattern:
        """テストパターンを更新"""
        for i, p in enumerate(self._patterns):
            if p.test_case_id == test_case_id:
                updated.test_case_id = test_case_id
                self._patterns[i] = updated
                return updated
        raise KeyError(f"テストパターンが見つかりません: {test_case_id}")

    def delete(self, test_case_id: str) -> None:
        """テストパターンを削除"""
        for i, p in enumerate(self._patterns):
            if p.test_case_id == test_case_id:
                self._patterns.pop(i)
                return
        raise KeyError(f"テストパターンが見つかりません: {test_case_id}")

    def get(self, test_case_id: str) -> TestPattern:
        """テストパターンを取得"""
        for p in self._patterns:
            if p.test_case_id == test_case_id:
                return p
        raise KeyError(f"テストパターンが見つかりません: {test_case_id}")

    def get_all(self) -> list[TestPattern]:
        """全テストパターンを取得"""
        return list(self._patterns)

    @property
    def count(self) -> int:
        """テストパターン数"""
        return len(self._patterns)

    def save_to_json(self, file_path: Path) -> None:
        """JSON ファイルに保存"""
        data = [p.to_dict() for p in self._patterns]
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_from_json(self, file_path: Path) -> None:
        """JSON ファイルから読み込み"""
        text = file_path.read_text(encoding="utf-8")
        data_list = json.loads(text)
        self._patterns.clear()
        max_id = 0
        for data in data_list:
            pattern = TestPattern.from_dict(data)
            self._patterns.append(pattern)
            # ID の数値部分を取得して最大値を更新
            if pattern.test_case_id.startswith("TC-"):
                try:
                    num = int(pattern.test_case_id[3:])
                    max_id = max(max_id, num)
                except ValueError:
                    pass
        self._next_id = max_id + 1
