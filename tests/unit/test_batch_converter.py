"""テストパターン一括生成・プレビュー テスト (Issue #15)"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.converter.batch_converter import BatchConverter, PreviewItem
from src.converter.openai_converter import ConversionResult, OpenAIConverter
from src.models.test_pattern import TestPattern


class TestBatchConverterConvertAll:
    def test_convert_all_empty(self) -> None:
        bc = BatchConverter(converter=MagicMock())
        result = bc.convert_all([])
        assert result == []

    def test_convert_all_success(self) -> None:
        mock_converter = MagicMock(spec=OpenAIConverter)
        mock_converter.convert.return_value = ConversionResult(
            test_case_id="TC-001",
            original_text="操作",
            converted_params={"signal_name": "Sig1", "value": 100},
            success=True,
        )
        bc = BatchConverter(converter=mock_converter)
        patterns = [
            TestPattern(test_case_id="TC-001", operation="操作", expected_value="期待"),
        ]
        result = bc.convert_all(patterns)
        assert len(result) == 1
        assert result[0].success
        assert result[0].converted_params["signal_name"] == "Sig1"

    def test_convert_all_with_error(self) -> None:
        mock_converter = MagicMock(spec=OpenAIConverter)
        mock_converter.convert.side_effect = Exception("API error")
        bc = BatchConverter(converter=mock_converter)
        patterns = [
            TestPattern(test_case_id="TC-001", operation="操作", expected_value="期待"),
        ]
        result = bc.convert_all(patterns)
        assert len(result) == 1
        assert not result[0].success

    def test_progress_callback(self) -> None:
        mock_converter = MagicMock(spec=OpenAIConverter)
        mock_converter.convert.return_value = ConversionResult(
            "TC-001", "op", {}, success=True,
        )
        callback = MagicMock()
        bc = BatchConverter(converter=mock_converter)
        bc.set_progress_callback(callback)
        patterns = [
            TestPattern(test_case_id="TC-001", operation="op1", expected_value="ex1"),
            TestPattern(test_case_id="TC-002", operation="op2", expected_value="ex2"),
        ]
        bc.convert_all(patterns)
        assert callback.call_count == 2


class TestBatchConverterPreview:
    def test_get_preview_items(self) -> None:
        bc = BatchConverter()
        bc._preview_items = [
            PreviewItem("TC-001", "op", "ex", {"key": "val"}, success=True),
        ]
        items = bc.get_preview_items()
        assert len(items) == 1

    def test_update_preview_item(self) -> None:
        bc = BatchConverter()
        bc._preview_items = [
            PreviewItem("TC-001", "op", "ex", {"key": "val"}, success=True),
        ]
        updated = bc.update_preview_item("TC-001", {"key": "new_val"})
        assert updated.converted_params["key"] == "new_val"
        assert updated.manually_edited

    def test_update_nonexistent_raises(self) -> None:
        bc = BatchConverter()
        with pytest.raises(KeyError):
            bc.update_preview_item("TC-999", {})


class TestBatchConverterConfirm:
    def test_confirm_all(self) -> None:
        bc = BatchConverter()
        bc._preview_items = [
            PreviewItem("TC-001", "op", "ex", {}, success=True),
            PreviewItem("TC-002", "op", "ex", {}, success=False),
        ]
        confirmed = bc.confirm_all()
        assert len(confirmed) == 1
        assert confirmed[0].test_case_id == "TC-001"

    def test_confirm_item(self) -> None:
        bc = BatchConverter()
        bc._preview_items = [
            PreviewItem("TC-001", "op", "ex", {}, success=True),
        ]
        item = bc.confirm_item("TC-001")
        assert item.confirmed

    def test_confirm_nonexistent_raises(self) -> None:
        bc = BatchConverter()
        with pytest.raises(KeyError):
            bc.confirm_item("TC-999")

    def test_export_confirmed(self, tmp_path: Path) -> None:
        bc = BatchConverter()
        bc._preview_items = [
            PreviewItem("TC-001", "op", "ex", {"signal": "Sig1"}, success=True, confirmed=True),
            PreviewItem("TC-002", "op", "ex", {}, success=True, confirmed=False),
        ]
        output = tmp_path / "confirmed.json"
        bc.export_confirmed(output)
        data = json.loads(output.read_text())
        assert len(data) == 1
        assert data[0]["test_case_id"] == "TC-001"
