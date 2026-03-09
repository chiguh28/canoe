"""テスト実行制御UI (Issue #18)

テスト実行画面にリアルタイム進捗表示、実行ステータス、
中断ボタンを提供する。
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.engine.test_runner import ExecutionSummary, TestRunner
from src.models.test_pattern import TestPattern


class ExecutionTab:
    """テスト実行タブ

    テスト実行の制御（開始・中断）と進捗表示を管理する。
    """

    def __init__(
        self,
        parent: tk.Widget | ttk.Frame,
        runner: TestRunner | None = None,
    ) -> None:
        self.parent = parent
        self.runner = runner or TestRunner()
        self._is_running: bool = False
        self._execution_thread: threading.Thread | None = None
        self._config_path: str = ""
        self._patterns: list[TestPattern] = []
        self._summary: ExecutionSummary | None = None
        self._log_entries: list[str] = []

        self._create_widgets()

    def _create_widgets(self) -> None:
        """ウィジェット生成"""
        # 設定フレーム
        config_frame = ttk.LabelFrame(self.parent, text="実行設定")
        config_frame.pack(fill=tk.X, padx=5, pady=5)

        # CANoe 構成ファイル選択
        cfg_row = ttk.Frame(config_frame)
        cfg_row.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(cfg_row, text="構成ファイル:").pack(side=tk.LEFT)
        self.config_var = tk.StringVar()
        self.config_entry = ttk.Entry(cfg_row, textvariable=self.config_var, width=50)
        self.config_entry.pack(side=tk.LEFT, padx=5)
        self.browse_button = ttk.Button(
            cfg_row, text="参照...", command=self._on_browse_config
        )
        self.browse_button.pack(side=tk.LEFT)

        # 制御ボタンフレーム
        control_frame = ttk.Frame(self.parent)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        self.start_button = ttk.Button(
            control_frame, text="実行開始", command=self._on_start
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.abort_button = ttk.Button(
            control_frame, text="中断", command=self._on_abort, state=tk.DISABLED
        )
        self.abort_button.pack(side=tk.LEFT, padx=5)

        # 現在のテストケース
        self.current_test_var = tk.StringVar(value="待機中")
        ttk.Label(control_frame, textvariable=self.current_test_var).pack(side=tk.LEFT, padx=20)

        # プログレスバー
        progress_frame = ttk.Frame(self.parent)
        progress_frame.pack(fill=tk.X, padx=5, pady=5)

        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)

        self.progress_label_var = tk.StringVar(value="0 / 0")
        ttk.Label(progress_frame, textvariable=self.progress_label_var).pack()

        # ログ表示
        log_frame = ttk.LabelFrame(self.parent, text="実行ログ")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.log_text = tk.Text(log_frame, height=15, state=tk.DISABLED)
        log_scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_browse_config(self) -> None:
        """構成ファイル選択ダイアログ"""
        path = filedialog.askopenfilename(
            title="CANoe構成ファイルを選択",
            filetypes=[("CANoe構成ファイル", "*.cfg"), ("すべて", "*.*")],
        )
        if path:
            self.config_var.set(path)
            self._config_path = path

    def set_patterns(self, patterns: list[TestPattern]) -> None:
        """実行対象パターンを設定"""
        self._patterns = patterns

    def _on_start(self) -> None:
        """実行開始"""
        if not self._patterns:
            messagebox.showwarning("警告", "実行するテストパターンがありません")
            return

        self._is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.abort_button.config(state=tk.NORMAL)
        self._log_entries.clear()
        self._add_log("テスト実行を開始します...")

        self.runner.set_progress_callback(self._on_progress)
        self._execution_thread = threading.Thread(target=self._run_tests, daemon=True)
        self._execution_thread.start()

    def _on_abort(self) -> None:
        """中断ボタン押下"""
        self.runner.abort()
        self._add_log("中断を要求しました...")

    def _run_tests(self) -> None:
        """テスト実行（別スレッド）"""
        try:
            self._summary = self.runner.execute(
                self._patterns, config_file=self._config_path
            )
            self._add_log(f"実行完了: {self._summary.passed} OK / {self._summary.failed} NG")
        except Exception as e:
            self._add_log(f"実行エラー: {e}")
        finally:
            self._is_running = False
            try:
                self.start_button.config(state=tk.NORMAL)
                self.abort_button.config(state=tk.DISABLED)
            except Exception:
                pass

    def _on_progress(self, current: int, total: int, test_name: str) -> None:
        """進捗更新コールバック"""
        try:
            percent = int((current / total) * 100) if total > 0 else 0
            self.progress_var.set(percent)
            self.progress_label_var.set(f"{current} / {total}")
            self.current_test_var.set(f"実行中: {test_name}")
            self._add_log(f"[{current}/{total}] {test_name}")
        except Exception:
            pass

    def _add_log(self, message: str) -> None:
        """ログメッセージを追加"""
        self._log_entries.append(message)
        try:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        except Exception:
            pass

    @property
    def is_running(self) -> bool:
        """実行中かどうか"""
        return self._is_running

    @property
    def summary(self) -> ExecutionSummary | None:
        """最新の実行サマリ"""
        return self._summary

    @property
    def log_entries(self) -> list[str]:
        """ログエントリ"""
        return list(self._log_entries)
