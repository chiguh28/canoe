"""SignalInfo / SignalRepository ユニットテスト

Phase 1 設計書 5.3 に準拠したテストケース。
TDD: Red → Green → Refactor の Red フェーズ。
"""

import pytest

from src.models.signal_model import (
    MessageInfo,
    Protocol,
    SignalInfo,
    SignalRepository,
)


class TestProtocol:
    """Protocol Enum のテスト"""

    def test_protocol_can(self):
        """CAN プロトコルが定義されている"""
        assert Protocol.CAN.value == "CAN"

    def test_protocol_lin(self):
        """LIN プロトコルが定義されている"""
        assert Protocol.LIN.value == "LIN"


class TestSignalInfo:
    """SignalInfo データクラスのテスト"""

    def test_create_can_signal(self):
        """CAN 信号の生成"""
        signal = SignalInfo(
            signal_name="EngineSpeed",
            message_name="EngineStatus",
            message_id=0x100,
            data_type="unsigned",
            min_value=0.0,
            max_value=8000.0,
            unit="rpm",
            node_info="ECM -> BCM",
            source_file="/path/to/sample.dbc",
            protocol=Protocol.CAN,
        )
        assert signal.signal_name == "EngineSpeed"
        assert signal.message_name == "EngineStatus"
        assert signal.message_id == 0x100
        assert signal.data_type == "unsigned"
        assert signal.min_value == 0.0
        assert signal.max_value == 8000.0
        assert signal.unit == "rpm"
        assert signal.node_info == "ECM -> BCM"
        assert signal.source_file == "/path/to/sample.dbc"
        assert signal.protocol == Protocol.CAN

    def test_create_lin_signal(self):
        """LIN 信号の生成"""
        signal = SignalInfo(
            signal_name="DoorStatus",
            message_name="BodyControl",
            message_id=0x20,
            data_type="boolean",
            min_value=0.0,
            max_value=1.0,
            unit="",
            node_info="BCM -> ",
            source_file="/path/to/sample.ldf",
            protocol=Protocol.LIN,
        )
        assert signal.signal_name == "DoorStatus"
        assert signal.protocol == Protocol.LIN

    def test_display_name(self):
        """GUI 表示用の名称（メッセージ名.信号名）"""
        signal = SignalInfo(
            signal_name="EngineSpeed",
            message_name="EngineStatus",
            message_id=0x100,
            data_type="unsigned",
            min_value=0.0,
            max_value=8000.0,
            unit="rpm",
            node_info="ECM -> BCM",
            source_file="/path/to/sample.dbc",
            protocol=Protocol.CAN,
        )
        assert signal.display_name == "EngineStatus.EngineSpeed"

    def test_matches_query_signal_name(self):
        """信号名で検索ヒット"""
        signal = SignalInfo(
            signal_name="EngineSpeed",
            message_name="EngineStatus",
            message_id=0x100,
            data_type="unsigned",
            min_value=0.0,
            max_value=8000.0,
            unit="rpm",
            node_info="ECM -> BCM",
            source_file="/path/to/sample.dbc",
            protocol=Protocol.CAN,
        )
        assert signal.matches_query("Engine")
        assert signal.matches_query("Speed")

    def test_matches_query_message_name(self):
        """メッセージ名で検索ヒット"""
        signal = SignalInfo(
            signal_name="EngineSpeed",
            message_name="EngineStatus",
            message_id=0x100,
            data_type="unsigned",
            min_value=0.0,
            max_value=8000.0,
            unit="rpm",
            node_info="ECM -> BCM",
            source_file="/path/to/sample.dbc",
            protocol=Protocol.CAN,
        )
        assert signal.matches_query("Status")

    def test_matches_query_case_insensitive(self):
        """検索は大文字小文字を無視する"""
        signal = SignalInfo(
            signal_name="EngineSpeed",
            message_name="EngineStatus",
            message_id=0x100,
            data_type="unsigned",
            min_value=0.0,
            max_value=8000.0,
            unit="rpm",
            node_info="ECM -> BCM",
            source_file="/path/to/sample.dbc",
            protocol=Protocol.CAN,
        )
        assert signal.matches_query("engine")
        assert signal.matches_query("ENGINE")
        assert signal.matches_query("EnGiNe")

    def test_matches_query_no_match(self):
        """検索不一致"""
        signal = SignalInfo(
            signal_name="EngineSpeed",
            message_name="EngineStatus",
            message_id=0x100,
            data_type="unsigned",
            min_value=0.0,
            max_value=8000.0,
            unit="rpm",
            node_info="ECM -> BCM",
            source_file="/path/to/sample.dbc",
            protocol=Protocol.CAN,
        )
        assert not signal.matches_query("Door")
        assert not signal.matches_query("Temperature")

    def test_frozen_dataclass(self):
        """SignalInfo は frozen（イミュータブル）"""
        signal = SignalInfo(
            signal_name="EngineSpeed",
            message_name="EngineStatus",
            message_id=0x100,
            data_type="unsigned",
            min_value=0.0,
            max_value=8000.0,
            unit="rpm",
            node_info="ECM -> BCM",
            source_file="/path/to/sample.dbc",
            protocol=Protocol.CAN,
        )
        with pytest.raises(AttributeError, match="cannot assign to field"):
            signal.signal_name = "NewName"  # type: ignore


class TestMessageInfo:
    """MessageInfo データクラスのテスト"""

    def test_create_message_info(self):
        """MessageInfo の生成"""
        msg = MessageInfo(
            name="EngineStatus",
            message_id=0x100,
            sender_node="ECM",
            signals=(),
            source_file="/path/to/sample.dbc",
            protocol=Protocol.CAN,
        )
        assert msg.name == "EngineStatus"
        assert msg.message_id == 0x100
        assert msg.sender_node == "ECM"
        assert msg.signals == ()
        assert msg.source_file == "/path/to/sample.dbc"
        assert msg.protocol == Protocol.CAN

    def test_frozen_dataclass(self):
        """MessageInfo は frozen（イミュータブル）"""
        msg = MessageInfo(
            name="EngineStatus",
            message_id=0x100,
            sender_node="ECM",
        )
        with pytest.raises(AttributeError, match="cannot assign to field"):
            msg.name = "NewName"  # type: ignore


class TestSignalRepository:
    """SignalRepository のテスト"""

    @pytest.fixture
    def repository(self) -> SignalRepository:
        """空の SignalRepository インスタンスを返す"""
        return SignalRepository()

    @pytest.fixture
    def sample_signals(self) -> list[SignalInfo]:
        """サンプル信号のリストを返す"""
        return [
            SignalInfo(
                signal_name="EngineSpeed",
                message_name="EngineStatus",
                message_id=0x100,
                data_type="unsigned",
                min_value=0.0,
                max_value=8000.0,
                unit="rpm",
                node_info="ECM -> BCM",
                source_file="/path/to/sample.dbc",
                protocol=Protocol.CAN,
            ),
            SignalInfo(
                signal_name="VehicleSpeed",
                message_name="VehicleStatus",
                message_id=0x200,
                data_type="unsigned",
                min_value=0.0,
                max_value=255.0,
                unit="km/h",
                node_info="ECM -> BCM",
                source_file="/path/to/sample.dbc",
                protocol=Protocol.CAN,
            ),
            SignalInfo(
                signal_name="DoorStatus",
                message_name="BodyControl",
                message_id=0x20,
                data_type="boolean",
                min_value=0.0,
                max_value=1.0,
                unit="",
                node_info="BCM -> ",
                source_file="/path/to/sample.ldf",
                protocol=Protocol.LIN,
            ),
        ]

    def test_add_and_get_all(self, repository: SignalRepository, sample_signals: list[SignalInfo]):
        """信号の追加と全件取得"""
        repository.add_signals(sample_signals)
        all_signals = repository.get_all()
        assert len(all_signals) == 3
        assert all_signals == sample_signals

    def test_search(self, repository: SignalRepository, sample_signals: list[SignalInfo]):
        """検索機能"""
        repository.add_signals(sample_signals)
        # 信号名で検索
        results = repository.search("Engine")
        assert len(results) == 1
        assert results[0].signal_name == "EngineSpeed"
        # メッセージ名で検索
        results = repository.search("Vehicle")
        assert len(results) == 1
        assert results[0].signal_name == "VehicleSpeed"

    def test_filter_by_protocol(
        self, repository: SignalRepository, sample_signals: list[SignalInfo]
    ):
        """プロトコルでフィルタ"""
        repository.add_signals(sample_signals)
        # CAN のみ
        can_signals = repository.filter_by_protocol(Protocol.CAN)
        assert len(can_signals) == 2
        assert all(s.protocol == Protocol.CAN for s in can_signals)
        # LIN のみ
        lin_signals = repository.filter_by_protocol(Protocol.LIN)
        assert len(lin_signals) == 1
        assert lin_signals[0].protocol == Protocol.LIN

    def test_get_by_message(self, repository: SignalRepository, sample_signals: list[SignalInfo]):
        """メッセージ名で信号を取得"""
        repository.add_signals(sample_signals)
        signals = repository.get_by_message("EngineStatus")
        assert len(signals) == 1
        assert signals[0].signal_name == "EngineSpeed"

    def test_count(self, repository: SignalRepository, sample_signals: list[SignalInfo]):
        """登録信号数"""
        assert repository.count == 0
        repository.add_signals(sample_signals)
        assert repository.count == 3

    def test_clear(self, repository: SignalRepository, sample_signals: list[SignalInfo]):
        """全信号情報をクリア"""
        repository.add_signals(sample_signals)
        assert repository.count == 3
        repository.clear()
        assert repository.count == 0
        assert repository.get_all() == []

    def test_empty_search_returns_all(
        self, repository: SignalRepository, sample_signals: list[SignalInfo]
    ):
        """空検索は全件返却"""
        repository.add_signals(sample_signals)
        results = repository.search("")
        assert len(results) == 3
        assert results == sample_signals
