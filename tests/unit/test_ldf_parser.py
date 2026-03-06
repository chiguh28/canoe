"""LDF パーサーのユニットテスト

TDD Red -> Green -> Refactor
Phase 1 設計書 3.2 準拠
"""

from pathlib import Path

import pytest

from src.models.signal_model import Protocol, SignalInfo
from src.parsers.ldf_parser import LDFParser, LDFParseError


@pytest.fixture
def sample_ldf_path() -> Path:
    """サンプル LDF ファイルパス"""
    return Path(__file__).parent.parent / "fixtures" / "sample.ldf"


@pytest.fixture
def ldf_parser() -> LDFParser:
    """LDFParser インスタンス"""
    return LDFParser()


def test_parse_ldf_returns_signal_list(ldf_parser: LDFParser, sample_ldf_path: Path) -> None:
    """LDF ファイルをパースし、SignalInfo リストを返す"""
    signals = ldf_parser.parse(sample_ldf_path)

    assert isinstance(signals, list)
    assert len(signals) > 0
    assert all(isinstance(s, SignalInfo) for s in signals)


def test_parse_ldf_signal_info_fields(ldf_parser: LDFParser, sample_ldf_path: Path) -> None:
    """パースされた SignalInfo のフィールドが正しく設定される"""
    signals = ldf_parser.parse(sample_ldf_path)

    # EngineSpeed シグナルを検索
    engine_speed = next((s for s in signals if s.signal_name == "EngineSpeed"), None)
    assert engine_speed is not None
    assert engine_speed.message_name == "EngineData"
    assert engine_speed.message_id == 0x10
    assert engine_speed.data_type in ("unsigned", "integer", "signal")
    assert engine_speed.min_value == 0.0
    assert engine_speed.max_value == 8000.0
    assert engine_speed.unit == "rpm"
    assert engine_speed.protocol == Protocol.LIN
    assert "ECU_Master" in engine_speed.node_info or "ECU_Slave1" in engine_speed.node_info
    assert str(sample_ldf_path) in engine_speed.source_file


def test_parse_ldf_all_signals_extracted(ldf_parser: LDFParser, sample_ldf_path: Path) -> None:
    """全シグナルが正しく抽出される"""
    signals = ldf_parser.parse(sample_ldf_path)

    signal_names = {s.signal_name for s in signals}
    expected_names = {"EngineSpeed", "ThrottlePosition", "VehicleSpeed", "BatteryVoltage"}
    assert signal_names == expected_names


def test_parse_ldf_message_id_mapping(ldf_parser: LDFParser, sample_ldf_path: Path) -> None:
    """メッセージ ID とシグナルのマッピングが正しい"""
    signals = ldf_parser.parse(sample_ldf_path)

    # EngineData (0x10) のシグナル
    engine_data_signals = [s for s in signals if s.message_id == 0x10]
    engine_data_names = {s.signal_name for s in engine_data_signals}
    assert engine_data_names == {"EngineSpeed", "ThrottlePosition"}

    # VehicleData (0x11) のシグナル
    vehicle_data_signals = [s for s in signals if s.message_id == 0x11]
    vehicle_data_names = {s.signal_name for s in vehicle_data_signals}
    assert vehicle_data_names == {"VehicleSpeed", "BatteryVoltage"}


def test_parse_nonexistent_file_raises_error(ldf_parser: LDFParser) -> None:
    """存在しないファイルを指定するとエラー"""
    nonexistent_path = Path("nonexistent.ldf")

    with pytest.raises(LDFParseError, match="File not found"):
        ldf_parser.parse(nonexistent_path)


def test_parse_invalid_ldf_raises_error(ldf_parser: LDFParser, tmp_path: Path) -> None:
    """不正な LDF ファイルをパースするとエラー"""
    invalid_ldf = tmp_path / "invalid.ldf"
    invalid_ldf.write_text("This is not a valid LDF file content")

    with pytest.raises(LDFParseError, match="Failed to parse"):
        ldf_parser.parse(invalid_ldf)


def test_parse_ldf_without_signals_raises_error(ldf_parser: LDFParser, tmp_path: Path) -> None:
    """Signals セクションがない LDF ファイルはエラー"""
    incomplete_ldf = tmp_path / "incomplete.ldf"
    incomplete_ldf.write_text(
        """LIN_description_file;
LDF_file_revision = "2.0";
LIN_protocol_version = "2.0";
LIN_language_version = "2.0";
LIN_speed = 19.2 kbps;

Nodes {
  Master: ECU_Master, 5 ms, 0.1 ms ;
  Slaves: ECU_Slave1 ;
}

Node_attributes {
  ECU_Slave1 {
    LIN_protocol = "2.0" ;
    configured_NAD = 0x01 ;
    product_id = 0x1E, 0x01, 0 ;
  }
}
"""
    )

    with pytest.raises(LDFParseError, match="Failed to parse"):
        ldf_parser.parse(incomplete_ldf)


def test_parse_str_path(ldf_parser: LDFParser, sample_ldf_path: Path) -> None:
    """文字列パスも受け付ける"""
    signals = ldf_parser.parse(str(sample_ldf_path))

    assert isinstance(signals, list)
    assert len(signals) > 0
