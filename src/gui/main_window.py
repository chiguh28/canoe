"""Main window for CANoe Auto Test Tool

This module provides the main GUI window with tabs, menu bar, and status bar.
"""

import tkinter as tk
from tkinter import ttk

from src.gui.execution_tab import ExecutionTab
from src.gui.result_tab import ResultTab
from src.gui.signal_tab import SignalTab
from src.models.signal_model import SignalRepository


class MainWindow:
    """メインウィンドウ

    アプリケーション全体のフレームを管理する。
    タブ構成で各フェーズの機能を統合する。
    """

    TITLE = "CANoe 自動テストツール"
    DEFAULT_WIDTH = 1024
    DEFAULT_HEIGHT = 768

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(self.TITLE)
        self.root.geometry(f"{self.DEFAULT_WIDTH}x{self.DEFAULT_HEIGHT}")
        self.root.minsize(800, 600)

        self.signal_repository = SignalRepository()

        self._create_menu()
        self._create_notebook()
        self._create_statusbar()
        self._connect_menu_commands()
        self._bind_shortcuts()  # F05: キーボードショートカット

    def _create_menu(self) -> None:
        """メニューバー作成"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        # Note: command will be set after signal_tab is created
        self._file_menu = file_menu
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self._on_quit)
        menubar.add_cascade(label="ファイル", menu=file_menu)

        # ツールメニュー
        tool_menu = tk.Menu(menubar, tearoff=0)
        tool_menu.add_command(label="設定...")
        menubar.add_cascade(label="ツール", menu=tool_menu)

        # ヘルプメニュー
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="バージョン情報")
        menubar.add_cascade(label="ヘルプ", menu=help_menu)

    def _create_notebook(self) -> None:
        """タブ (Notebook) 作成"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Phase 1: 信号情報タブ
        self.signal_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.signal_frame, text="信号情報")
        # F06: ステータスバーコールバックを渡す
        self.signal_tab = SignalTab(
            self.signal_frame, self.signal_repository, status_callback=self.set_status
        )

        # Phase 2: テストパターンタブ
        ph2_frame = ttk.Frame(self.notebook)
        self.notebook.add(ph2_frame, text="テストパターン作成")

        # Phase 3: テスト実行タブ
        ph3_frame = ttk.Frame(self.notebook)
        self.notebook.add(ph3_frame, text="テスト実行")
        # F04: タブ間データ連携 - signal_repository を渡す
        self.execution_tab = ExecutionTab(ph3_frame, repository=self.signal_repository)

        # Phase 4: 結果・帳票タブ (F02)
        ph4_frame = ttk.Frame(self.notebook)
        self.notebook.add(ph4_frame, text="結果・帳票")
        self.result_tab = ResultTab(ph4_frame)

    def _create_statusbar(self) -> None:
        """ステータスバー作成"""
        self.statusbar = ttk.Label(self.root, text="準備完了", relief=tk.SUNKEN, anchor=tk.W)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    def _connect_menu_commands(self) -> None:
        """メニューコマンドの接続（タブ作成後に実行）"""
        # ファイルメニューの「ファイルを開く」をSignalTabに接続 (F01)
        self._file_menu.insert_command(
            0, label="ファイルを開く...", command=self.signal_tab._on_open_file
        )

    def _bind_shortcuts(self) -> None:
        """キーボードショートカットのバインド (F05)"""
        # グローバルショートカット
        self.root.bind("<Control-o>", lambda e: self.signal_tab._on_open_file())
        self.root.bind("<Control-q>", lambda e: self._on_quit())
        self.root.bind("<Control-Tab>", lambda e: self._next_tab())
        self.root.bind("<Control-Shift-Tab>", lambda e: self._prev_tab())
        # F5: テスト実行
        self.root.bind("<F5>", lambda e: self._on_run_test())
        # Ctrl+E: Excel帳票出力
        self.root.bind("<Control-e>", lambda e: self.result_tab._on_export())
        self.root.bind("<Control-E>", lambda e: self.result_tab._on_export())

    def _next_tab(self) -> None:
        """次のタブに移動"""
        current = self.notebook.index(self.notebook.select())
        total = self.notebook.index("end")
        self.notebook.select((current + 1) % total)

    def _prev_tab(self) -> None:
        """前のタブに移動"""
        current = self.notebook.index(self.notebook.select())
        total = self.notebook.index("end")
        self.notebook.select((current - 1) % total)

    def _on_run_test(self) -> None:
        """テスト実行（F5キー用）"""
        # execution_tab の実行開始メソッドを呼ぶ
        if hasattr(self.execution_tab, "_on_start"):
            self.execution_tab._on_start()

    def _on_quit(self) -> None:
        """終了処理"""
        self.root.quit()

    def set_status(self, message: str) -> None:
        """ステータスバーのメッセージを更新"""
        self.statusbar.config(text=message)

    def run(self) -> None:
        """メインループ開始"""
        self.root.mainloop()
