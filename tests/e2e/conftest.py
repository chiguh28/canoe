"""E2E テスト専用フィクスチャ

MockCANoeCOM / MockOpenAIConverter を定義し、
E2E テスト全体で共有する。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.converter.batch_converter import BatchConverter
from src.converter.openai_converter import ConversionResult, OpenAIConverter
from src.engine.canoe_com import CANoeState
from src.engine.judgment import JudgmentEngine
from src.engine.log_manager import LogManager
from src.engine.test_runner import TestRunner
from src.models.signal_model import SignalRepository
from src.models.test_pattern import TestPattern
from src.parsers.dbc_parser import DBCParser
from src.parsers.ldf_parser import LDFParser
from src.report.excel_report import ExcelReportGenerator

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
E2E_FIXTURES_DIR = FIXTURES_DIR / "e2e"
ERROR_FIXTURES_DIR = FIXTURES_DIR / "error"


# ---------------------------------------------------------------------------
# Mock classes
# ---------------------------------------------------------------------------


class MockCANoeCOM:
    """CANoe COM API モック

    E2E テスト用。シナリオに応じた信号値を返す。
    JSON ファイルで応答パターンを定義可能。
    """

    def __init__(self, response_file: Path | None = None) -> None:
        self._state: CANoeState = CANoeState.DISCONNECTED
        self._config_path: str = ""
        self._signal_values: dict[str, float] = {}
        self._responses: dict[str, list[dict[str, Any]]] = {}
        if response_file and response_file.exists():
            self._load_responses(response_file)

    @property
    def state(self) -> CANoeState:
        return self._state

    @property
    def config_path(self) -> str:
        return self._config_path

    def connect(self) -> None:
        self._state = CANoeState.CONNECTED

    def disconnect(self) -> None:
        if self._state == CANoeState.MEASURING:
            self.stop_measurement()
        self._state = CANoeState.DISCONNECTED

    def load_config(self, config_path: str) -> None:
        self._config_path = config_path
        self._state = CANoeState.CONNECTED

    def start_measurement(self) -> None:
        self._state = CANoeState.MEASURING

    def stop_measurement(self) -> None:
        self._state = CANoeState.CONNECTED

    def set_signal_value(self, channel: int, message: str, signal: str, value: float) -> None:
        key = f"{channel}.{message}.{signal}"
        self._signal_values[key] = value
        self._apply_scenario_response(key, value)

    def get_signal_value(self, channel: int, message: str, signal: str) -> float:
        key = f"{channel}.{message}.{signal}"
        return self._signal_values.get(key, 0.0)

    def _load_responses(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        self._responses = json.loads(text)

    def _apply_scenario_response(self, key: str, value: float) -> None:
        for scenario in self._responses.get(key, []):
            if scenario.get("input") == value:
                for out_key, out_val in scenario.get("outputs", {}).items():
                    self._signal_values[out_key] = out_val


class MockCANoeCOMFailing(MockCANoeCOM):
    """接続失敗をシミュレートする MockCANoeCOM"""

    def connect(self) -> None:
        from src.engine.canoe_com import CANoeError

        raise CANoeError("CANoe 接続失敗（モック）")


class MockCANoeCOMDisconnecting(MockCANoeCOM):
    """測定中切断をシミュレートする MockCANoeCOM"""

    def __init__(self, disconnect_after: int = 1, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._call_count = 0
        self._disconnect_after = disconnect_after

    def stop_measurement(self) -> None:
        from src.engine.canoe_com import CANoeError

        raise CANoeError("CANoe 測定中に切断されました（モック）")


class MockOpenAIConverter(OpenAIConverter):
    """Azure OpenAI 変換モック

    固定の変換結果を返す。テストデータ JSON から応答を定義可能。
    """

    def __init__(self, responses: dict[str, ConversionResult] | None = None) -> None:
        super().__init__()
        self._mock_responses = responses or {}
        self._call_count: int = 0

    @property
    def call_count(self) -> int:
        return self._call_count

    def convert(
        self,
        test_case_id: str,
        operation_text: str,
        expected_text: str,
        signal_list: list[str] | None = None,
    ) -> ConversionResult:
        self._call_count += 1
        if test_case_id in self._mock_responses:
            return self._mock_responses[test_case_id]
        return ConversionResult(
            test_case_id=test_case_id,
            original_text=f"{operation_text}\n期待値: {expected_text}",
            converted_params={
                "signal_name": "MockSignal",
                "message_name": "MockMessage",
                "action": "set",
                "value": 0,
                "channel": 1,
                "wait_ms": 1000,
                "expected_signal": "MockSignal",
                "expected_message": "MockMessage",
                "expected_value": 0,
                "tolerance": 0,
                "judgment_type": "exact",
            },
            success=True,
        )


class MockOpenAIConverterFailing(OpenAIConverter):
    """全件失敗する変換モック"""

    def convert(
        self,
        test_case_id: str,
        operation_text: str,
        expected_text: str,
        signal_list: list[str] | None = None,
    ) -> ConversionResult:
        return ConversionResult(
            test_case_id=test_case_id,
            original_text=f"{operation_text}\n期待値: {expected_text}",
            converted_params={},
            success=False,
            error_message="API接続失敗（モック）",
        )


class MockOpenAIConverterPartialFail(OpenAIConverter):
    """部分失敗する変換モック（fail_ids に指定された TC のみ失敗）"""

    def __init__(self, fail_ids: set[str] | None = None) -> None:
        super().__init__()
        self._fail_ids = fail_ids or set()

    def convert(
        self,
        test_case_id: str,
        operation_text: str,
        expected_text: str,
        signal_list: list[str] | None = None,
    ) -> ConversionResult:
        if test_case_id in self._fail_ids:
            return ConversionResult(
                test_case_id=test_case_id,
                original_text=f"{operation_text}\n期待値: {expected_text}",
                converted_params={},
                success=False,
                error_message=f"変換失敗（モック）: {test_case_id}",
            )
        return ConversionResult(
            test_case_id=test_case_id,
            original_text=f"{operation_text}\n期待値: {expected_text}",
            converted_params={
                "signal_name": "MockSignal",
                "message_name": "MockMessage",
                "action": "set",
                "value": 0,
                "judgment_type": "exact",
            },
            success=True,
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_dbc_path() -> Path:
    return FIXTURES_DIR / "sample.dbc"


@pytest.fixture
def sample_ldf_path() -> Path:
    return FIXTURES_DIR / "sample.ldf"


@pytest.fixture
def signal_repository(sample_dbc_path: Path, sample_ldf_path: Path) -> SignalRepository:
    """DBC + LDF を読み込んだ SignalRepository"""
    repo = SignalRepository()
    dbc_signals = DBCParser().parse(sample_dbc_path)
    ldf_signals = LDFParser().parse(sample_ldf_path)
    repo.add_signals(dbc_signals)
    repo.add_signals(ldf_signals)
    return repo


@pytest.fixture
def test_patterns() -> list[TestPattern]:
    """テストパターンフィクスチャ（3件）"""
    path = E2E_FIXTURES_DIR / "test_patterns.json"
    text = path.read_text(encoding="utf-8")
    data_list = json.loads(text)
    return [TestPattern.from_dict(d) for d in data_list]


@pytest.fixture
def mock_canoe() -> MockCANoeCOM:
    """MockCANoeCOM インスタンス（レスポンス定義付き）"""
    response_file = E2E_FIXTURES_DIR / "mock_canoe_responses.json"
    return MockCANoeCOM(response_file if response_file.exists() else None)


@pytest.fixture
def mock_converter() -> MockOpenAIConverter:
    """MockOpenAIConverter インスタンス"""
    return MockOpenAIConverter()


@pytest.fixture
def batch_converter(mock_converter: MockOpenAIConverter) -> BatchConverter:
    """MockOpenAIConverter を使った BatchConverter"""
    return BatchConverter(converter=mock_converter)


@pytest.fixture
def test_runner(mock_canoe: MockCANoeCOM) -> TestRunner:
    """MockCANoeCOM を使った TestRunner"""
    return TestRunner(com_wrapper=mock_canoe)


@pytest.fixture
def judgment_engine() -> JudgmentEngine:
    """JudgmentEngine インスタンス"""
    return JudgmentEngine()


@pytest.fixture
def log_manager(tmp_path: Path) -> LogManager:
    """tmp_path を使った LogManager"""
    return LogManager(log_dir=tmp_path / "logs")


@pytest.fixture
def excel_generator() -> ExcelReportGenerator:
    """ExcelReportGenerator インスタンス"""
    return ExcelReportGenerator()
