"""SignalTab のユニットテスト (Issue #11)

ファイル読込UI・信号一覧表示画面の機能テスト。
TDD: テストを先に書き、実装を後から行う。
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.gui.signal_tab import SignalTab
from src.models.signal_model import Protocol, SignalInfo, SignalRepository


def _make_signal(
    name: str = "TestSignal",
    message: str = "TestMsg",
    msg_id: int = 0x100,
    protocol: Protocol = Protocol.CAN,
    min_val: float = 0.0,
    max_val: float = 255.0,
    unit: str = "rpm",
    data_type: str = "unsigned",
) -> SignalInfo:
    """テスト用 SignalInfo ヘルパー"""
    return SignalInfo(
        signal_name=name,
        message_name=message,
        message_id=msg_id,
        data_type=data_type,
        min_value=min_val,
        max_value=max_val,
        unit=unit,
        node_info="ECU1 -> ECU2",
        source_file="test.dbc",
        protocol=protocol,
    )


class TestSignalTabCreation:
    """SignalTab の生成テスト"""

    def test_signal_tab_creates_with_parent_frame(self) -> None:
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)
        assert tab.repository is repo

    def test_signal_tab_has_open_button(self) -> None:
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)
        assert hasattr(tab, "open_button")

    def test_signal_tab_has_search_entry(self) -> None:
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)
        assert hasattr(tab, "search_entry")

    def test_signal_tab_has_treeview(self) -> None:
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)
        assert hasattr(tab, "treeview")

    def test_signal_tab_has_file_list(self) -> None:
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)
        assert hasattr(tab, "loaded_files")


class TestSignalTabFileLoading:
    """ファイル読み込み機能テスト"""

    def test_load_dbc_file(self, tmp_path: Path) -> None:
        """DBC ファイル読み込みでパーサーが呼ばれる"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        signals = [_make_signal("Sig1"), _make_signal("Sig2")]

        with patch("src.gui.signal_tab.DBCParser") as mock_parser_cls:
            mock_parser_cls.return_value.parse.return_value = signals
            dbc_file = tmp_path / "test.dbc"
            dbc_file.write_text("VERSION \"\"")

            tab.load_file(dbc_file)

            mock_parser_cls.return_value.parse.assert_called_once_with(dbc_file)
            assert repo.count == 2

    def test_load_ldf_file(self, tmp_path: Path) -> None:
        """LDF ファイル読み込みでパーサーが呼ばれる"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        signals = [_make_signal("LinSig1", protocol=Protocol.LIN)]

        with patch("src.gui.signal_tab.LDFParser") as mock_parser_cls:
            mock_parser_cls.return_value.parse.return_value = signals
            ldf_file = tmp_path / "test.ldf"
            ldf_file.write_text("LIN_description_file;")

            tab.load_file(ldf_file)

            mock_parser_cls.return_value.parse.assert_called_once_with(ldf_file)
            assert repo.count == 1

    def test_load_unsupported_file_raises_error(self, tmp_path: Path) -> None:
        """サポート外拡張子でエラー"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("dummy")

        with pytest.raises(ValueError, match="サポートされていないファイル形式"):
            tab.load_file(txt_file)

    def test_load_file_tracks_loaded_files(self, tmp_path: Path) -> None:
        """読み込み済みファイルが追跡される"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        with patch("src.gui.signal_tab.DBCParser") as mock_parser_cls:
            mock_parser_cls.return_value.parse.return_value = [_make_signal()]
            dbc_file = tmp_path / "test.dbc"
            dbc_file.write_text("VERSION \"\"")

            tab.load_file(dbc_file)

            assert str(dbc_file) in tab.loaded_files

    def test_load_multiple_files(self, tmp_path: Path) -> None:
        """複数ファイルの読み込み"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        with patch("src.gui.signal_tab.DBCParser") as mock_dbc, \
             patch("src.gui.signal_tab.LDFParser") as mock_ldf:
            mock_dbc.return_value.parse.return_value = [_make_signal("CanSig")]
            mock_ldf.return_value.parse.return_value = [
                _make_signal("LinSig", protocol=Protocol.LIN),
            ]

            dbc_file = tmp_path / "test.dbc"
            dbc_file.write_text("VERSION \"\"")
            ldf_file = tmp_path / "test.ldf"
            ldf_file.write_text("LIN_description_file;")

            tab.load_file(dbc_file)
            tab.load_file(ldf_file)

            assert repo.count == 2
            assert len(tab.loaded_files) == 2


class TestSignalTabSearch:
    """絞り込み検索テスト"""

    def test_filter_signals_by_query(self) -> None:
        """検索クエリで信号を絞り込める"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        repo.add_signals([
            _make_signal("EngineSpeed"),
            _make_signal("VehicleSpeed"),
            _make_signal("BrakeStatus"),
        ])

        results = tab.get_filtered_signals("speed")
        assert len(results) == 2
        assert all("Speed" in s.signal_name for s in results)

    def test_empty_query_returns_all(self) -> None:
        """空クエリで全件返す"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        repo.add_signals([_make_signal("Sig1"), _make_signal("Sig2")])

        results = tab.get_filtered_signals("")
        assert len(results) == 2


class TestSignalTabTreeviewData:
    """Treeview 表示データ変換テスト"""

    def test_signal_to_row_data(self) -> None:
        """SignalInfo を Treeview の行データに変換"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        signal = _make_signal(
            name="EngineSpeed",
            message="EngineData",
            msg_id=0x100,
            data_type="unsigned",
            min_val=0.0,
            max_val=8000.0,
            unit="rpm",
            protocol=Protocol.CAN,
        )

        row = tab.signal_to_row(signal)
        assert row == (
            "EngineSpeed",
            "EngineData",
            "0x100",
            "unsigned",
            "0.0",
            "8000.0",
            "rpm",
            "CAN",
        )

    def test_treeview_columns(self) -> None:
        """Treeview のカラム定義"""
        expected_columns = [
            "signal_name",
            "message_name",
            "message_id",
            "data_type",
            "min_value",
            "max_value",
            "unit",
            "protocol",
        ]
        assert SignalTab.COLUMNS == expected_columns

    def test_treeview_column_headers(self) -> None:
        """Treeview のカラムヘッダー（日本語）"""
        expected_headers = [
            "信号名",
            "メッセージ名",
            "メッセージID",
            "データ型",
            "最小値",
            "最大値",
            "単位",
            "プロトコル",
        ]
        assert SignalTab.COLUMN_HEADERS == expected_headers


class TestSignalTabSort:
    """ソート機能テスト"""

    def test_sort_by_signal_name(self) -> None:
        """信号名でソート"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        repo.add_signals([
            _make_signal("Zebra"),
            _make_signal("Alpha"),
            _make_signal("Middle"),
        ])

        sorted_signals = tab.sort_signals(repo.get_all(), "signal_name", reverse=False)
        names = [s.signal_name for s in sorted_signals]
        assert names == ["Alpha", "Middle", "Zebra"]

    def test_sort_by_signal_name_reverse(self) -> None:
        """信号名で逆順ソート"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        repo.add_signals([
            _make_signal("Zebra"),
            _make_signal("Alpha"),
            _make_signal("Middle"),
        ])

        sorted_signals = tab.sort_signals(repo.get_all(), "signal_name", reverse=True)
        names = [s.signal_name for s in sorted_signals]
        assert names == ["Zebra", "Middle", "Alpha"]

    def test_sort_by_protocol(self) -> None:
        """プロトコルでソート"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        repo.add_signals([
            _make_signal("Sig1", protocol=Protocol.LIN),
            _make_signal("Sig2", protocol=Protocol.CAN),
        ])

        sorted_signals = tab.sort_signals(repo.get_all(), "protocol", reverse=False)
        protocols = [s.protocol.value for s in sorted_signals]
        assert protocols == ["CAN", "LIN"]
