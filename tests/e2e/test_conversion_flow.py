"""パターン作成→変換 E2E テスト

Phase 2 のワークフロー:
パターン入力 → 一括変換 → プレビュー → 手動修正 → 確定 → JSON 出力
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.converter.batch_converter import BatchConverter
from src.models.test_pattern import TestPattern, TestPatternRepository

from .conftest import (
    MockOpenAIConverter,
    MockOpenAIConverterFailing,
    MockOpenAIConverterPartialFail,
)


@pytest.mark.e2e
class TestConversionFlow:
    """E2E-N03: 一括変換→プレビュー→確定"""

    def test_batch_convert_preview_confirm(
        self,
        mock_converter: MockOpenAIConverter,
        tmp_path: Path,
    ) -> None:
        """10 件一括変換 → プレビュー確認 → 全件確定 → JSON 出力"""
        patterns = [
            TestPattern(
                test_case_id=f"TC-{i:03d}",
                test_case_name=f"テストケース {i}",
                target_signal=f"Signal_{i}",
                operation=f"信号 {i} を操作する",
                expected_value=f"期待値 {i}",
                wait_time_ms=100 * i,
            )
            for i in range(1, 11)
        ]

        # 進捗コールバック検証
        progress_log: list[tuple[int, int]] = []

        def on_progress(current: int, total: int) -> None:
            progress_log.append((current, total))

        batch = BatchConverter(converter=mock_converter)
        batch.set_progress_callback(on_progress)

        # 一括変換
        previews = batch.convert_all(patterns)
        assert len(previews) == 10
        assert all(p.success for p in previews)
        assert mock_converter.call_count == 10

        # 進捗が 1/10 → 10/10 まで通知されること
        assert len(progress_log) == 10
        assert progress_log[0] == (1, 10)
        assert progress_log[-1] == (10, 10)

        # プレビュー確認
        preview_items = batch.get_preview_items()
        assert len(preview_items) == 10
        for item in preview_items:
            assert item.converted_params
            assert not item.confirmed

        # 全件確定
        confirmed = batch.confirm_all()
        assert len(confirmed) == 10
        assert all(c.confirmed for c in confirmed)

        # JSON 出力
        output_path = tmp_path / "confirmed_output.json"
        batch.export_confirmed(output_path)
        assert output_path.exists()

        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert len(data) == 10
        assert data[0]["test_case_id"] == "TC-001"
        assert "params" in data[0]

    def test_manual_edit_after_preview(
        self,
        mock_converter: MockOpenAIConverter,
        tmp_path: Path,
    ) -> None:
        """プレビュー後の手動修正 → 確定"""
        patterns = [
            TestPattern(
                test_case_id="TC-EDIT-001",
                test_case_name="手動修正テスト",
                operation="信号を操作",
                expected_value="期待値",
            ),
        ]

        batch = BatchConverter(converter=mock_converter)
        batch.convert_all(patterns)

        # プレビュー項目を手動修正
        new_params = {
            "signal_name": "EditedSignal",
            "message_name": "EditedMessage",
            "action": "set",
            "value": 999,
            "judgment_type": "exact",
        }
        updated = batch.update_preview_item("TC-EDIT-001", new_params)
        assert updated.manually_edited is True
        assert updated.converted_params["signal_name"] == "EditedSignal"
        assert updated.converted_params["value"] == 999

        # 確定 → 出力
        batch.confirm_all()
        output_path = tmp_path / "edited_output.json"
        batch.export_confirmed(output_path)

        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["params"]["signal_name"] == "EditedSignal"

    def test_repository_save_load_roundtrip(self, tmp_path: Path) -> None:
        """TestPatternRepository の JSON 保存・読込の往復テスト"""
        repo = TestPatternRepository()
        for i in range(5):
            repo.add(
                TestPattern(
                    test_case_name=f"テスト {i}",
                    target_signal=f"Signal_{i}",
                    operation=f"操作 {i}",
                    expected_value=f"期待値 {i}",
                )
            )
        assert repo.count == 5

        json_path = tmp_path / "patterns.json"
        repo.save_to_json(json_path)
        assert json_path.exists()

        # 新しいリポジトリに読み込み
        repo2 = TestPatternRepository()
        repo2.load_from_json(json_path)
        assert repo2.count == 5
        assert repo2.get("TC-001").test_case_name == "テスト 0"
        assert repo2.get("TC-005").test_case_name == "テスト 4"


@pytest.mark.e2e
class TestConversionErrors:
    """E2E-E02〜E03: AI 変換エラー"""

    def test_all_conversion_failure(self, tmp_path: Path) -> None:
        """E2E-E02: 全件変換失敗"""
        patterns = [
            TestPattern(
                test_case_id=f"TC-FAIL-{i:03d}",
                test_case_name=f"失敗テスト {i}",
                operation=f"操作 {i}",
                expected_value=f"期待値 {i}",
            )
            for i in range(1, 6)
        ]

        failing_converter = MockOpenAIConverterFailing()
        batch = BatchConverter(converter=failing_converter)
        previews = batch.convert_all(patterns)

        assert len(previews) == 5
        assert all(not p.success for p in previews)
        assert all(p.error_message for p in previews)

        # 確定 → 失敗項目は確定されないこと
        confirmed = batch.confirm_all()
        assert len(confirmed) == 0

        # export_confirmed で空JSON出力
        output_path = tmp_path / "empty_output.json"
        batch.export_confirmed(output_path)
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert len(data) == 0

    def test_partial_conversion_failure(self, tmp_path: Path) -> None:
        """E2E-E03: 10 件中 3 件が変換失敗 → 成功 7 件のみ確定可能"""
        fail_ids = {"TC-003", "TC-006", "TC-009"}
        converter = MockOpenAIConverterPartialFail(fail_ids=fail_ids)

        patterns = [
            TestPattern(
                test_case_id=f"TC-{i:03d}",
                test_case_name=f"テスト {i}",
                operation=f"操作 {i}",
                expected_value=f"期待値 {i}",
            )
            for i in range(1, 11)
        ]

        batch = BatchConverter(converter=converter)
        previews = batch.convert_all(patterns)

        assert len(previews) == 10
        success_count = sum(1 for p in previews if p.success)
        fail_count = sum(1 for p in previews if not p.success)
        assert success_count == 7
        assert fail_count == 3

        # 確定 → 成功分のみ
        confirmed = batch.confirm_all()
        assert len(confirmed) == 7

        # JSON 出力 → 7件のみ
        output_path = tmp_path / "partial_output.json"
        batch.export_confirmed(output_path)
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert len(data) == 7

        # 失敗した TC-ID が出力に含まれないこと
        exported_ids = {item["test_case_id"] for item in data}
        assert fail_ids.isdisjoint(exported_ids)
