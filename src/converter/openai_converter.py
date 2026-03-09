"""Azure OpenAI 変換ロジック (Issue #14)

日本語テスト記述を Azure OpenAI (GPT-4o) で解析し、
CANoe 操作スクリプトのパラメータに変換する。
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Azure OpenAI の設定キー
ENV_ENDPOINT = "AZURE_OPENAI_ENDPOINT"
ENV_API_KEY = "AZURE_OPENAI_API_KEY"
ENV_DEPLOYMENT = "AZURE_OPENAI_DEPLOYMENT"
ENV_API_VERSION = "AZURE_OPENAI_API_VERSION"

MAX_RETRIES = 3
RETRY_DELAY_BASE = 2.0


@dataclass
class ConversionResult:
    """変換結果"""

    test_case_id: str
    original_text: str  # 元の日本語テスト記述
    converted_params: dict[str, Any]  # 変換後のパラメータ
    success: bool = True
    error_message: str = ""
    confidence: float = 1.0  # 変換の信頼度 (0.0-1.0)


class OpenAIConfigError(Exception):
    """Azure OpenAI 設定エラー"""


class OpenAIConversionError(Exception):
    """変換エラー"""


class OpenAIConverter:
    """Azure OpenAI 変換エンジン

    日本語テスト記述を構造化パラメータに変換する。
    """

    SYSTEM_PROMPT = """あなたはCANoe自動テストツールのアシスタントです。
ユーザーが日本語で記述したテストパターン（操作内容・期待値）を解析し、
以下のJSON構造に変換してください。

出力フォーマット:
{
    "signal_name": "信号名",
    "message_name": "メッセージ名",
    "action": "set" | "get" | "wait",
    "value": 数値または文字列,
    "channel": チャンネル番号(デフォルト1),
    "wait_ms": 待機時間(ms),
    "expected_value": 期待値(数値),
    "tolerance": 許容差(数値, デフォルト0),
    "judgment_type": "exact" | "range" | "change" | "timeout"
}

利用可能な信号リストが提供される場合は、そのリストから最適な信号を選択してください。
変換できない場合は {"error": "理由"} を返してください。"""

    def __init__(self) -> None:
        self._endpoint: str = ""
        self._api_key: str = ""
        self._deployment: str = ""
        self._api_version: str = "2024-02-01"
        self._cache: dict[str, ConversionResult] = {}
        self._client: Any = None

    def configure_from_env(self) -> None:
        """環境変数から設定を読み込み

        Raises:
            OpenAIConfigError: 必要な環境変数が設定されていない場合
        """
        self._endpoint = os.environ.get(ENV_ENDPOINT, "")
        self._api_key = os.environ.get(ENV_API_KEY, "")
        self._deployment = os.environ.get(ENV_DEPLOYMENT, "")
        self._api_version = os.environ.get(ENV_API_VERSION, "2024-02-01")

        if not self._endpoint:
            raise OpenAIConfigError(f"環境変数 {ENV_ENDPOINT} が設定されていません")
        if not self._api_key:
            raise OpenAIConfigError(f"環境変数 {ENV_API_KEY} が設定されていません")
        if not self._deployment:
            raise OpenAIConfigError(f"環境変数 {ENV_DEPLOYMENT} が設定されていません")

    def configure(self, endpoint: str, api_key: str, deployment: str) -> None:
        """直接設定"""
        self._endpoint = endpoint
        self._api_key = api_key
        self._deployment = deployment

    def convert(
        self,
        test_case_id: str,
        operation_text: str,
        expected_text: str,
        signal_list: list[str] | None = None,
    ) -> ConversionResult:
        """日本語テスト記述を構造化パラメータに変換

        Args:
            test_case_id: テストケースID
            operation_text: 操作内容（日本語）
            expected_text: 期待値（日本語）
            signal_list: 利用可能な信号名リスト

        Returns:
            変換結果
        """
        cache_key = f"{operation_text}|{expected_text}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            return ConversionResult(
                test_case_id=test_case_id,
                original_text=f"{operation_text}\n期待値: {expected_text}",
                converted_params=cached.converted_params,
                success=cached.success,
                error_message=cached.error_message,
                confidence=cached.confidence,
            )

        user_message = self._build_user_message(operation_text, expected_text, signal_list)

        for attempt in range(MAX_RETRIES):
            try:
                response = self._call_api(user_message)
                result = self._parse_response(test_case_id, operation_text, expected_text, response)
                self._cache[cache_key] = result
                return result
            except OpenAIConversionError:
                if attempt == MAX_RETRIES - 1:
                    raise
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning("API呼び出し失敗。%s秒後にリトライします (試行 %d/%d)",
                               delay, attempt + 1, MAX_RETRIES)
                time.sleep(delay)

        # ここには到達しないが、型チェッカーのため
        return ConversionResult(
            test_case_id=test_case_id,
            original_text=f"{operation_text}\n期待値: {expected_text}",
            converted_params={},
            success=False,
            error_message="最大リトライ回数に達しました",
        )

    def convert_batch(
        self,
        items: list[tuple[str, str, str]],
        signal_list: list[str] | None = None,
    ) -> list[ConversionResult]:
        """バッチ変換

        Args:
            items: [(test_case_id, operation_text, expected_text), ...] のリスト
            signal_list: 利用可能な信号名リスト

        Returns:
            変換結果のリスト
        """
        results = []
        for test_case_id, operation_text, expected_text in items:
            try:
                result = self.convert(test_case_id, operation_text, expected_text, signal_list)
                results.append(result)
            except OpenAIConversionError as e:
                results.append(ConversionResult(
                    test_case_id=test_case_id,
                    original_text=f"{operation_text}\n期待値: {expected_text}",
                    converted_params={},
                    success=False,
                    error_message=str(e),
                ))
        return results

    def _build_user_message(
        self,
        operation_text: str,
        expected_text: str,
        signal_list: list[str] | None,
    ) -> str:
        """API 呼び出し用のユーザーメッセージを構築"""
        message = f"操作内容: {operation_text}\n期待値: {expected_text}"
        if signal_list:
            message += f"\n\n利用可能な信号:\n{', '.join(signal_list)}"
        return message

    def _call_api(self, user_message: str) -> str:
        """Azure OpenAI API を呼び出し

        Raises:
            OpenAIConversionError: API 呼び出しに失敗した場合
        """
        if not self._endpoint or not self._api_key:
            raise OpenAIConversionError("Azure OpenAI が設定されていません")

        try:
            import httpx
        except ImportError:
            try:
                import urllib.request
                url = (
                    f"{self._endpoint}/openai/deployments/{self._deployment}"
                    f"/chat/completions?api-version={self._api_version}"
                )
                payload = json.dumps({
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                }).encode("utf-8")

                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "api-key": self._api_key,
                    },
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read())
                    return str(result["choices"][0]["message"]["content"])
            except Exception as e:
                raise OpenAIConversionError(f"API 呼び出しに失敗しました: {e}") from e

        try:
            url = (
                f"{self._endpoint}/openai/deployments/{self._deployment}"
                f"/chat/completions?api-version={self._api_version}"
            )
            response = httpx.post(
                url,
                json={
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
                headers={"api-key": self._api_key},
                timeout=30.0,
            )
            response.raise_for_status()
            return str(response.json()["choices"][0]["message"]["content"])
        except Exception as e:
            raise OpenAIConversionError(f"API 呼び出しに失敗しました: {e}") from e

    def _parse_response(
        self,
        test_case_id: str,
        operation_text: str,
        expected_text: str,
        response_text: str,
    ) -> ConversionResult:
        """API レスポンスを解析"""
        try:
            params = json.loads(response_text)
        except json.JSONDecodeError as e:
            return ConversionResult(
                test_case_id=test_case_id,
                original_text=f"{operation_text}\n期待値: {expected_text}",
                converted_params={},
                success=False,
                error_message=f"JSON パースエラー: {e}",
            )

        if "error" in params:
            return ConversionResult(
                test_case_id=test_case_id,
                original_text=f"{operation_text}\n期待値: {expected_text}",
                converted_params=params,
                success=False,
                error_message=str(params["error"]),
            )

        return ConversionResult(
            test_case_id=test_case_id,
            original_text=f"{operation_text}\n期待値: {expected_text}",
            converted_params=params,
            success=True,
        )
