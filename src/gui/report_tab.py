"""結果・帳票タブ

テスト実行結果の表示とExcel帳票出力を提供する。
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.engine.judgment import JudgmentDetail
from src.engine.test_runner import ExecutionSummary, TestResult
from src.gui.error_messages import ErrorMessages


class ReportTab:
    """結果・帳票タブ

    テスト結果の一覧表示、統計情報、Excel帳票出力を管理する。
    """

    COLUMNS = [
        "test_case_id", "test_case_name", "target_signal",
        "expected_value", "actual_value", "status",
    ]

    COLUMN_HEADERS = [
        "TC-ID", "テストケース名", "対象信号",
        "期待値", "実測値", "判定結果",
    ]

    def __init__(self, parent: tk.Widget | ttk.Frame) -> None:
        self.parent = parent
        self._summary: ExecutionSummary | None = None
        self._judgments: list[JudgmentDetail] = []

        self._create_widgets()

    def _create_widgets(self) -> None:
        """ウィジェット生成"""
        # 統計情報フレーム
        stats_frame = ttk.LabelFrame(self.parent, text="統計情報")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        stats_row = ttk.Frame(stats_frame)
        stats_row.pack(fill=tk.X, padx=5, pady=5)

        self.stats_labels: dict[str, ttk.Label] = {}
        stat_items = [
            ("total", "テスト総数:"),
            ("passed", "OK:"),
            ("failed", "NG:"),
            ("pass_rate", "合格率:"),
        ]
        for key, label_text in stat_items:
            ttk.Label(stats_row, text=label_text).pack(side=tk.LEFT, padx=(10, 2))
            val_label = ttk.Label(stats_row, text="-")
            val_label.pack(side=tk.LEFT, padx=(0, 10))
            self.stats_labels[key] = val_label

        # 操作ボタン
        btn_frame = ttk.Frame(self.parent)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        self.export_button = ttk.Button(
            btn_frame, text="Excel帳票出力", command=self._on_export
        )
        self.export_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(
            btn_frame, text="クリア", command=self._on_clear
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)

        # 結果一覧 Treeview
        tree_frame = ttk.LabelFrame(self.parent, text="テスト結果一覧")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        self.treeview = ttk.Treeview(
            tree_frame,
            columns=self.COLUMNS,
            show="headings",
            yscrollcommand=scrollbar_y.set,
        )
        scrollbar_y.config(command=self.treeview.yview)

        for col, header in zip(self.COLUMNS, self.COLUMN_HEADERS, strict=True):
            self.treeview.heading(col, text=header)
            self.treeview.column(col, width=120, minwidth=80)

        self.treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_export(self) -> None:
        """Excel帳票出力ダイアログ"""
        if self._summary is None:
            messagebox.showwarning("警告", "出力するテスト結果がありません")
            return

        path = filedialog.asksaveasfilename(
            title="Excel帳票を保存",
            defaultextension=".xlsx",
            filetypes=[("Excelファイル", "*.xlsx"), ("すべて", "*.*")],
        )
        if path:
            try:
                result_path = self.generate_report(Path(path))
                messagebox.showinfo("完了", f"帳票を出力しました: {result_path}")
            except Exception as e:
                messagebox.showerror("エラー", ErrorMessages.save_error(path, str(e)))

    def _on_clear(self) -> None:
        """結果クリア"""
        self.clear_results()
        self._refresh_treeview()
        self._update_stats_display()

    def _refresh_treeview(self) -> None:
        """Treeview を更新"""
        for item in self.treeview.get_children():
            self.treeview.delete(item)

        if self._summary:
            for result in self._summary.results:
                row = self.result_to_row(result)
                self.treeview.insert("", tk.END, values=row)

    def _update_stats_display(self) -> None:
        """統計情報表示を更新"""
        if self._summary:
            stats = self.get_statistics()
            self.stats_labels["total"].config(text=str(stats["total"]))
            self.stats_labels["passed"].config(text=str(stats["passed"]))
            self.stats_labels["failed"].config(text=str(stats["failed"]))
            self.stats_labels["pass_rate"].config(text=f"{stats['pass_rate']:.1f}%")
        else:
            for label in self.stats_labels.values():
                label.config(text="-")

    # --- Public API ---

    @property
    def summary(self) -> ExecutionSummary | None:
        """実行サマリ"""
        return self._summary

    @property
    def judgments(self) -> list[JudgmentDetail]:
        """判定結果リスト"""
        return list(self._judgments)

    def set_results(
        self,
        summary: ExecutionSummary,
        judgments: list[JudgmentDetail] | None = None,
    ) -> None:
        """テスト結果を設定"""
        self._summary = summary
        self._judgments = judgments or []
        self._refresh_treeview()
        self._update_stats_display()

    def clear_results(self) -> None:
        """結果をクリア"""
        self._summary = None
        self._judgments = []

    def result_to_row(self, result: TestResult) -> tuple[str, ...]:
        """TestResult を Treeview の行データに変換"""
        return (
            result.test_case_id,
            result.test_case_name,
            "",  # target_signal is in judgment detail
            result.expected_value,
            result.actual_value,
            result.status.value,
        )

    def get_statistics(self) -> dict[str, object]:
        """統計情報を取得"""
        if self._summary is None:
            return {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0.0}
        return {
            "total": self._summary.total,
            "passed": self._summary.passed,
            "failed": self._summary.failed,
            "pass_rate": self._summary.pass_rate,
        }

    def generate_report(self, output_path: Path) -> Path:
        """Excel帳票を生成"""
        if self._summary is None:
            raise ValueError("テスト結果が設定されていません")

        from src.report.excel_report import ExcelReportGenerator

        generator = ExcelReportGenerator()
        return generator.generate(
            summary=self._summary,
            judgments=self._judgments or None,
            output_path=output_path,
            config_file=self._summary.config_file,
        )
