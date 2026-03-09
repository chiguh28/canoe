"""Main window for CANoe Auto Test Tool

This module provides the main GUI window with tabs, menu bar, and status bar.
"""

import tkinter as tk
from tkinter import ttk

from src.gui.execution_tab import ExecutionTab
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

    def _create_menu(self) -> None:
        """メニューバー作成"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="ファイルを開く...")
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit)
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
        self.signal_tab = SignalTab(self.signal_frame, self.signal_repository)

        # Phase 2: テストパターンタブ
        ph2_frame = ttk.Frame(self.notebook)
        self.notebook.add(ph2_frame, text="テストパターン作成")

        # Phase 3: テスト実行タブ
        ph3_frame = ttk.Frame(self.notebook)
        self.notebook.add(ph3_frame, text="テスト実行")
        self.execution_tab = ExecutionTab(ph3_frame)

        # Phase 4: 結果・帳票タブ
        ph4_frame = ttk.Frame(self.notebook)
        ttk.Label(ph4_frame, text="準備中（Phase 4 で実装）").pack(pady=50)
        self.notebook.add(ph4_frame, text="結果・帳票")

    def _create_statusbar(self) -> None:
        """ステータスバー作成"""
        self.statusbar = ttk.Label(self.root, text="準備完了", relief=tk.SUNKEN, anchor=tk.W)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    def set_status(self, message: str) -> None:
        """ステータスバーのメッセージを更新"""
        self.statusbar.config(text=message)

    def run(self) -> None:
        """メインループ開始"""
        self.root.mainloop()
