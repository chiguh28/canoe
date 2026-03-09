"""テストパターン一括生成・プレビュー機能 (Issue #15)

全テストパターンを一括でAzure OpenAIで変換し、
プレビュー・手動修正・確定の機能を提供する。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.converter.openai_converter import OpenAIConverter
from src.models.test_pattern import TestPattern

logger = logging.getLogger(__name__)


@dataclass
class PreviewItem:
    """プレビュー項目"""

    test_case_id: str
    original_operation: str
    original_expected: str
    converted_params: dict[str, object]
    success: bool = True
    error_message: str = ""
    manually_edited: bool = False
    confirmed: bool = False


class BatchConverter:
    """テストパターン一括変換エンジン

    全テストパターンを順次Azure OpenAI変換し、
    プレビュー・手動修正・確定の機能を提供する。
    """

    def __init__(self, converter: OpenAIConverter | None = None) -> None:
        self._converter = converter or OpenAIConverter()
        self._preview_items: list[PreviewItem] = []
        self._progress_callback: Callable[[int, int], None] | None = None

    def set_progress_callback(self, callback: Callable[[int, int], None]) -> None:
        """進捗コールバックを設定"""
        self._progress_callback = callback

    def convert_all(
        self,
        patterns: list[TestPattern],
        signal_list: list[str] | None = None,
    ) -> list[PreviewItem]:
        """全テストパターンを一括変換

        Args:
            patterns: テストパターンリスト
            signal_list: 利用可能な信号名リスト

        Returns:
            プレビュー項目のリスト
        """
        self._preview_items = []
        total = len(patterns)

        for i, pattern in enumerate(patterns):
            if self._progress_callback:
                self._progress_callback(i + 1, total)

            try:
                result = self._converter.convert(
                    pattern.test_case_id,
                    pattern.operation,
                    pattern.expected_value,
                    signal_list,
                )
                item = PreviewItem(
                    test_case_id=pattern.test_case_id,
                    original_operation=pattern.operation,
                    original_expected=pattern.expected_value,
                    converted_params=result.converted_params,
                    success=result.success,
                    error_message=result.error_message,
                )
            except Exception as e:
                item = PreviewItem(
                    test_case_id=pattern.test_case_id,
                    original_operation=pattern.operation,
                    original_expected=pattern.expected_value,
                    converted_params={},
                    success=False,
                    error_message=str(e),
                )

            self._preview_items.append(item)

        return list(self._preview_items)

    def get_preview_items(self) -> list[PreviewItem]:
        """現在のプレビュー項目を取得"""
        return list(self._preview_items)

    def update_preview_item(
        self, test_case_id: str, new_params: dict[str, object]
    ) -> PreviewItem:
        """プレビュー項目を手動修正

        Args:
            test_case_id: テストケースID
            new_params: 修正後のパラメータ

        Returns:
            更新されたプレビュー項目
        """
        for item in self._preview_items:
            if item.test_case_id == test_case_id:
                item.converted_params = new_params
                item.manually_edited = True
                return item
        raise KeyError(f"プレビュー項目が見つかりません: {test_case_id}")

    def confirm_all(self) -> list[PreviewItem]:
        """全プレビュー項目を確定"""
        for item in self._preview_items:
            if item.success:
                item.confirmed = True
        return [item for item in self._preview_items if item.confirmed]

    def confirm_item(self, test_case_id: str) -> PreviewItem:
        """個別プレビュー項目を確定"""
        for item in self._preview_items:
            if item.test_case_id == test_case_id:
                item.confirmed = True
                return item
        raise KeyError(f"プレビュー項目が見つかりません: {test_case_id}")

    def export_confirmed(self, output_path: Path) -> Path:
        """確定済みのパラメータをJSON出力

        Args:
            output_path: 出力先パス

        Returns:
            出力ファイルパス
        """
        confirmed = [
            {
                "test_case_id": item.test_case_id,
                "params": item.converted_params,
            }
            for item in self._preview_items
            if item.confirmed
        ]
        output_path.write_text(
            json.dumps(confirmed, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path
