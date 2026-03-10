"""Main window for CANoe Auto Test Tool

This module provides the main GUI window with tabs, menu bar, and status bar.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from src.config.settings_manager import SettingsManager
from src.gui.execution_tab import ExecutionTab
from src.gui.keyboard_shortcuts import KeyboardShortcutManager
from src.gui.pattern_tab import PatternTab
from src.gui.report_tab import ReportTab
from src.gui.signal_tab import SignalTab
from src.models.signal_model import SignalRepository
from src.models.test_pattern import TestPatternRepository


class MainWindow:
    """メインウィンドウ

    アプリケーション全体のフレームを管理する。
    タブ構成で各フェーズの機能を統合する。
    """

    TITLE = "CANoe 自動テストツール"
    DEFAULT_WIDTH = 1024
    DEFAULT_HEIGHT = 768
    VERSION = "0.1.0"

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(self.TITLE)
        self.root.geometry(f"{self.DEFAULT_WIDTH}x{self.DEFAULT_HEIGHT}")
        self.root.minsize(800, 600)

        self.signal_repository = SignalRepository()
        self.pattern_repository = TestPatternRepository()
        self.shortcut_manager = KeyboardShortcutManager()
        self.settings = SettingsManager()

        self._create_menu()
        self._create_notebook()
        self._create_statusbar()
        self._setup_keyboard_shortcuts()

    def _create_menu(self) -> None:
        """メニューバー作成"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label="ファイルを開く...", command=self._on_open_file, accelerator="Ctrl+O"
        )
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="ファイル", menu=file_menu)

        # ツールメニュー
        tool_menu = tk.Menu(menubar, tearoff=0)
        tool_menu.add_command(label="設定...", command=self._on_settings)
        menubar.add_cascade(label="ツール", menu=tool_menu)

        # ヘルプメニュー
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="バージョン情報", command=self._on_about)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)

    def _create_notebook(self) -> None:
        """タブ (Notebook) 作成"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Phase 1: 信号情報タブ
        self.signal_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.signal_frame, text="信号情報")
        self.signal_tab = SignalTab(self.signal_frame, self.signal_repository)

        # Phase 2: テストパターン作成タブ
        ph2_frame = ttk.Frame(self.notebook)
        self.notebook.add(ph2_frame, text="テストパターン作成")
        self.pattern_tab = PatternTab(
            ph2_frame, self.signal_repository, self.pattern_repository
        )

        # Phase 3: テスト実行タブ
        ph3_frame = ttk.Frame(self.notebook)
        self.notebook.add(ph3_frame, text="テスト実行")
        self.execution_tab = ExecutionTab(ph3_frame)

        # Phase 4: 結果・帳票タブ
        ph4_frame = ttk.Frame(self.notebook)
        self.notebook.add(ph4_frame, text="結果・帳票")
        self.report_tab = ReportTab(ph4_frame)

        # タブ切替時にデータを同期
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _create_statusbar(self) -> None:
        """ステータスバー作成"""
        self.statusbar = ttk.Label(self.root, text="準備完了", relief=tk.SUNKEN, anchor=tk.W)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    def set_status(self, message: str) -> None:
        """ステータスバーのメッセージを更新"""
        self.statusbar.config(text=message)

    def _setup_keyboard_shortcuts(self) -> None:
        """キーボードショートカットを設定"""
        self.shortcut_manager.register(
            "Ctrl+O", "ファイルを開く", self._on_open_file
        )
        self.shortcut_manager.register(
            "Ctrl+Q", "終了", self.root.quit
        )
        self.shortcut_manager.register(
            "F5", "テスト実行", self._on_run_tests
        )
        self.shortcut_manager.register(
            "Ctrl+E", "Excel帳票出力", self._on_export_report
        )
        self.shortcut_manager.bind_to_widget(self.root)

    def _on_open_file(self) -> None:
        """ファイルを開く（メニュー連携）"""
        self.signal_tab._on_open_file()
        # 信号読込後にパターンタブの信号リストを更新
        self.pattern_tab.refresh_signals()
        self.set_status(f"信号情報: {self.signal_repository.count} 件読込済み")

    def _on_settings(self) -> None:
        """設定ダイアログ"""
        messagebox.showinfo(
            "設定",
            "設定はJSON形式で管理されます。\n"
            f"CANoe構成ファイル: {self.settings.get('canoe_config_path') or '未設定'}\n"
            f"ログ保存先: {self.settings.get('log_directory') or 'logs'}\n"
            f"帳票出力先: {self.settings.get('report_output_directory') or '未設定'}",
        )

    def _on_about(self) -> None:
        """バージョン情報ダイアログ"""
        messagebox.showinfo(
            "バージョン情報",
            f"{self.TITLE}\nバージョン: {self.VERSION}\n\n"
            "CANoe を用いた車載通信テストの自動化ツール",
        )

    def _on_tab_changed(self, _event: object = None) -> None:
        """タブ切替時の処理"""
        # パターンタブに切り替えた時に信号リストを更新
        current = self.notebook.index(self.notebook.select())
        if current == 1:  # テストパターン作成タブ
            self.pattern_tab.refresh_signals()
        elif current == 2:  # テスト実行タブ
            # 実行タブにパターンを渡す
            patterns = self.pattern_tab.get_all_patterns()
            self.execution_tab.set_patterns(patterns)

    def _on_run_tests(self) -> None:
        """テスト実行（ショートカット）"""
        patterns = self.pattern_tab.get_all_patterns()
        self.execution_tab.set_patterns(patterns)
        self.notebook.select(2)  # テスト実行タブに切替
        self.execution_tab._on_start()

    def _on_export_report(self) -> None:
        """Excel帳票出力（ショートカット）"""
        self.notebook.select(3)  # 結果・帳票タブに切替
        self.report_tab._on_export()

    def run(self) -> None:
        """メインループ開始"""
        self.root.mainloop()
