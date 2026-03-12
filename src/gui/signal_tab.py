"""信号情報タブ (Issue #11)

ファイル読込UI・信号一覧表示画面を提供する。
DBC/LDFファイルの読み込み、信号一覧Treeview表示、
絞り込み検索、ソート機能を実装。
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

from src.models.signal_model import SignalInfo, SignalRepository
from src.parsers.dbc_parser import DBCParser
from src.parsers.ldf_parser import LDFParser

if TYPE_CHECKING:
    from collections.abc import Callable


class SignalTab:
    """信号情報タブ

    DBC/LDFファイルの読み込みと信号一覧表示を管理する。
    """

    COLUMNS = [
        "signal_name",
        "message_name",
        "message_id",
        "data_type",
        "min_value",
        "max_value",
        "unit",
        "protocol",
    ]

    COLUMN_HEADERS = [
        "信号名",
        "メッセージ名",
        "メッセージID",
        "データ型",
        "最小値",
        "最大値",
        "単位",
        "プロトコル",
    ]

    def __init__(
        self,
        parent: tk.Widget | ttk.Frame,
        repository: SignalRepository,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.parent = parent
        self.repository = repository
        self.loaded_files: list[str] = []
        self._sort_reverse: dict[str, bool] = {}
        self._status_callback = status_callback  # F06: ステータスバーコールバック

        self._create_widgets()

    def _create_widgets(self) -> None:
        """ウィジェット生成"""
        # ツールバーフレーム
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        # ファイルを開くボタン
        self.open_button = ttk.Button(toolbar, text="ファイルを開く", command=self._on_open_file)
        self.open_button.pack(side=tk.LEFT, padx=5)

        # 絞り込み検索
        ttk.Label(toolbar, text="検索:").pack(side=tk.LEFT, padx=(20, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_var.trace_add("write", self._on_search_changed)

        # 読み込みファイル一覧ラベル
        self.file_list_label = ttk.Label(toolbar, text="読込ファイル: なし")
        self.file_list_label.pack(side=tk.RIGHT, padx=5)

        # Treeview フレーム
        tree_frame = ttk.Frame(self.parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # スクロールバー
        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        # Treeview
        self.treeview = ttk.Treeview(
            tree_frame,
            columns=self.COLUMNS,
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
        )

        scrollbar_y.config(command=self.treeview.yview)
        scrollbar_x.config(command=self.treeview.xview)

        # カラムヘッダー設定
        for col, header in zip(self.COLUMNS, self.COLUMN_HEADERS, strict=True):
            self.treeview.heading(
                col,
                text=header,
                command=lambda c=col: self._on_column_click(c),  # type: ignore[misc]
            )
            self.treeview.column(col, width=120, minwidth=80)

        # レイアウト
        self.treeview.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

    def _on_open_file(self) -> None:
        """ファイル選択ダイアログを表示して読み込み"""
        filetypes = [
            ("DBC/LDFファイル", "*.dbc *.ldf"),
            ("DBCファイル", "*.dbc"),
            ("LDFファイル", "*.ldf"),
            ("すべてのファイル", "*.*"),
        ]
        file_paths = filedialog.askopenfilenames(
            title="ファイルを開く",
            filetypes=filetypes,
        )
        for fp in file_paths:
            try:
                self.load_file(Path(fp))
            except Exception as e:
                # F03: エラーメッセージの日本語化・詳細化
                file_name = Path(fp).name
                error_message = self._format_error_message(file_name, e)
                messagebox.showerror("読み込みエラー", error_message)

    def load_file(self, file_path: Path) -> None:
        """ファイルを読み込んで信号をリポジトリに追加

        Args:
            file_path: DBC/LDF ファイルのパス

        Raises:
            ValueError: サポートされていないファイル形式の場合
        """
        suffix = file_path.suffix.lower()

        if suffix == ".dbc":
            parser = DBCParser()
            signals = parser.parse(file_path)
        elif suffix == ".ldf":
            parser_ldf = LDFParser()
            signals = parser_ldf.parse(file_path)
        else:
            raise ValueError(f"サポートされていないファイル形式: {suffix}")

        self.repository.add_signals(signals)
        self.loaded_files.append(str(file_path))
        self._update_file_list_label()
        self._refresh_treeview()
        # F06: ステータスバー更新
        if self._status_callback:
            self._status_callback(
                f"信号読み込み完了: {len(signals)}件追加 (総計: {self.repository.count}件)"
            )

    def _update_file_list_label(self) -> None:
        """読み込みファイル一覧ラベルを更新"""
        if self.loaded_files:
            names = [Path(f).name for f in self.loaded_files]
            self.file_list_label.config(text=f"読込ファイル: {', '.join(names)}")
        else:
            self.file_list_label.config(text="読込ファイル: なし")

    def _on_search_changed(self, *_args: object) -> None:
        """検索テキスト変更時のコールバック"""
        self._refresh_treeview()

    def _on_column_click(self, column: str) -> None:
        """カラムヘッダークリック時のソート"""
        reverse = self._sort_reverse.get(column, False)
        self._sort_reverse[column] = not reverse
        self._refresh_treeview(sort_column=column, sort_reverse=reverse)

    def _refresh_treeview(
        self,
        sort_column: str | None = None,
        sort_reverse: bool = False,
    ) -> None:
        """Treeview の表示を更新"""
        # 既存アイテムをクリア
        for item in self.treeview.get_children():
            self.treeview.delete(item)

        # フィルタリング
        try:
            query = str(self.search_var.get()) if hasattr(self, "search_var") else ""
        except Exception:
            query = ""
        signals = self.get_filtered_signals(query)

        # ソート
        if sort_column:
            signals = self.sort_signals(signals, sort_column, sort_reverse)

        # 挿入
        for signal in signals:
            row = self.signal_to_row(signal)
            self.treeview.insert("", tk.END, values=row)

    def get_filtered_signals(self, query: str) -> list[SignalInfo]:
        """検索クエリで信号をフィルタリング"""
        return self.repository.search(query)

    def signal_to_row(self, signal: SignalInfo) -> tuple[str, ...]:
        """SignalInfo を Treeview の行データに変換"""
        return (
            signal.signal_name,
            signal.message_name,
            f"0x{signal.message_id:X}",
            signal.data_type,
            str(signal.min_value),
            str(signal.max_value),
            signal.unit,
            signal.protocol.value,
        )

    def _format_error_message(self, file_name: str, error: Exception) -> str:
        """エラーメッセージをフォーマットする (F03)

        Args:
            file_name: エラーが発生したファイル名
            error: 発生した例外

        Returns:
            ユーザーフレンドリーなエラーメッセージ
        """
        error_str = str(error)

        # エラー種別に応じたメッセージ
        if "サポートされていないファイル形式" in error_str:
            return (
                f"「{file_name}」はサポートされていないファイル形式です。\n"
                f"DBC または LDF ファイルを選択してください。\n\n詳細: {error_str}"
            )
        elif "No such file" in error_str or "FileNotFoundError" in error.__class__.__name__:
            return (
                f"「{file_name}」の読み込みに失敗しました。\n"
                f"ファイルが存在するか確認してください。\n\n詳細: {error_str}"
            )
        elif "Invalid DBC" in error_str or "DBCParseError" in error.__class__.__name__:
            return (
                f"「{file_name}」は有効な DBC ファイルではありません。\n"
                f"CANoe で正しく読み込めるファイルを選択してください。\n\n詳細: {error_str}"
            )
        elif "Invalid LDF" in error_str or "LDFParseError" in error.__class__.__name__:
            return (
                f"「{file_name}」は有効な LDF ファイルではありません。\n"
                f"CANoe で正しく読み込めるファイルを選択してください。\n\n詳細: {error_str}"
            )
        else:
            return f"「{file_name}」の読み込み中にエラーが発生しました。\n\n詳細: {error_str}"

    def sort_signals(
        self,
        signals: list[SignalInfo],
        column: str,
        reverse: bool = False,
    ) -> list[SignalInfo]:
        """信号リストをソート

        Args:
            signals: ソート対象の信号リスト
            column: ソートキーのカラム名
            reverse: 逆順ソートの場合 True

        Returns:
            ソート済みの信号リスト
        """

        def sort_key(s: SignalInfo) -> str:
            val = getattr(s, column, "")
            if hasattr(val, "value"):
                return str(val.value)
            return str(val)

        return sorted(signals, key=sort_key, reverse=reverse)
