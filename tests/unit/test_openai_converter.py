"""Azure OpenAI 変換ロジック テスト (Issue #14)"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.converter.openai_converter import (
    ConversionResult,
    OpenAIConfigError,
    OpenAIConversionError,
    OpenAIConverter,
)


class TestOpenAIConverterConfig:
    def test_configure_from_env_missing_endpoint(self) -> None:
        converter = OpenAIConverter()
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(OpenAIConfigError, match="ENDPOINT"):
                converter.configure_from_env()

    def test_configure_from_env_missing_api_key(self) -> None:
        converter = OpenAIConverter()
        with patch.dict("os.environ", {"AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com"}):
            with pytest.raises(OpenAIConfigError, match="API_KEY"):
                converter.configure_from_env()

    def test_configure_from_env_missing_deployment(self) -> None:
        converter = OpenAIConverter()
        env = {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_API_KEY": "test-key",
        }
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(OpenAIConfigError, match="DEPLOYMENT"):
                converter.configure_from_env()

    def test_configure_from_env_success(self) -> None:
        converter = OpenAIConverter()
        env = {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
        }
        with patch.dict("os.environ", env, clear=True):
            converter.configure_from_env()
            assert converter._endpoint == "https://test.openai.azure.com"

    def test_configure_direct(self) -> None:
        converter = OpenAIConverter()
        converter.configure("https://test.openai.azure.com", "key", "gpt-4o")
        assert converter._endpoint == "https://test.openai.azure.com"
        assert converter._api_key == "key"
        assert converter._deployment == "gpt-4o"


class TestOpenAIConverterConvert:
    def test_convert_not_configured_raises(self) -> None:
        converter = OpenAIConverter()
        with pytest.raises(OpenAIConversionError):
            converter.convert("TC-001", "エンジン回転数を3000に設定", "3000rpm")

    def test_parse_response_success(self) -> None:
        converter = OpenAIConverter()
        response = json.dumps({
            "signal_name": "EngineSpeed",
            "action": "set",
            "value": 3000,
        })
        result = converter._parse_response("TC-001", "操作", "期待", response)
        assert result.success
        assert result.converted_params["signal_name"] == "EngineSpeed"

    def test_parse_response_error(self) -> None:
        converter = OpenAIConverter()
        response = json.dumps({"error": "変換できません"})
        result = converter._parse_response("TC-001", "操作", "期待", response)
        assert not result.success

    def test_parse_response_invalid_json(self) -> None:
        converter = OpenAIConverter()
        result = converter._parse_response("TC-001", "操作", "期待", "not json")
        assert not result.success
        assert "JSON" in result.error_message

    def test_cache_hit(self) -> None:
        converter = OpenAIConverter()
        # キャッシュに結果をセット
        cached = ConversionResult(
            test_case_id="TC-001",
            original_text="操作\n期待値: 期待",
            converted_params={"signal_name": "EngSpeed"},
            success=True,
        )
        converter._cache["操作|期待"] = cached

        result = converter.convert.__wrapped__(converter, "TC-002", "操作", "期待") \
            if hasattr(converter.convert, "__wrapped__") \
            else converter.convert("TC-002", "操作", "期待")
        # キャッシュからの取得なので API 未設定でもエラーにならない
        assert result.success
        assert result.test_case_id == "TC-002"

    def test_build_user_message_with_signals(self) -> None:
        converter = OpenAIConverter()
        msg = converter._build_user_message("操作内容", "期待値", ["Sig1", "Sig2"])
        assert "操作内容" in msg
        assert "期待値" in msg
        assert "Sig1" in msg

    def test_build_user_message_without_signals(self) -> None:
        converter = OpenAIConverter()
        msg = converter._build_user_message("操作内容", "期待値", None)
        assert "操作内容" in msg
        assert "利用可能" not in msg


class TestOpenAIConverterBatch:
    @patch("src.converter.openai_converter.time.sleep")
    def test_convert_batch_with_failures(self, mock_sleep: MagicMock) -> None:
        converter = OpenAIConverter()
        converter.configure("https://test.openai.azure.com", "key", "gpt-4o")

        # API 呼び出しをモック（リトライ3回分のエラーも含む）
        with patch.object(converter, "_call_api") as mock_api:
            mock_api.side_effect = [
                json.dumps({"signal_name": "Sig1", "action": "set", "value": 100}),
                OpenAIConversionError("API error"),
                OpenAIConversionError("API error"),
                OpenAIConversionError("API error"),
            ]
            results = converter.convert_batch([
                ("TC-001", "操作1", "期待1"),
                ("TC-002", "操作2", "期待2"),
            ])

        assert len(results) == 2
        assert results[0].success
        assert not results[1].success
