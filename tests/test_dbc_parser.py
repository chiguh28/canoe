"""DBC Parser のテスト

TDD Phase 1: Red
このテストファイルを先に作成し、実装前に失敗を確認する。
"""

from pathlib import Path

import pytest

from src.models.signal_model import Protocol, SignalInfo
from src.parsers.dbc_parser import DBCParseError, DBCParser

# Fixture path
FIXTURE_DIR = Path(__file__).parent / "fixtures"
SAMPLE_DBC = FIXTURE_DIR / "sample.dbc"


class TestDBCParser:
    """DBCParser クラスのテスト"""

    def test_parse_basic_dbc_file(self):
        """基本的なDBCファイルの解析テスト"""
        parser = DBCParser()
        signals = parser.parse(SAMPLE_DBC)

        # 信号が正しく取得できること
        assert len(signals) > 0
        assert all(isinstance(s, SignalInfo) for s in signals)

    def test_parse_engine_speed_signal(self):
        """EngineSpeed信号の詳細な解析テスト"""
        parser = DBCParser()
        signals = parser.parse(SAMPLE_DBC)

        # EngineSpeed信号を検索
        engine_speed = next((s for s in signals if s.signal_name == "EngineSpeed"), None)
        assert engine_speed is not None, "EngineSpeed signal not found"

        # フィールド検証
        assert engine_speed.signal_name == "EngineSpeed"
        assert engine_speed.message_name == "EngineData"
        assert engine_speed.message_id == 256
        assert engine_speed.min_value == 0
        assert engine_speed.max_value == 8000
        assert engine_speed.unit == "rpm"
        assert engine_speed.protocol == Protocol.CAN
        assert str(SAMPLE_DBC) in engine_speed.source_file

    def test_parse_throttle_position_signal(self):
        """ThrottlePosition信号のスケール係数テスト"""
        parser = DBCParser()
        signals = parser.parse(SAMPLE_DBC)

        throttle = next((s for s in signals if s.signal_name == "ThrottlePosition"), None)
        assert throttle is not None

        # スケール係数 0.5 が適用された範囲
        assert throttle.min_value == 0
        assert throttle.max_value == 100
        assert throttle.unit == "%"

    def test_parse_signed_signal(self):
        """符号付き信号（CoolantTemp）の解析テスト"""
        parser = DBCParser()
        signals = parser.parse(SAMPLE_DBC)

        coolant = next((s for s in signals if s.signal_name == "CoolantTemp"), None)
        assert coolant is not None

        # オフセット -40 が適用された範囲
        assert coolant.min_value == -40
        assert coolant.max_value == 215
        assert coolant.unit == "degC"
        # @1- は符号付きを示す
        assert "signed" in coolant.data_type.lower() or coolant.data_type == "signed"

    def test_parse_node_info(self):
        """ノード情報の解析テスト"""
        parser = DBCParser()
        signals = parser.parse(SAMPLE_DBC)

        engine_speed = next((s for s in signals if s.signal_name == "EngineSpeed"), None)
        assert engine_speed is not None

        # ノード情報の形式: "送信元 -> 受信先1, 受信先2"
        assert "ECU1" in engine_speed.node_info  # 送信元
        assert "ECU2" in engine_speed.node_info or "ECU3" in engine_speed.node_info  # 受信先

    def test_parse_all_messages(self):
        """全メッセージの信号が取得できることを確認"""
        parser = DBCParser()
        signals = parser.parse(SAMPLE_DBC)

        # sample.dbc には3つのメッセージがある
        message_names = {s.message_name for s in signals}
        assert "EngineData" in message_names
        assert "VehicleSpeed" in message_names
        assert "GearStatus" in message_names

        # 合計6つの信号がある
        signal_names = {s.signal_name for s in signals}
        expected_signals = {
            "EngineSpeed",
            "ThrottlePosition",
            "CoolantTemp",
            "Speed",
            "Odometer",
            "CurrentGear",
            "GearRequest",
        }
        assert signal_names == expected_signals

    def test_parse_nonexistent_file(self):
        """存在しないファイルのエラーハンドリング"""
        parser = DBCParser()
        with pytest.raises(DBCParseError, match="DBC file not found"):
            parser.parse(Path("/nonexistent/file.dbc"))

    def test_parse_invalid_dbc_file(self, tmp_path):
        """不正なDBCファイルのエラーハンドリング"""
        invalid_dbc = tmp_path / "invalid.dbc"
        invalid_dbc.write_text("THIS IS NOT A VALID DBC FILE")

        parser = DBCParser()
        with pytest.raises(DBCParseError, match="Failed to parse DBC file"):
            parser.parse(invalid_dbc)

    def test_parse_empty_dbc_file(self, tmp_path):
        """空のDBCファイルのエラーハンドリング"""
        empty_dbc = tmp_path / "empty.dbc"
        empty_dbc.write_text("")

        parser = DBCParser()
        with pytest.raises(DBCParseError):
            parser.parse(empty_dbc)

    def test_data_type_extraction(self):
        """データ型の抽出テスト"""
        parser = DBCParser()
        signals = parser.parse(SAMPLE_DBC)

        # unsigned信号
        engine_speed = next((s for s in signals if s.signal_name == "EngineSpeed"), None)
        assert "unsigned" in engine_speed.data_type.lower() or engine_speed.data_type == "unsigned"

        # signed信号
        coolant = next((s for s in signals if s.signal_name == "CoolantTemp"), None)
        assert "signed" in coolant.data_type.lower() or coolant.data_type == "signed"

    def test_display_name_integration(self):
        """SignalInfo.display_name が正しく機能することを確認"""
        parser = DBCParser()
        signals = parser.parse(SAMPLE_DBC)

        engine_speed = next((s for s in signals if s.signal_name == "EngineSpeed"), None)
        assert engine_speed.display_name == "EngineData.EngineSpeed"
