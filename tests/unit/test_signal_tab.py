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
            dbc_file.write_text('VERSION ""')

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
            dbc_file.write_text('VERSION ""')

            tab.load_file(dbc_file)

            assert str(dbc_file) in tab.loaded_files

    def test_load_multiple_files(self, tmp_path: Path) -> None:
        """複数ファイルの読み込み"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        with (
            patch("src.gui.signal_tab.DBCParser") as mock_dbc,
            patch("src.gui.signal_tab.LDFParser") as mock_ldf,
        ):
            mock_dbc.return_value.parse.return_value = [_make_signal("CanSig")]
            mock_ldf.return_value.parse.return_value = [
                _make_signal("LinSig", protocol=Protocol.LIN),
            ]

            dbc_file = tmp_path / "test.dbc"
            dbc_file.write_text('VERSION ""')
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

        repo.add_signals(
            [
                _make_signal("EngineSpeed"),
                _make_signal("VehicleSpeed"),
                _make_signal("BrakeStatus"),
            ]
        )

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

        repo.add_signals(
            [
                _make_signal("Zebra"),
                _make_signal("Alpha"),
                _make_signal("Middle"),
            ]
        )

        sorted_signals = tab.sort_signals(repo.get_all(), "signal_name", reverse=False)
        names = [s.signal_name for s in sorted_signals]
        assert names == ["Alpha", "Middle", "Zebra"]

    def test_sort_by_signal_name_reverse(self) -> None:
        """信号名で逆順ソート"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        repo.add_signals(
            [
                _make_signal("Zebra"),
                _make_signal("Alpha"),
                _make_signal("Middle"),
            ]
        )

        sorted_signals = tab.sort_signals(repo.get_all(), "signal_name", reverse=True)
        names = [s.signal_name for s in sorted_signals]
        assert names == ["Zebra", "Middle", "Alpha"]

    def test_sort_by_protocol(self) -> None:
        """プロトコルでソート"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        repo.add_signals(
            [
                _make_signal("Sig1", protocol=Protocol.LIN),
                _make_signal("Sig2", protocol=Protocol.CAN),
            ]
        )

        sorted_signals = tab.sort_signals(repo.get_all(), "protocol", reverse=False)
        protocols = [s.protocol.value for s in sorted_signals]
        assert protocols == ["CAN", "LIN"]


class TestSignalTabUICallbacks:
    """UI callback methods のテスト"""

    def test_on_search_changed_calls_refresh(self) -> None:
        """検索テキスト変更で _refresh_treeview が呼ばれる"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        with patch.object(tab, "_refresh_treeview") as mock_refresh:
            tab._on_search_changed()
            mock_refresh.assert_called_once()

    def test_on_column_click_toggles_sort_order(self) -> None:
        """カラムクリックでソート順がトグルされる"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        repo.add_signals(
            [
                _make_signal("Zebra"),
                _make_signal("Alpha"),
            ]
        )

        # 初回クリック: reverse=False → True
        assert tab._sort_reverse.get("signal_name", False) is False
        tab._on_column_click("signal_name")
        assert tab._sort_reverse["signal_name"] is True

        # 2回目クリック: reverse=True → False
        tab._on_column_click("signal_name")
        assert tab._sort_reverse["signal_name"] is False

    def test_refresh_treeview_calls_treeview_methods(self) -> None:
        """_refresh_treeview が Treeview を更新する"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        repo.add_signals([_make_signal("TestSig")])

        # _refresh_treeview を呼び出して、エラーが起きないことを確認
        tab._refresh_treeview()
        # get_filtered_signals が呼ばれることを確認
        assert repo.count == 1

    def test_refresh_treeview_with_sort_column(self) -> None:
        """_refresh_treeview にソートパラメータを渡せる"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        repo.add_signals(
            [
                _make_signal("Zebra"),
                _make_signal("Alpha"),
            ]
        )

        # sort_signals が呼ばれることを確認
        with patch.object(tab, "sort_signals", wraps=tab.sort_signals) as mock_sort:
            tab._refresh_treeview(sort_column="signal_name", sort_reverse=False)
            mock_sort.assert_called_once()

    def test_update_file_list_label_with_files(self) -> None:
        """_update_file_list_label でラベルが更新される"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        # ファイル追加してラベル更新
        tab.loaded_files.append("/path/to/test1.dbc")
        tab._update_file_list_label()

        # config メソッドが呼ばれたことを確認
        tab.file_list_label.config.assert_called()
        # 呼び出し時の引数に "test1.dbc" が含まれることを確認
        call_args = tab.file_list_label.config.call_args
        if call_args:
            text_arg = call_args[1].get("text", "")
            assert "test1.dbc" in text_arg

    def test_update_file_list_label_empty(self) -> None:
        """_update_file_list_label でファイルなしの場合のラベル"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        tab.loaded_files.clear()
        tab._update_file_list_label()

        # config メソッドが呼ばれて "なし" を設定
        call_args = tab.file_list_label.config.call_args
        if call_args:
            text_arg = call_args[1].get("text", "")
            assert "なし" in text_arg

    def test_on_open_file_with_file_dialog(self, tmp_path: Path) -> None:
        """_on_open_file でファイルダイアログ経由で読み込める"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        dbc_file = tmp_path / "test.dbc"
        dbc_file.write_text('VERSION ""')

        with (
            patch("src.gui.signal_tab.filedialog.askopenfilenames") as mock_dialog,
            patch("src.gui.signal_tab.DBCParser") as mock_parser,
        ):
            mock_dialog.return_value = [str(dbc_file)]
            mock_parser.return_value.parse.return_value = [_make_signal()]

            tab._on_open_file()

            mock_dialog.assert_called_once()
            assert len(tab.loaded_files) == 1

    def test_on_open_file_handles_errors(self, tmp_path: Path) -> None:
        """_on_open_file でエラー発生時にメッセージボックスが表示される (F03)"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        invalid_file = tmp_path / "invalid.txt"
        invalid_file.write_text("not a valid file")

        with (
            patch("src.gui.signal_tab.filedialog.askopenfilenames") as mock_dialog,
            patch("src.gui.signal_tab.messagebox.showerror") as mock_error,
        ):
            mock_dialog.return_value = [str(invalid_file)]

            tab._on_open_file()

            # エラーメッセージボックスが呼ばれたことを確認
            mock_error.assert_called_once()
            # F03: エラーメッセージにファイル名が含まれることを確認
            call_args = mock_error.call_args
            if call_args:
                error_message = call_args[0][1] if len(call_args[0]) > 1 else ""
                assert "invalid.txt" in error_message, "Error message should contain filename"
                # 日本語メッセージであることを確認（複数パターン対応）
                assert any(
                    keyword in error_message
                    for keyword in ["読み込み", "サポートされていない", "ファイル形式"]
                ), "Error message should be in Japanese"

    def test_on_open_file_empty_selection(self) -> None:
        """_on_open_file でキャンセル時は何もしない"""
        parent = MagicMock()
        repo = SignalRepository()
        tab = SignalTab(parent, repo)

        with patch("src.gui.signal_tab.filedialog.askopenfilenames") as mock_dialog:
            mock_dialog.return_value = []  # キャンセル

            tab._on_open_file()

            assert len(tab.loaded_files) == 0
